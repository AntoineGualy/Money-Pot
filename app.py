# Imports
from flask import Flask, render_template, redirect, request, session, url_for, abort
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from werkzeug.security import generate_password_hash, check_password_hash
import functools
import secrets

# import request to to be able to conecct to the open foods API
import requests

# DataBase_URL (Supabase)
import os
from dotenv import load_dotenv

load_dotenv()




# My App
app = Flask(__name__)




@app.template_filter("local_time")
def local_time(dt):
    if dt is None :
        return ""
    

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt.astimezone(
        ZoneInfo("America/Denver")
    ).strftime("%b %d, %Y %I:%M %p")
  

app.secret_key = os.getenv("SECRET_KEY")

# Configure database Supabase
db_url = os.getenv("DATABASE_URL")


if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = db_url or "sqlite:///database.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False


db = SQLAlchemy(app)
migrate = Migrate(app, db)

print(app.config["SQLALCHEMY_DATABASE_URI"])

# Security Model ~ Single Row in DB
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(25), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

    # Saves the password when a user signs up
    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method="pbkdf2:sha256")

    # Checks if the user password enter by the user is in the database
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


# A Money Pot - a shared budget that can have multiple members
class Pot(db.Model):
    __tablename__ = "pot"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    budget = db.Column(db.Integer, default=0)
    invite_code = db.Column(db.String(32), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    memberships = db.relationship(
        "Membership", backref="pot", cascade="all, delete-orphan"
    )
    items = db.relationship(
        "GroceryItem", backref="pot", cascade="all, delete-orphan"
    )

    def owner_membership(self):
        return next((m for m in self.memberships if m.role == "owner"), None)

    def __repr__(self):
        return f"<Pot {self.id} {self.name}>"


# Join table between User and Pot - a user can belong to multiple pots,
# and a pot can have multiple members. Carries the owner/member role.
class Membership(db.Model):
    __tablename__ = "membership"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    pot_id = db.Column(db.Integer, db.ForeignKey("pot.id"), nullable=False)
    role = db.Column(db.String(10), nullable=False, default="member")  # 'owner' | 'member'
    joined_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    user = db.relationship("User", backref="memberships")

    __table_args__ = (
        # A user can only have one membership row per pot.
        db.UniqueConstraint("user_id", "pot_id", name="uq_membership_user_pot"),
        # role may only ever be 'owner' or 'member' - enforced by the database,
        # not just application code.
        db.CheckConstraint("role IN ('owner', 'member')", name="ck_membership_role"),
        # Speeds up "find this pot's owner" lookups.
        db.Index("ix_membership_pot_role", "pot_id", "role"),
        # A pot can have at most one 'owner' membership row. This only
        # guarantees AT MOST one owner - it cannot guarantee a pot always
        # HAS an owner. That's an application-level guarantee instead (see
        # the leave/remove-member logic added in a later phase), enforced by
        # keeping every ownership-transfer step inside a single transaction.
        db.Index(
            "uq_membership_one_owner_per_pot",
            "pot_id",
            unique=True,
            sqlite_where=db.text("role = 'owner'"),
            postgresql_where=db.text("role = 'owner'"),
        ),
    )

    def __repr__(self):
        return f"<Membership user={self.user_id} pot={self.pot_id} role={self.role}>"


# Data Class - Row of data
class GroceryItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Integer, default=0)
    category = db.Column(db.String(20))
    time = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    pot_id = db.Column(db.Integer, db.ForeignKey("pot.id"), nullable=False)
    added_by_user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    added_by = db.relationship("User", foreign_keys=[added_by_user_id])

    def __repr__(self):
        return f"<GroceryItem {self.id}>"


# --- Session / auth helpers -------------------------------------------------
# These replace the session["username"] -> User lookup that used to be
# copy-pasted into every route, and add the pot-membership equivalent
# (get_active_pot). No routes call these yet - that's the next phase.

def current_user():
    if "username" not in session:
        return None
    return User.query.filter_by(username=session["username"]).first()


