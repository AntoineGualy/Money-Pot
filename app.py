# Imports 
from flask import Flask, render_template, redirect, request
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime


# My App
app = Flask(__name__)



@app.route("/", methods=["GET", "POST"])
def index():
    return render_template('index.html')




if __name__ in "__main__":
    app.run(debug=True)