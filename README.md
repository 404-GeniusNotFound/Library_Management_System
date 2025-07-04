# 📚 Library Management System  
**Modern Application Development - I**  
*Submission Date: January 2023*

---

## 🧩 Objective

Build a fully functional, multi-user **Library Management System** for managing and issuing **e-books**. The application should support both **librarian** and **general user** workflows, including section and book management, login functionality, and basic search features.

---

## 🔧 Tech Stack

- **Flask**: Web framework for routing and backend logic  
- **Jinja2 + Bootstrap**: HTML templating and responsive styling  
- **SQLite**: Lightweight database for local storage  
- **Python (Core)**: Business logic and data manipulation  
- **HTML/CSS/JS**: Frontend development  

---

## 🧑‍💼 Roles & Features

### 🔐 User Authentication
- Simple login form with role-based access (User / Librarian)
- Optional: Separate registration/login for users

---

## 📚 General User Functionalities

- ✅ Login/Register as a user  
- ✅ Browse available **sections** and **e-books**  
- ✅ **Request / Return** e-books (max 5 at a time)  
- ✅ Auto-revoke access after a specified time (e.g., 7 days)  
- ✅ Leave **feedback** for e-books  
- ✅ Search by section, author, or keywords

---

## 🧑‍🏫 Librarian Functionalities

- ✅ Login as a librarian  
- ✅ Add, edit, delete **sections** and **e-books**  
- ✅ Issue or revoke access to books for users  
- ✅ Assign books to sections  
- ✅ Monitor user activity and issued books  
- ✅ CRUD operations via dashboard  
- ✅ Optional: UTF-8 handling for multilingual books  

---

## 🔍 Search System

- 🔎 Search e-books by:
  - Section
  - Author
  - Book title  
- 🔎 Section-level browsing and book filtering

---

## 💡 Advanced Features (Implemented)

- 📥 **Downloadable PDF** format for e-books  
- ⚙️ **RESTful APIs** for CRUD operations on sections and books  
- 📊 Librarian Dashboard with status tracking and optional graphs  
- 🛡️ **Form Validation** (frontend + backend)

---

## ✨ Optional Features (Bonus)

- 🎨 Enhanced UI using Bootstrap  
- 🔊 Text-to-speech reading capability for books  
- 🔐 Full authentication flow with session tracking  
- 💰 Paid version or subscription plans (future scope)

---

## 🧱 Data Models

### 👤 User
- `user_id`, `username`, `password`, `role`, `registered_on`

### 📁 Section
- `section_id`, `name`, `description`, `created_on`

### 📖 Book
- `book_id`, `title`, `content`, `author`, `section_id`, `date_issued`, `return_date`

### 🔄 Transactions
- Tracks issued books, return status, and expiration auto-revoke logic

---

## 🧪 Testing & Evaluation

- Fully tested locally on IDE (VS Code) with SQLite
- No external servers or setup required
- Minimal dependencies
- Report and walkthrough video included as per guidelines

---

## 📦 Submission Contents

- 📁 `app/`: Flask application folder (routes, templates, static)  
- 🗃️ `library.db`: SQLite database  
- 📄 `README.md`: Project description  
- 📹 `demo.mp4`: Project walkthrough video  
- 📄 `report.pdf`: System design & model overview  

---

## 🗣️ Final Thoughts

This project helped in understanding full-stack development using Flask. It integrates templating, backend logic, database operations, and user interaction in a complete end-to-end solution. The system is modular, extensible, and ready for future improvements like email notifications, mobile compatibility, or integration with cloud databases.