def login_required(view):
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        if "username" not in session:
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def create_personal_pot(user):
    pot = Pot(
        name=f"{user.username}'s Pot",
        budget=0,
        invite_code=secrets.token_urlsafe(12),
    )
    db.session.add(pot)
    db.session.flush()  # assigns pot.id without ending the transaction
    db.session.add(Membership(user_id=user.id, pot_id=pot.id, role="owner"))
    return pot


def get_active_pot(user):
    """Resolve the user's active Pot.

    Returns (pot, created) - created is True only when a fallback personal
    pot had to be created because the user had zero memberships (covers
    leaving a last pot, being removed, or a pot being deleted by its
    owner - always leaves the user with a pot). Never commits: only
    flushes, so a freshly created pot/membership are visible within the
    current transaction. The caller owns the commit, since it may have
    other writes of its own to fold into the same transaction.
    """
    pot_id = session.get("active_pot_id")
    membership = (
        Membership.query.filter_by(user_id=user.id, pot_id=pot_id).first()
        if pot_id else None
    )
    if not membership:
        membership = (
            Membership.query.filter_by(user_id=user.id)
            .order_by(Membership.id.asc())
            .first()
        )
        if not membership:
            pot = create_personal_pot(user)
            db.session.flush()
            session["active_pot_id"] = pot.id
            return pot, True
        session["active_pot_id"] = membership.pot_id
    return membership.pot, False


def _assert_pot_has_owner(pot_id):
    """Defensive check for the leave/ownership-transfer path: the database
    only guarantees a pot has AT MOST one owner (the partial unique index).
    It cannot guarantee a pot always HAS one - that's this function's job.
    Raises before a bad state can be committed, rather than silently
    persisting a pot with zero owners.
    """
    has_owner = Membership.query.filter_by(pot_id=pot_id, role="owner").first() is not None
    if not has_owner:
        raise RuntimeError(f"Pot {pot_id} would be left with no owner - refusing to commit")


# Makes the pot switcher/nav available to every template without every route
# passing pot lists explicitly. Read-only - no writes, no self-heal here.
@app.context_processor
def inject_pot_nav():
    user = current_user()
    if not user:
        return {}
    memberships = (
        Membership.query.filter_by(user_id=user.id)
        .order_by(Membership.id.asc())
        .all()
    )
    return {
        "nav_memberships": memberships,
        "nav_active_pot_id": session.get("active_pot_id"),
    }


# login
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")
    
    # Checks to see if the username name and password match somewhere in the data base
    username = request.form.get("username")
    password = request.form.get("password")
    user = User.query.filter_by(username=username).first()
    
    # allows user to access the home page after being verifed
    if user and user.check_password(password):
        session['username'] = username
        # A self-healed pot is the only possible write on this path - commit
        # it explicitly, since nothing else in this route will.
        _, pot_created = get_active_pot(user)
        if pot_created:
            db.session.commit()
        if session.get("pending_invite_code"):
            return redirect(url_for("join_pot_info", code=session["pending_invite_code"]))
        return redirect(url_for("index"))
    else:
        return render_template("login.html", error="Invalid username or password")





#Sign Up
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("login.html")

    username = (request.form.get("username") or "").strip()
    password = request.form.get("password") or ""

    if not username or not password:
        return render_template("login.html", error="Username and password required.")

    user = User.query.filter_by(username=username).first()
    if user:
        return render_template("login.html", error="There already exist a User with this Username!")

    new_user = User(username=username)
    new_user.set_password(password)
    db.session.add(new_user)
    db.session.commit()

    pot = create_personal_pot(new_user)
    db.session.commit()

    session["username"] = username
    session["active_pot_id"] = pot.id
    if session.get("pending_invite_code"):
        return redirect(url_for("join_pot_info", code=session["pending_invite_code"]))
    return redirect(url_for("index"))




#Logout 
@app.route("/logout", methods=["GET", "POST"])
def logout():
    # pop ends the session
    session.pop("username", None)
    # The user is redirected to the login page
    return redirect(url_for("login"))







