<p align="center">
  <h1 align="center">🥫 Money-Pot</h1>
  <p align="center"><b>Smart grocery budgeting made simple, shared, and accessible.</b></p>
</p>


🥫 Money-Pot
Smart grocery budgeting made simple, shared, and accessible.
Money-Pot is a free grocery budgeting web application that helps users manage grocery spending, track purchases, collaborate under a shared budget, discover deals and coupons, and access free food resources. It is designed especially for college students, roommates, couples, and low-income users who need a clear, reliable way to manage shared grocery expenses.
This repository represents the MVP (Minimum Viable Product) and ongoing development of Money-Pot.


🧩 Problem Statement
Grocery budgeting is a major source of stress in shared households. Many people—especially college students—rely on verbal agreements or loose planning when splitting grocery costs. This often leads to:
Overspending
Confusion over who paid for what
Financial stress and arguments
Poor visibility into shared expenses
At the same time, low-income and food-insecure individuals face additional challenges in finding affordable groceries and accessing free food resources.
Money-Pot solves this by providing a centralized, transparent, and collaborative grocery budgeting system.


🎯 Target Users
Primary Users
College students
Roommates sharing grocery expenses
Couples or partners managing a joint budget
Secondary Users
Low-income households
Food-insecure individuals
Families aiming to reduce grocery spending


🏆 Product Goals
Primary Goal
Help users create a stable, shared grocery budgeting system that promotes financial awareness, reduces overspending, and improves communication in shared households.
Success Looks Like
Users clearly understand where their grocery money is going
Shared households avoid confusion or conflict over expenses
Users actively reduce unnecessary grocery spending
Users take advantage of deals, coupons, and free food resources
Food-insecure users gain easier access to essential food support


✨ Core Features (Planned & In Progress)

🧑‍🤝‍🧑 Shared Budgeting
Create weekly or monthly grocery budgets
Invite roommates, partners, or family members
Everyone can add purchases and view shared spending

🧾 User Accountability
Track who made each purchase
See when money was spent
Understand how each purchase impacts the shared budget
Encourages transparency and teamwork

🛒 Grocery Deals & Coupons
Integration with external APIs for:
Store deals
Coupons
Discounts and promotions
Helps users save money before they shop

🥗 Free Food Resources
A dedicated section for:
Local food banks
Free food events
Community kitchens
Free grocery programs
Designed to support low-income and food-insecure users.

📊 Analytics Dashboard
Weekly and monthly spending summaries
Category-based spending (produce, meat, snacks, etc.)
Spending trends over time




🛠️ Current MVP Status
The current MVP focuses on establishing the backend foundation:
Flask-based web application
CRUD functionality for budget entries
SQLAlchemy ORM with a relational database
Server-side routing (GET/POST)
Dynamic rendering with Jinja2
Deployed web app for testing real-world behavior




⚠️ Known Limitation & Key Learning
During deployment, a critical issue was discovered:
budget data entered by one user was visible to others using the same deployed app.
This highlighted an important architectural lesson:
Shared state exists without authentication
User-specific data must be scoped correctly
Authentication and session management are essential for real-world apps
This insight directly informs the next development phase:
user accounts, authentication, and true shared-budget groups.



🧠 What I’ve Learned So Far
How shared data behaves in deployed web applications
Why authentication is critical for privacy and trust
How MVPs expose real architectural flaws
How to debug logical and system-level issues
How product requirements influence backend design



🛠️ Tech Stack
Backend
Python
Flask
SQLAlchemy
SQLite (development)
Frontend
HTML
CSS
Jinja2 Templates
Tools
Git & GitHub
VS Code


🔮 Roadmap
User authentication (login & registration)
True shared-budget groups with multiple users
Budget invitations & permissions
Grocery deal & coupon API integration
Free food resource database
Analytics dashboard & visualizations
Production-ready database


🚧 Project Status
Active Development (MVP → V1)
Money-Pot is under active development and architectural refinement.


📫 Contact
Antoine Gualy
gualyantoine@gmail.com
Computer Science Student
Aspiring Software Engineer

