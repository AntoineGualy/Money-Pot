https://antoinegualy.github.io/Money-Pot/

<p align="center">
  <h1 align="center">🥫 Money-Pot</h1>
  <p align="center"><b>Smart grocery budgeting made simple, shared, and accessible.</b></p>
</p>


<h2>Money-Pot</h2> 
Money-Pot is a free grocery budgeting web application that helps users manage grocery spending, track purchases, collaborate under a shared budget, discover deals and coupons, and access free food resources. It is designed especially for college students, roommates, couples, and low-income users who need a clear, reliable way to manage shared grocery expenses.
This repository represents the ongoing development of Money-Pot.

<h2>## 📸 Screenshots</h2>

> Early MVP UI (Work in Progress)

<img width="1710" height="987" alt="Screenshot 2026-01-06 at 3 47 47 AM" src="https://github.com/user-attachments/assets/d64d24b2-a6eb-4bd7-bccc-29a6e88e7a93" />
<img width="1710" height="987" alt="Screenshot 2026-01-06 at 3 49 19 AM" src="https://github.com/user-attachments/assets/df4b56b0-9699-4a31-aa95-9b437254c465" />


<h2>🧩 Problem Statement</h2>
Grocery budgeting is a major source of stress in shared households. Many people—especially college students—rely on verbal agreements or loose planning when splitting grocery costs. This often leads to:
Overspending
Confusion over who paid for what
Financial stress and arguments
Poor visibility into shared expenses
At the same time, low-income and food-insecure individuals face additional challenges in finding affordable groceries and accessing free food resources.
Money-Pot solves this by providing a centralized, transparent, and collaborative grocery budgeting system.


<h2>🎯 Target Users</h2>
<h3>Primary Users</h3>
<ul>
<li>College students</li>
<li>Roommates sharing grocery expenses</li>
<li>Couples or partners managing a joint budget</li>
</ul><br>  

<h3>Secondary Users<h3>
<ul>
<li>Low-income households</li>
<li>Food-insecure individuals</li>
<li>Families aiming to reduce grocery spending</li>
</ul>

<h2>🏆 Product Goals</h2>
<p>Primary Goal
Help users create a stable, shared grocery budgeting system that promotes financial awareness, reduces overspending, and improves communication on money and budgeting.</p>
  
<h3>Success Looks Like</h3>
<ol>
<li>Users clearly understand where their grocery money is going</li>
<li>Shared households avoid confusion or conflict over expenses</li>
<li>Users actively reduce unnecessary grocery spending</ul>
<li>Users take advantage of deals, coupons, and free food resources</li>
</ol>

<h1>✨ Core Features (Planned & In Progress)</h1>

<h3>🧑‍🤝‍🧑 Shared Budgeting</h3>
Create weekly or monthly grocery budgets
Invite roommates, partners, or family members
Everyone can add purchases and view shared spending

<h3>🧾 User Accountability</h3>
Track who made each purchase
See when money was spent
Understand how each purchase impacts the shared budget
Encourages transparency and teamwork

<h3>🛒 Grocery Deals & Coupons</h3>
Integration with external APIs for:
Store deals
Coupons
Discounts and promotions
Helps users save money before they shop

<h3>🥗 Free Food Resources</h3>
A dedicated section for:
Local food banks
Free food events
Community kitchens
Free grocery programs
Designed to support low-income and food-insecure users.

<h3>📊 Analytics Dashboard</h3>
Weekly and monthly spending summaries
Category-based spending (produce, meat, snacks, etc.)
Spending trends over time




<h2>🛠️ Current MVP Status</h2>
The current MVP focuses on establishing the backend foundation:
Flask-based web application
CRUD functionality for budget entries
SQLAlchemy ORM with a relational database
Server-side routing (GET/POST)
Dynamic rendering with Jinja2
Deployed web app for testing real-world behavior




<h2>⚠️ Known Limitation & Key Learning</h2>
During deployment, a critical issue was discovered:
budget data entered by one user was visible to others using the same deployed app.
This highlighted an important architectural lesson:
Shared state exists without authentication
User-specific data must be scoped correctly
Authentication and session management are essential for real-world apps
This insight directly informs the next development phase:
user accounts, authentication, and true shared-budget groups.



<h2>🧠 What I’ve Learned So Far</h2>
How shared data behaves in deployed web applications
Why authentication is critical for privacy and trust
How MVPs expose real architectural flaws
How to debug logical and system-level issues
How product requirements influence backend design



<h2>🛠️ Tech Stack</h2>
<ul>
<li>Backend</li>
<li>Python</li>
<li>Flask</li>
<li>SQLAlchemy</li>
<li>SQLite (development)</li>
<li>Frontend</li>
<li>HTML</li>
<li>CSS</li>
<li>Jinja2 Templates</li>
<li>Tools</li>
<li>Git & GitHub</li>
<li>VS Code</li>
</ul>

<h2>🔮 Roadmap</h2>
<ul>
<li>User authentication </li>
<li>shared-budget groups with multiple users</li>
<li>Budget invitations & permissions</li>
<li>Grocery deal & coupon API integration</li>
<li>Free food resource database</li>
<li>Analytics dashboard & visualizations</li>
<li>Production-ready database</li>
</ul>

<h2>🚧 Project Status</h2>
Active Development (MVP → V1)
Money-Pot is under active development and architectural refinement.


<h2>📫 Contact</h2>
<p>Antoine Gualy<br>
gualyantoine@gmail.com<br>
Computer Science Student<br>
Aspiring Software Engineer</p>