# Takes the information puts in database then sends it back
@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    user = current_user()
    pot, pot_created = get_active_pot(user)

    # Add a purchase
    if request.method == "POST":
        amount = int(request.form['amount'])
        category = request.form['category']

        new_item = GroceryItem(
            amount=amount,
            category=category,
            pot_id=pot.id,
            added_by_user_id=user.id
        )
        db.session.add(new_item)
        # One commit persists the new item together with any self-healed
        # pot from above - they're the same transaction either way.
        db.session.commit()
        return redirect("/")

    if pot_created:
        # GET has no other write of its own - without this, a self-healed
        # pot would be discarded when the request ends.
        db.session.commit()

    # 2) Compute "this week" (Monday -> Sunday)
    now = datetime.now(timezone.utc)
    start_of_week = now - timedelta(days=now.weekday())
    start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)

    weekly_budget = pot.budget or 0

    # 3) Purchases this week
    items = (
        GroceryItem.query
        .filter(GroceryItem.time >= start_of_week)
        .filter(GroceryItem.pot_id == pot.id)
        .order_by(GroceryItem.time.desc())
        .all()
     )


    # 4) Calculate spent + remaining
    spent = sum(item.amount for item in items)
    remaining = weekly_budget - spent

    return render_template(
        "index.html",
        username=user.username,
        pot_name=pot.name,
        items=items,
        weekly_budget=weekly_budget,
        spent=spent,
        remaining=remaining
    )




@app.route("/budget", methods=["POST"])
@login_required
def set_budget():
    user = current_user()
    # Any self-healed pot rides along with this route's own write below in
    # the same transaction - no separate commit needed here.
    pot, _ = get_active_pot(user)

    new_budget = (request.form.get("budget") or "").strip()
    if not new_budget.isdigit():
        return "Budget must be a non-negative integer", 400

    pot.budget = int(new_budget)

    db.session.commit()
    return redirect("/")
    






# Delete an Item
@app.route("/delete/<int:id>", methods=["POST"])
@login_required
def delete(id:int):
    user = current_user()
    delete_item = GroceryItem.query.get_or_404(id)

    if not Membership.query.filter_by(user_id=user.id, pot_id=delete_item.pot_id).first():
        abort(403)

    try:
        db.session.delete(delete_item)
        db.session.commit()
        return redirect("/")
    except Exception as e:
        return f"ERROR: {e}"
    





# edit  an Item
@app.route("/edit/<int:id>", methods=["GET", "POST"])
@login_required
def edit(id:int):
    user = current_user()
    edit_item = GroceryItem.query.get_or_404(id)

    if not Membership.query.filter_by(user_id=user.id, pot_id=edit_item.pot_id).first():
        abort(403)

    if request.method == "POST":
        edit_item.amount = request.form['func']
        try:
            db.session.commit()
            return redirect("/")
        except Exception as e:
            return f"ERROR: {e}"
    else:
        return render_template('edit.html', edit_item=edit_item)


# --- Pot management routes ---------------------------------------------------

# "My Pots" list, and the create-pot form's target page. The create form
# itself lives on this same template, per the plan - there's no separate
# standalone "new pot" page.
@app.route("/pots", methods=["GET"])
@login_required
def list_pots():
    user = current_user()
    memberships = (
        Membership.query.filter_by(user_id=user.id)
        .order_by(Membership.id.asc())
        .all()
    )
    return render_template("pots_list.html", memberships=memberships)


@app.route("/pots/new", methods=["GET", "POST"])
@login_required
def new_pot():
    if request.method == "GET":
        # The creation form lives on the list page, not a page of its own.
        return redirect(url_for("list_pots"))

    user = current_user()
    name = (request.form.get("name") or "").strip()
    if not name:
        return "Pot name is required", 400

    pot = Pot(name=name, budget=0, invite_code=secrets.token_urlsafe(12))
    db.session.add(pot)
    db.session.flush()
    db.session.add(Membership(user_id=user.id, pot_id=pot.id, role="owner"))
    db.session.commit()

    session["active_pot_id"] = pot.id
    return redirect(url_for("index"))


@app.route("/pots/switch", methods=["POST"])
@login_required
def switch_pot():
    user = current_user()
    pot_id = request.form.get("pot_id", type=int)
    membership = (
        Membership.query.filter_by(user_id=user.id, pot_id=pot_id).first()
        if pot_id else None
    )
    if not membership:
        abort(403)
    session["active_pot_id"] = membership.pot_id
    return redirect(url_for("index"))


