# Imports 
from flask import Flask, render_template, redirect, request
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime


# My App
app = Flask(__name__)


# Configure database SQL
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
db = SQLAlchemy(app)




# Data Class - Row of data

class GroceryItem(db.Model):
    id = db.Column(db.Float, primary_key=True)
    amount = db.Column(db.Integer, default=0)
    category = db.Column(db.String(20))
    shopper = db.Column(db.String(20))
    time = db.Column(db.DateTime, default=datetime.utcnow)


    def __repr__(self):
        return f"item {self.id}"
    














@app.route("/", methods=["GET", "POST"])
def index():
    return render_template('index.html')




if __name__ in "__main__":
    app.run(debug=True)