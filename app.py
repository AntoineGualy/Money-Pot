# Imports 
from flask import Flask, render_template, redirect, request, session, url_for 
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from werkzeug.security import generate_password_hash, check_password_hash

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

print(app.config["SQLALCHEMY_DATABASE_URI"])

# Security Model ~ Single Row in DB
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(25), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    budget_id = db.Column(db.Integer, db.ForeignKey("budget.id"), nullable=True)
    



    # Saves the password when a user signs up
    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method="pbkdf2:sha256")



    # Checks if the user password enter by the user is in the database
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)



# Data Class - Row of data
class GroceryItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Integer, default=0)
    category = db.Column(db.String(20))
    shopper = db.Column(db.String(20))
    time = db.Column(db.DateTime,default=lambda: datetime.now(timezone.utc))
    budget_id = db.Column(db.Integer, db.ForeignKey("budget.id"), nullable=False)



class Budget(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # ForeignKey that connects each user to they own budget
    owner_user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    budget = db.Column(db.Integer, default=0)



    def __repr__(self):
        return f"item {self.id}"
    

with app.app_context():
    db.create_all()




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

    new_budget = Budget(owner_user_id=new_user.id, budget=0)
    db.session.add(new_budget)
    db.session.commit()

    new_user.budget_id = new_budget.id
    db.session.commit()

    session["username"] = username
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
def index():
    # If the user is not loged in he is automatically
    username = request.form.get("username")
    if "username" not in session:
        return render_template("login.html")
    
    # Display Username at the top
    username = session["username"]

    # Finds the logged in user
    username = session["username"]
    user = User.query.filter_by(username=username).first()

    # Gets the user's budget row
    budget_row = Budget.query.get(user.budget_id)
    weekly_budget = budget_row.budget if budget_row else 0
    
    # Add a purchase
    if request.method == "POST":
        amount = int(request.form['amount'])
        category = request.form['category']
        shopper = request.form['shopper']

        if not user or not user.budget_id:
            return "No budget found for this user.", 400
        
        
        new_item = GroceryItem(
            amount=amount,
            category=category,
            shopper=shopper,
            budget_id = user.budget_id
        )
        db.session.add(new_item)
        db.session.commit()
        return redirect("/")



    # 2) Compute "this week" (Monday -> Sunday)
    now = datetime.now(timezone.utc)
    start_of_week = now - timedelta(days=now.weekday())
    start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)

    # Initialize weekly_bdget 
    weekly_budget = budget_row.budget if budget_row else 0

    # Stops user for sharing unwanted data
    username = session["username"]
    user = User.query.filter_by(username=username).first()

    # 3) Purchases this week
    items = (
        GroceryItem.query
        .filter(GroceryItem.time >= start_of_week)
        .filter(GroceryItem.budget_id == user.budget_id)
        .order_by(GroceryItem.time.desc())
        .all()  
     )
    

    # 4) Calculate spent + remaining
    spent = sum(item.amount for item in items)
    remaining = weekly_budget - spent

    return render_template(
        "index.html",
        username=username,
        items=items,
        weekly_budget=weekly_budget,
        spent=spent,
        remaining=remaining
    )




@app.route("/budget", methods=["POST"])
def set_budget():
    # if the user in not signed send they to the login page 
    if "username" not in session:
        return redirect(url_for("login"))
    
    # Finds user 
    username = session["username"]
    user = User.query.filter_by(username=username).first()
    if not user or not user.budget_id:
        return "No budget found for this user.", 400
    
    
    new_budget = (request.form.get("budget") or "").strip()
    if not new_budget.isdigit():
        return "Budget must be a non-negative integer", 400
    
    new_budget = int(new_budget)
    

    budget_row = Budget.query.get(user.budget_id)
    if not budget_row:
        return "Budget record missing", 400
    
    budget_row.budget = new_budget

    """if budget_row:
        #Update existing row
        budget_row.budget = new_budget
    else:
        #Create it once
        budget_row = Budget(budget=new_budget)
        db.session.add(budget_row)"""

    db.session.commit()
    return redirect("/")
    






# Delete an Item
@app.route("/delete/<int:id>")
def delete(id:int):
    delete_item = GroceryItem.query.get_or_404(id)
    try:
        db.session.delete(delete_item)
        db.session.commit()
        return redirect("/")
    except Exception as e:
        return f"ERROR: {e}"
    





# edit  an Item 
@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit(id:int):
    edit_item = GroceryItem.query.get_or_404(id)
    if request.method == "POST":
        edit_item.amount = request.form['func'] 
        try:
            db.session.commit()
            return redirect("/")
        except Exception as e:
            return f"ERROR: {e}"
    else:
        return render_template('edit.html', edit_item=edit_item)





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





with app.app_context():
    db.create_all()
    
if __name__ in "__main__":
    app.run(debug=True)