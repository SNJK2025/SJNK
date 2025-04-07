# 📖 Library Management System (LMS)

A full-stack web-based Library Management System built using **Flask**, **PostgreSQL**, and **HTML/CSS/JS**. It provides role-based dashboards for **Users** and **Admins**, supports book borrowing, review moderation, analytics, email notifications, and much more.

---

## 🚀 Features

### 👤 User Features
- Register & Login (with password hashing)
- Browse & search available books
- Borrow books with auto-validation based on limit
- View borrowing history & return/renew books
- Submit and view book reviews
- Book reservation and inter-library loan requests
- AI-powered book recommendations
- Email notifications for new books
- User profile editing & subscription toggling

### 🛠️ Admin Features
- Admin dashboard with library statistics
- Add, edit, delete books with cover upload
- Moderate user reviews
- Manage users, staff, and categories
- Adjust system settings (borrow limits, fine rates, etc.)
- View overdue books and impose fines
- Send bulk email announcements
- View audit logs for admin actions
- Generate book usage reports
- Manage inter-library loan (ILL) requests

---

## 🛠️ Tech Stack

- **Backend**: Flask (Python), PostgreSQL, psycopg2
- **Frontend**: HTML, CSS, Bootstrap
- **Email**: Gmail SMTP (with App Passwords)
- **Security**: bcrypt password hashing
- **Logging**: Custom admin audit logs

---

## 🧪 Setup Instructions

### 🔧 Prerequisites

- Python 3.x
- PostgreSQL
- Virtualenv (optional but recommended)

### ⚙️ Database Setup

1. Create a PostgreSQL database named `LM`.
2. Create necessary tables using provided SQL schema (or generate them based on your models).

### 🔌 Environment Setup

```bash
# Clone the repo
git clone https://github.com/yourusername/library-management-system.git
cd library-management-system

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows use venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the app
python app.py