@app.route("/pots/<int:pot_id>/settings", methods=["GET"])
@login_required
def pot_settings(pot_id):
    user = current_user()
    membership = Membership.query.filter_by(user_id=user.id, pot_id=pot_id).first()
    if not membership:
        abort(403)
    pot = Pot.query.get_or_404(pot_id)
    memberships = (
        Membership.query.filter_by(pot_id=pot.id)
        .order_by(Membership.id.asc())
        .all()
    )
    return render_template(
        "pot_settings.html", pot=pot, memberships=memberships, my_role=membership.role
    )


# Regenerating the invite code invalidates the old link immediately (owner
# needs this after removing a member, so the old shared link stops working).
# A separate "revoke" (disable invites entirely, no working link at all)
# would need invite_code to be nullable - out of scope for the MVP; dropped
# per review rather than kept as a redundant duplicate of this route.
@app.route("/pots/<int:pot_id>/invite/regenerate", methods=["POST"])
@login_required
def regenerate_invite(pot_id):
    user = current_user()
    if not Membership.query.filter_by(user_id=user.id, pot_id=pot_id, role="owner").first():
        abort(403)
    pot = Pot.query.get_or_404(pot_id)
    pot.invite_code = secrets.token_urlsafe(12)
    db.session.commit()
    return redirect(url_for("pot_settings", pot_id=pot.id))


@app.route("/pots/<int:pot_id>/leave", methods=["POST"])
@login_required
def leave_pot(pot_id):
    user = current_user()
    membership = Membership.query.filter_by(user_id=user.id, pot_id=pot_id).first()
    if not membership:
        abort(403)

    other_memberships = (
        Membership.query.filter(Membership.pot_id == pot_id, Membership.id != membership.id)
        .order_by(Membership.id.asc())
        .all()
    )

    if not other_memberships:
        # Last member leaving - the pot and everything in it goes with them.
        # Explicit bulk deletes (not relying on ORM/DB cascade - SQLite
        # doesn't enforce FKs by default in dev).
        GroceryItem.query.filter_by(pot_id=pot_id).delete()
        Membership.query.filter_by(pot_id=pot_id).delete()
        Pot.query.filter_by(id=pot_id).delete()
    else:
        # Delete the leaving member's row FIRST and flush before promoting a
        # new owner: the partial unique index only allows one 'owner' row
        # per pot at a time, checked immediately (not deferred) on SQLite -
        # setting the new owner's role while the old owner's row still
        # exists would violate it, even though the old row is about to go.
        was_owner = membership.role == "owner"
        db.session.delete(membership)
        db.session.flush()
        if was_owner:
            new_owner = other_memberships[0]  # lowest Membership.id = longest-standing
            new_owner.role = "owner"
            db.session.flush()
        _assert_pot_has_owner(pot_id)

    if session.get("active_pot_id") == pot_id:
        session.pop("active_pot_id", None)

    db.session.commit()
    return redirect(url_for("index"))


@app.route("/pots/<int:pot_id>/members/<int:user_id>/remove", methods=["POST"])
@login_required
def remove_member(pot_id, user_id):
    user = current_user()
    if not Membership.query.filter_by(user_id=user.id, pot_id=pot_id, role="owner").first():
        abort(403)

    if user_id == user.id:
        return "Owners cannot remove themselves - use leave instead.", 400

    target_membership = Membership.query.filter_by(user_id=user_id, pot_id=pot_id).first()
    if not target_membership:
        abort(404)

    db.session.delete(target_membership)
    db.session.commit()
    return redirect(url_for("pot_settings", pot_id=pot_id))


@app.route("/join/<code>", methods=["GET"])
def join_pot_info(code):
    pot = Pot.query.filter_by(invite_code=code).first()
    if not pot:
        return render_template("join_pot.html", pot=None, code=code), 404
    if "username" not in session:
        session["pending_invite_code"] = code
        return redirect(url_for("login"))
    return render_template("join_pot.html", pot=pot, code=code)


