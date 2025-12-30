# Imports 
from flask import Flask, render_template, redirect, request
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta

# import request to to be able to conecct to the open foods API
import requests


# My App
app = Flask(__name__)


# Configure database SQL
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
db = SQLAlchemy(app)




# Data Class - Row of data

class GroceryItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Integer, default=0)
    category = db.Column(db.String(20))
    shopper = db.Column(db.String(20))
    time = db.Column(db.DateTime, default=datetime.utcnow)



class WeeklyBudget(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    budget = db.Column(db.Integer, default=0)



    def __repr__(self):
        return f"item {self.id}"
    





# Takes the information puts in database then sends it back 
@app.route("/", methods=["GET", "POST"])
def index():
    # Add a purchase
    if request.method == "POST":
        amount = int(request.form['amount'])
        category = request.form['category']
        shopper = request.form['shopper']
        new_item = GroceryItem(
            amount=amount,
            category=category,
            shopper=shopper
        )
        db.session.add(new_item)
        db.session.commit()
        return redirect("/")
    
    # GET = show dashboard + list
    # 1) Get weekly budget (single row) 
    budget_row = WeeklyBudget.query.first()
    weekly_budget = budget_row.budget if budget_row else 0

    # 2) Compute "this week" (Monday -> Sunday)
    now = datetime.utcnow()
    start_of_week = now - timedelta(days=now.weekday())
    start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)


    # 3) Purchases this week
    items = (
        GroceryItem.query
        .filter(GroceryItem.time >= start_of_week)
        .order_by(GroceryItem.time.desc())
        .all()  
     )
    

    # 4) Calculate spent + remaining
    spent = sum(item.amount for item in items)
    remaining = weekly_budget - spent

    return render_template(
        "index.html",
        items=items,
        weekly_budget=weekly_budget,
        spent=spent,
        remaining=remaining
    )






@app.route("/budget", methods=["POST"])
def set_budget():
    new_budget = int(request.form["budget"])

    budget_row = WeeklyBudget.query.first()

    if budget_row:
        #Update existing row
        budget_row.budget = new_budget
    else:
        #Create it once
        budget_row = WeeklyBudget(budget=new_budget)
        db.session.add(budget_row)

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
    
    barcode = "737628064502"

    url = f"https://world.openfoodfacts.org/api/v2/product/{barcode}.json"

    response = requests.get(url)

    print(response.status_code)
    data = response.json()
    print(data.keys())


    if data.get("status") == 1:
        product = data.get("product", {})
        name = product.get("product_name", "No name found")
        result = {"name": name}
    else:
        print("Product not found")    

    
    
    return render_template("look_up.html", result=result)






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
    with app.app_context():
        db.create_all()
    app.run(debug=True)