@app.route("/join/<code>", methods=["POST"])
@login_required
def join_pot(code):
    user = current_user()
    pot = Pot.query.filter_by(invite_code=code).first()
    if not pot:
        abort(404)

    # Idempotent: joining a pot you're already in just switches to it,
    # rather than erroring or creating a duplicate membership.
    existing = Membership.query.filter_by(user_id=user.id, pot_id=pot.id).first()
    if not existing:
        db.session.add(Membership(user_id=user.id, pot_id=pot.id, role="member"))
        db.session.commit()

    session["active_pot_id"] = pot.id
    session.pop("pending_invite_code", None)
    return redirect(url_for("index"))




@app.route("/lookup", methods=["GET"])
def smart_look():
        return render_template('look_up.html')




@app.route("/lookup", methods=["POST"])
def smart_look_post():
    
    barcode = request.form["barcode"].strip()

    url = f"https://world.openfoodfacts.org/api/v2/product/{barcode}.json"
    response = requests.get(url, timeout=25)
    data = response.json()

    result = None

    # API test results
    print("RAW BARCODE:", repr(barcode))
    print("URL:", url)
    print("OFF HTTP:", response.status_code)
    print("OFF STATUS FIELD:", data.get("status"))
    print("OFF CODE FIELD:", data.get("code"))

    if data.get("status") == 1:
        product = data.get("product", {})
        name = product.get("product_name", "N/A")
        brand = product.get("brands", "N/A") 
        category = product.get("categories", "N/A")
        nutriments = product.get("nutriments", {})
        calories = nutriments.get("energy-kcal_100g", "N/A")
        sugar = nutriments.get("sugars_100g", "N/A")
        protein = nutriments.get("proteins_100g", "N/A")
        
        result = {"name": name, "brand": brand, "category": category,
                   "calories": calories, "sugar": sugar, "protein": protein}
        

    else:
        result = {"error":"Product not found"}  

    
    return render_template("look_up.html", result=result)




@app.route("/lookup/name")
def lookup_name():
    return render_template("lookup_name.html")







@app.route("/lookup/name", methods=["POST"])
def lookup_name_post():


    name = request.form["brand_name"].strip()

    url = "https://world.openfoodfacts.org/cgi/search.pl"
    params = {
        "search_terms": name,
        "search_simple": 1,
        "action": "process",
        "json": 1,
        "page_size": 5
    }

    response = requests.get(url, params=params, timeout=10)
    data = response.json()

    
    #The page crashs after 25 seconds and this is what the page should do if so.
    try:
        response = requests.get(url, params=params, timeout=25)
    except requests.exceptions.Timeout:
        return render_template("lookup_name.html", result={"error": "Open Food Facts timed out. Try again."})
    except Exception as e:
        return render_template("lookup_name.html", result={"error": f"Request failed: {e}"})
    


    # API test results
    print("RAW QUERY:", repr(name))
    print("OFF HTTP:", response.status_code)
    print("NUM PRODUCTS:", len(data.get("products", [])))



    products = data.get("products", [])

    if products:
        product = products[0]

        name = product.get("product_name", "N/A")
        brand = product.get("brands", "N/A") 
        category = product.get("categories", "N/A")
        nutriments = product.get("nutriments", {})
        calories = nutriments.get("energy-kcal_100g", "N/A")
        sugar = nutriments.get("sugars_100g", "N/A")
        protein = nutriments.get("proteins_100g", "N/A")
        
        result = {"name": name, "brand": brand, "category": category,
                   "calories": calories, "sugar": sugar, "protein": protein}
        

    else:
        result = {"error":"Product not found"}  

    
    return render_template("lookup_name.html", result=result)






@app.route("/what-page", methods = ["GET", "POST"])
def what_page():
    return render_template("what.html")







@app.route("/test-api")
def test_api():
    # test http call = http://127.0.0.1:5000/test-api

    barcode = "737628064502"

    url = f"https://world.openfoodfacts.org/api/v2/product/{barcode}.json"

    response = requests.get(url)

    print(response.status_code)
    data = response.json()
    print(data.keys())


    if data.get("status") == 1:
        product = data.get("product", {})
        name = product.get("product_name", "No name found")
        print("Product name:", name)
    else:
        print("Product not found")    

    
    
    return "Check the terminal for API response"





if __name__ in "__main__":
    app.run(debug=True)