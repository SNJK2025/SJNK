from flask import *
import psycopg2
import os
import bcrypt
from datetime import date, timedelta
from flask import render_template, request, redirect, url_for, flash
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask_babel import Babel, gettext as _
from flask import g
import logging
from datetime import datetime


app =  Flask(__name__)
app.secret_key = "12233xbjdymzxvgf"

def database_connection():
    conn = psycopg2.connect(
    dbname="LM",
    user="postgres",
    password="414163",
    host="localhost",
    port="5432"
)
    return conn


def log_admin_action(action, admin_email="admin@example.com"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open("admin_audit_log.txt", "a") as f:
        f.write(f"[{timestamp}] {admin_email}: {action}\n")


msg = ""

def send_email_notification(receiver_email, subject, body):
    sender_email = "libraryreminder27@gmail.com"         # Replace with your Gmail
    sender_password = "cxmuxeplqvwchwgw"          # Use Gmail App Password if 2FA is enabled

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, receiver_email, msg.as_string())
        server.quit()
        print(f"Email sent to {receiver_email}")
    except Exception as e:
        print(f"Failed to send email to {receiver_email}: {e}")

@app.route('/')
def root():
    return redirect(url_for('home'))

@app.route("/home", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        try:
            conn = database_connection()
            username = request.form["uname"]
            email = request.form["email"]
            password = request.form["pwd"]

            # 🔐 Hash the password before storing
            hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

            cur = conn.cursor()
            cur.execute("INSERT INTO register_users (username, email, passwd) VALUES (%s, %s, %s)", 
            (username, email, hashed_pw.decode('utf-8')))
            conn.commit()
            cur.close()
            conn.close()

            return render_template("home.html", msg="You have successfully registered yourself")
        except:
            return render_template("home.html", msg="Oops...Something Went Wrong")

    return render_template("home.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["pwd"]

        # Admin login
        if email == "vedant@gmail.com" and password == "123":
            conn = database_connection()
            cur = conn.cursor()
            cur.execute("SELECT * FROM book_repo")
            fetched_books = cur.fetchall()
            return render_template("admin.html", fetched_books=fetched_books)

        # Normal user login
        conn = database_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM register_users")
        all_reg = cur.fetchall()

        for i in all_reg:
            if i[2] == email and bcrypt.checkpw(password.encode('utf-8'), i[3].encode('utf-8')):
                cur.execute("""
                    SELECT 
                        b.*, 
                        CASE 
                            WHEN i.issue_book IS NOT NULL AND i.issue_status = 0 THEN 'Unavailable'
                            ELSE 'Available'
                        END AS availability
                    FROM book_repo b
                    LEFT JOIN (
                        SELECT issue_book, issue_status
                        FROM issued_books
                        WHERE issue_status = 0
                    ) i ON b.book_title = i.issue_book
                """)
                admin_books = cur.fetchall()

                cur.execute("SELECT COUNT(*) FROM register_users")
                active_users = cur.fetchone()

                cur.close()
                conn.close()

                return render_template(
                    "index.html",
                    admin_books=admin_books,
                    active_users=active_users[0],
                    username=i[2]
                )

        conn.commit()
        cur.close()
        conn.close()

        return render_template("home.html", msg="Please register first...")

    return render_template("home.html")

@app.route('/adminscreen')
def adminscreen():
    conn = database_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM book_repo")
    fetched_books = cur.fetchall()

    cur.close()
    conn.close()

    return render_template("admin.html", fetched_books=fetched_books)


@app.route("/upload", methods=["GET", "POST"])
def upload():
    if request.method == "POST":
        conn = database_connection()
        cur = conn.cursor()

        book_title = request.form["title"]
        author_name = request.form["author"]
        genre = request.form["genre"]
        isb_no = request.form["isbn"]
        book = request.files["cover_image"]
        book.save(os.path.join("D:/Vs code/LibManagement/LibManagement/static/images", book.filename))

        cur.execute("""
            INSERT INTO book_repo (book_title, author_name, book_genre, book_isb_no, book_thumbnail)
            VALUES (%s, %s, %s, %s, %s)
        """, (book_title, author_name, genre, isb_no, book.filename))
        conn.commit()

        log_admin_action(f"Uploaded new book: {book_title} by {author_name} (Genre: {genre}, ISBN: {isb_no})")

        cur.execute("SELECT email FROM register_users WHERE is_subscribed = TRUE")
        subscribers = cur.fetchall()

        subject = "New Book Alert from Library!"
        body = f"A new book titled '{book_title}' by {author_name} in '{genre}' genre has just been added to the library. Log in now to borrow it!"

        for email_row in subscribers:
            send_email_notification(email_row[0], subject, body)

        # ✅ Fetch updated book list
        cur.execute("SELECT * FROM book_repo")
        updated_books = cur.fetchall()

        cur.close()
        conn.close()

        msg = "Book is uploaded successfully in repository and alerts sent!"
        return render_template("admin.html", msg=msg, fetched_books=updated_books)
        
@app.route('/requested_books',methods=["GET","POST"])
def requested_books():
    conn = database_connection()
    cur = conn.cursor()
    cur.execute("select * from issued_books where issue_status=0")
    req_books = cur.fetchall()
    print(req_books)
    cur.close()
    conn.close()
    return render_template("requested_books.html",req_books=req_books,msg="")

@app.route('/book_clicked', methods=['POST'])
def book_clicked():
    conn = database_connection()
    cur = conn.cursor()
    book_id = request.form.get('book_id')
    user_id = request.form.get('user_id')

    # Fetch borrow limit from system settings
    cur.execute("SELECT setting_value FROM system_settings WHERE setting_name = 'borrow_limit'")
    borrow_limit = int(cur.fetchone()[0])

    # Count current active borrowed books
    cur.execute("SELECT COUNT(*) FROM issued_books WHERE username = %s AND issue_status = 0", (user_id,))
    current_borrowed = cur.fetchone()[0]

    if current_borrowed >= borrow_limit:
        cur.close()
        conn.close()
        msg = f"You have reached your borrow limit ({borrow_limit} books). Please return books to borrow new ones."
        return render_template("index.html", msg=msg, admin_books=[], active_users=0, username=user_id)

    # Get validity from system settings
    cur.execute("SELECT setting_value FROM system_settings WHERE setting_name = 'book_validity_days'")
    validity = int(cur.fetchone()[0])

    # Proceed to issue book
    cur.execute("INSERT INTO issued_books (username, issue_date, book_validity, issue_status, issue_book) VALUES (%s, %s, %s, %s, %s)", 
                (user_id, date.today(), validity, 0, book_id))

    cur.execute("SELECT * FROM book_repo")
    books = cur.fetchall()
    cur.execute("SELECT COUNT(*) FROM register_users")
    active_users = cur.fetchone()[0]

    conn.commit()
    cur.close()
    conn.close()
    return render_template("index.html", admin_books=books, active_users=active_users, username=user_id, msg="Book request submitted.")



@app.route('/book_issue', methods=['POST'])
def book_issue():
    conn = database_connection()
    cur = conn.cursor()
    user_id = request.form.get('username')
    book_id = request.form.get('bookname')
    cur.execute("update issued_books set issue_status =1 where username=%s and issue_book=%s", (user_id,book_id))
    flash(f"Book {book_id} has been issued to {user_id} successfully...")
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('requested_books'))

# Profile page
@app.route('/profile', methods=['GET'])
def profile():
    username = request.args.get('user')
    conn = database_connection()
    cur = conn.cursor()

    # Fetch user details (id, full name, subscription status)
    cur.execute("SELECT id, username, is_subscribed FROM register_users WHERE email = %s", (username,))
    user_data = cur.fetchone()

    if user_data is None:
        flash("User not found.")
        return redirect(url_for('home'))

    user_id = user_data[0]
    user_name = user_data[1]
    is_subscribed = user_data[2]

    # Fetch borrowing history
    cur.execute("""
        SELECT b.book_title, i.issue_date, 
               i.issue_date + i.book_validity * interval '1 day' as due_date,
               CASE 
                   WHEN i.issue_status = 1 THEN 'Returned'
                   ELSE 'Borrowed'
               END as status
        FROM issued_books i
        JOIN book_repo b ON b.book_title = i.issue_book
        WHERE i.username = %s
        ORDER BY i.issue_date DESC
    """, (username,))
    
    history = cur.fetchall()
    cur.close()
    conn.close()
    
    return render_template('profile.html',
                           history=history,
                           username=username,
                           user_id=user_id,
                           user_name=user_name,
                           is_subscribed=is_subscribed)
    # Edit profile
@app.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    if request.method == 'POST':
        old_email = request.form['old_email']
        name = request.form['uname']
        new_email = request.form['email']
        password = request.form['pwd']

        conn = database_connection()
        cur = conn.cursor()
        cur.execute("""
            UPDATE register_users
            SET username=%s, email=%s, passwd=%s
            WHERE email=%s
        """, (name, new_email, password, old_email))
        conn.commit()
        cur.close()
        conn.close()
        flash('Profile updated successfully!')
        return redirect(url_for('home'))
    
    # GET method - render form
    email = request.args.get('email')
    return render_template('edit_profile.html', user_email=email)
    

@app.route('/search', methods=['GET', 'POST'])
def search():
    conn = database_connection()
    cur = conn.cursor()

    # Fetch categories from book_categories table
    cur.execute("SELECT category_name FROM book_categories")
    genres = [g[0] for g in cur.fetchall()]

    query = "SELECT * FROM book_repo WHERE 1=1"
    params = []

    books = []

    if request.method == 'POST':
        title = request.form.get('title')
        author = request.form.get('author')
        genre = request.form.get('genre')

        if title:
            query += " AND LOWER(book_title) LIKE %s"
            params.append('%' + title.lower() + '%')
        if author:
            query += " AND LOWER(author_name) LIKE %s"
            params.append('%' + author.lower() + '%')
        if genre and genre != "All":
            query += " AND LOWER(book_genre) = %s"
            params.append(genre.lower())

        cur.execute(query, tuple(params))
        books = cur.fetchall()

    cur.close()
    conn.close()

    username = request.args.get('user') or request.form.get('username')

    return render_template("search.html", books=books, genres=genres, username=username )

# Reset password
@app.route("/reset_password", methods=["GET", "POST"])
def reset_password():
    msg = ""
    if request.method == "POST":
        email = request.form["email"]
        new_pwd = request.form["pwd"]
        
        conn = database_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM register_users WHERE email = %s", (email,))
        user = cur.fetchone()

        if user:
            cur.execute("UPDATE register_users SET passwd=%s WHERE email=%s", (new_pwd, email))
            conn.commit()
            msg = "Password updated successfully!"
        else:
            msg = "No user found with this email."
        cur.close()
        conn.close()

    return render_template("reset_password.html", msg=msg)

# Review
@app.route('/review', methods=['GET', 'POST'])
def review():
    conn = database_connection()
    cur = conn.cursor()

    if request.method == 'POST':
        username = request.form['username']
        book_title = request.form['book']
        review = request.form['review']
        rating = int(request.form['rating'])

        cur.execute("""
            INSERT INTO book_reviews (username, book_title, review, rating)
            VALUES (%s, %s, %s, %s)
        """, (username, book_title, review, rating))
        conn.commit()

    # Show reviews (optional)
    # cur.execute("SELECT * FROM book_reviews ORDER BY review_date DESC")
    cur.execute("SELECT * FROM book_reviews WHERE approved=TRUE ORDER BY review_date DESC")
    reviews = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("review.html", reviews=reviews, username=request.args.get("user") or request.form.get("username"))

#  Admin can approve reviws
@app.route('/moderate_reviews', methods=['GET', 'POST'])
def moderate_reviews():
    conn = database_connection()
    cur = conn.cursor()

    if request.method == 'POST':
        action = request.form['action']
        review_id = request.form['review_id']
        
        if action == 'approve':
            cur.execute("UPDATE book_reviews SET approved=TRUE WHERE id=%s", (review_id,))
        elif action == 'delete':
            cur.execute("DELETE FROM book_reviews WHERE id=%s", (review_id,))
        conn.commit()

    cur.execute("SELECT * FROM book_reviews ORDER BY review_date DESC")
    all_reviews = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('moderate_reviews.html', reviews=all_reviews)

# User can suggest book

@app.route('/suggest_book', methods=['GET', 'POST'])
def suggest_book():
    msg = ""
    if request.method == 'POST':
        username = request.form['username']
        title = request.form['title']
        author = request.form['author']
        reason = request.form['reason']

        conn = database_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO book_requests (username, title, author, reason)
            VALUES (%s, %s, %s, %s)
        """, (username, title, author, reason))
        conn.commit()
        cur.close()
        conn.close()
        msg = "Book request submitted successfully."

    return render_template("suggest_book.html", msg=msg)

# The system tracks most borrowed books
@app.route('/popular_books')
def popular_books():
    conn = database_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT b.book_title, b.book_thumbnail, COUNT(i.issue_book) AS borrow_count
        FROM issued_books i
        JOIN book_repo b ON i.issue_book = b.book_title
        GROUP BY b.book_title, b.book_thumbnail
        ORDER BY borrow_count DESC
        LIMIT 5
    """)
    popular = cur.fetchall()
    cur.close()
    conn.close()

    return render_template('popular_books.html', popular=popular)

@app.route('/my_books')
def my_books():
    user = request.args.get("user")

    conn = database_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT issue_book, issue_date, issue_status
        FROM issued_books
        WHERE username = %s AND issue_status = 0
    """, (user,))
    issued = cur.fetchall()
    cur.close()
    conn.close()

    return render_template("my_books.html", books=issued, user=user)

@app.route('/return_book', methods=["POST"])
def return_book():
    book = request.form.get('book')
    user = request.form.get('user')

    conn = database_connection()
    cur = conn.cursor()

    # Mark the book as returned
    cur.execute("""
        UPDATE issued_books 
        SET issue_status = 1 
        WHERE username = %s AND issue_book = %s
    """, (user, book))
    conn.commit()

    #  Check if anyone has reserved this book
    cur.execute("""
        SELECT br.username, ru.email
        FROM book_reservations br
        JOIN register_users ru ON br.username = ru.email
        WHERE br.book_title = %s
    """, (book,))
    reserved_users = cur.fetchall()

    #  Send email notifications to all who reserved
    subject = f"Book Available: {book}"
    body = f"The book '{book}' you reserved is now available. Please login to borrow it."

    for username, email in reserved_users:
        send_email_notification(email, subject, body)

    # Remove reservations for this book after notification 
    cur.execute("DELETE FROM book_reservations WHERE book_title = %s", (book,))
    conn.commit()

    cur.close()
    conn.close()

    flash(f"Book '{book}' successfully returned.")
    return redirect(url_for('my_books', user=user))

# Admin can impose fines for overdue books

@app.route('/calculate_fines')
def calculate_fines():
    conn = database_connection()
    cur = conn.cursor()

    # fine_per_day = 5  # Set your fine per overdue day

    cur.execute("SELECT setting_value FROM system_settings WHERE setting_name = 'fine_per_day'")
    fine_per_day = int(cur.fetchone()[0])

    cur.execute("""
        SELECT id, username, issue_book, issue_date, book_validity, issue_status, fine, payment_status
        FROM issued_books
        WHERE issue_status = 1
    """)

    rows = cur.fetchall()
    fined_records = []

    for row in rows:
        issue_id, username, book, issue_date, validity, status, fine, payment_status = row
        due_date = issue_date + timedelta(days=validity)
        today = date.today()
        overdue_days = (today - due_date).days
        calc_fine = fine_per_day * overdue_days if overdue_days > 0 else 0

        # Update DB fine if not already correct
        if calc_fine != fine:
            cur.execute("UPDATE issued_books SET fine = %s WHERE id = %s", (calc_fine, issue_id))
            fine = calc_fine

        if fine > 0:
            fined_records.append({
                "issue_id": issue_id,
                "username": username,
                "book": book,
                "issue_date": issue_date,
                "due_date": due_date,
                "fine": fine,
                "payment_status": payment_status
            })

    conn.commit()
    cur.close()
    conn.close()

    return render_template("fines.html", fines=fined_records)

# Users can pay fines online 
@app.route('/pay_fine', methods=["POST"])
def pay_fine():
    issue_id = request.form.get("issue_id")

    conn = database_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE issued_books SET payment_status = 'Paid'
        WHERE id = %s
    """, (issue_id,))
    conn.commit()
    cur.close()
    conn.close()

    log_admin_action(f"Marked fine as paid for issue ID: {issue_id}")

    flash("Fine marked as paid successfully.")
    return redirect(url_for('calculate_fines'))

@app.route('/edit_book/<int:book_id>')
def edit_book(book_id):
    conn = database_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM book_repo WHERE id = %s", (book_id,))
    book = cur.fetchone()
    cur.close()
    conn.close()
    return render_template("edit_book.html", book=book)


@app.route('/update_book', methods=["POST"])
def update_book():
    book_id = request.form["book_id"]
    title = request.form["title"]
    author = request.form["author"]
    genre = request.form["genre"]
    isbn = request.form["isbn"]

    cover_image = request.files["cover_image"]
    new_cover_name = None

    if cover_image and cover_image.filename != '':
        new_cover_name = cover_image.filename
        cover_image.save(os.path.join("static/images", new_cover_name))

    conn = database_connection()
    cur = conn.cursor()
    
    if new_cover_name:
        cur.execute("""
            UPDATE book_repo
            SET book_title=%s, author_name=%s, book_genre=%s, book_isb_no=%s, book_thumbnail=%s
            WHERE id=%s
        """, (title, author, genre, isbn, new_cover_name, book_id))
    else:
        cur.execute("""
            UPDATE book_repo
            SET book_title=%s, author_name=%s, book_genre=%s, book_isb_no=%s
            WHERE id=%s
        """, (title, author, genre, isbn, book_id))

    conn.commit()
    cur.close()
    conn.close()
    log_admin_action(f"Updated book ID: {book_id}, Title: {title}, Author: {author}")
    return redirect(url_for("login"))  # This will reload books in admin.html

# admin can delete books

@app.route('/delete_book', methods=['POST'])
def delete_book():
    book_id = request.form.get('book_id')

    conn = database_connection()
    cur = conn.cursor()

    # Delete cover image (optional cleanup)
    cur.execute("SELECT book_thumbnail FROM book_repo WHERE id = %s", (book_id,))
    result = cur.fetchone()
    if result:
        image_file = result[0]
        image_path = os.path.join("static/images", image_file)
        if os.path.exists(image_path):
            os.remove(image_path)

    # Delete the book
    cur.execute("DELETE FROM book_repo WHERE id = %s", (book_id,))
    conn.commit()

    log_admin_action(f"Deleted book ID: {book_id}")

    # Fetch updated list of books
    cur.execute("SELECT * FROM book_repo")
    updated_books = cur.fetchall()

    cur.close()
    conn.close()

    flash("Book deleted successfully.")
    return render_template("admin.html", fetched_books=updated_books, msg="")
 
# #  Users can renew borrowed books
@app.route('/renew_book', methods=['POST'])
def renew_book():
    username = request.form['user']
    bookname = request.form['book']

    conn = database_connection()
    cur = conn.cursor()

    # Check if the same book is requested by another user (status 0)
    cur.execute("""
        SELECT COUNT(*) FROM issued_books 
        WHERE issue_book = %s AND username != %s AND issue_status = 0
    """, (bookname, username))
    reserved = cur.fetchone()[0]

    if reserved > 0:
        flash("Cannot renew. Another user has reserved this book.")
    else:
        # Extend validity by 7 days
        cur.execute("""
            UPDATE issued_books 
            SET book_validity = book_validity + 7 
            WHERE username = %s AND issue_book = %s AND issue_status = 1
        """, (username, bookname))
        flash("Book renewed successfully for 7 more days.")

    conn.commit()
    cur.close()
    conn.close()

    return render_template("my_books.html", user=username)  

# Admin can manage user accounts
@app.route('/admin/users')
def manage_users():
    conn = database_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, username, email, is_active FROM register_users")
    users = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("manage_users.html", users=users)


@app.route('/admin/create_user', methods=["POST"])
def create_user():
    username = request.form['username']
    email = request.form['email']
    password = request.form['password']

    conn = database_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO register_users (username, email, passwd, is_active) VALUES (%s, %s, %s, TRUE)", (username, email, password))
    conn.commit()
    cur.close()
    conn.close()

    log_admin_action(f"Created user: {email}")
    flash("User created successfully.")
    return redirect(url_for('manage_users'))


@app.route('/admin/update_user/<int:user_id>', methods=["POST"])
def update_user(user_id):
    username = request.form['username']
    email = request.form['email']

    conn = database_connection()
    cur = conn.cursor()
    cur.execute("UPDATE register_users SET username = %s, email = %s WHERE id = %s", (username, email, user_id))
    conn.commit()
    cur.close()
    conn.close()

    log_admin_action(f"Updated user ID: {user_id} to email: {email}")
    flash("User updated successfully.")
    return redirect(url_for('manage_users'))


@app.route('/admin/deactivate_user/<int:user_id>', methods=["POST"])
def deactivate_user(user_id):
    conn = database_connection()
    cur = conn.cursor()
    cur.execute("UPDATE register_users SET is_active = FALSE WHERE id = %s", (user_id,))
    conn.commit()
    cur.close()
    conn.close()
    flash("User deactivated successfully.")
    return redirect(url_for('manage_users'))

@app.route('/admin/reactivate_user/<int:user_id>', methods=["POST"])
def reactivate_user(user_id):
    conn = database_connection()
    cur = conn.cursor()
    cur.execute("UPDATE register_users SET is_active = TRUE WHERE id = %s", (user_id,))
    conn.commit()
    cur.close()
    conn.close()
    flash("User reactivated successfully.")
    return redirect(url_for('manage_users'))

# Admin can manage book categories
@app.route('/admin/categories')
def manage_categories():
    conn = database_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM book_categories")
    categories = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("manage_categories.html", categories=categories)


@app.route('/admin/add_category', methods=["POST"])
def add_category():
    name = request.form['category_name']
    conn = database_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO book_categories (category_name) VALUES (%s)", (name,))
    conn.commit()
    cur.close()
    conn.close()
    log_admin_action(f"Added category: {name}")
    flash("Category added successfully.")
    return redirect(url_for('manage_categories'))


@app.route('/admin/update_category/<int:cat_id>', methods=["POST"])
def update_category(cat_id):
    name = request.form['category_name']
    conn = database_connection()
    cur = conn.cursor()
    cur.execute("UPDATE book_categories SET category_name = %s WHERE id = %s", (name, cat_id))
    conn.commit()
    cur.close()
    conn.close()
    flash("Category updated successfully.")
    return redirect(url_for('manage_categories'))


@app.route('/admin/delete_category/<int:cat_id>', methods=["POST"])
def delete_category(cat_id):
    conn = database_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM book_categories WHERE id = %s", (cat_id,))
    conn.commit()
    cur.close()
    conn.close()

    log_admin_action(f"Deleted category ID: {cat_id}")
    flash("Category deleted.")
    return redirect(url_for('manage_categories'))


# Admin can customize system settings
@app.route('/admin/system_settings', methods=['GET', 'POST'])
def system_settings():
    conn = database_connection()
    cur = conn.cursor()

    if request.method == 'POST':
        borrow_limit = request.form.get('borrow_limit')
        validity_days = request.form.get('book_validity_days')
        fine_per_day = request.form.get('fine_per_day')

        cur.execute("UPDATE system_settings SET setting_value = %s WHERE setting_name = 'borrow_limit'", (borrow_limit,))
        cur.execute("UPDATE system_settings SET setting_value = %s WHERE setting_name = 'book_validity_days'", (validity_days,))
        cur.execute("UPDATE system_settings SET setting_value = %s WHERE setting_name = 'fine_per_day'", (fine_per_day,))
        conn.commit()

        log_admin_action(
            f"Updated system settings: borrow_limit={borrow_limit}, book_validity_days={validity_days}, fine_per_day={fine_per_day}"
        )
        flash("Settings updated successfully.")

    cur.execute("SELECT setting_name, setting_value FROM system_settings")
    settings = {row[0]: row[1] for row in cur.fetchall()}

    cur.close()
    conn.close()
    return render_template("system_settings.html", settings=settings)

# Users get notifications for newly added books

@app.route('/toggle_subscription', methods=['POST'])
def toggle_subscription():
    user_id = request.form.get("user_id")
    if not user_id:
        flash("Invalid user. Please log in again.")
        return redirect(url_for('home'))

    is_subscribed = 'is_subscribed' in request.form

    conn = database_connection()
    cur = conn.cursor()
    cur.execute("UPDATE register_users SET is_subscribed = %s WHERE id = %s", (is_subscribed, user_id))
    conn.commit()
    cur.close()
    conn.close()

    flash("Subscription preference updated.")
    return redirect(url_for('profile'))


# Admin can send bulk emails to users

@app.route('/admin/send_email', methods=['GET', 'POST'])
def send_bulk_email():
    if request.method == 'POST':
        subject = request.form.get('subject')
        message = request.form.get('message')
        recipient_type = request.form.get('recipient_type')

        conn = database_connection()
        cur = conn.cursor()

        if recipient_type == 'subscribed':
            cur.execute("SELECT email FROM register_users WHERE is_subscribed = TRUE")
        else:
            cur.execute("SELECT email FROM register_users")

        recipients = cur.fetchall()
        cur.close()
        conn.close()

        for r in recipients:
            send_email_notification(r[0], subject, message)

        flash("Bulk email sent successfully.")
        return redirect(url_for('send_bulk_email'))

    return render_template("bulk_email.html")

# Admin can generate reports on book usage
@app.route('/admin/report')
def generate_report():
    conn = database_connection()
    cur = conn.cursor()

    # Fetch book usage statistics
    cur.execute("""
        SELECT 
            b.book_title, 
            COUNT(i.issue_book) AS times_borrowed
        FROM issued_books i
        JOIN book_repo b ON i.issue_book = b.book_title
        GROUP BY b.book_title
        ORDER BY times_borrowed DESC
    """)
    usage_stats = cur.fetchall()

    cur.close()
    conn.close()
    return render_template('book_usage_report.html', usage_stats=usage_stats)

# Auto-suggests book titles as users type in the search bar

@app.route('/suggest_titles')
def suggest_titles():
    query = request.args.get('q', '').lower()
    conn = database_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT DISTINCT book_title 
        FROM book_repo 
        WHERE LOWER(book_title) LIKE %s
        LIMIT 10
    """, ('%' + query + '%',))
    results = cur.fetchall()
    cur.close()
    conn.close()

    suggestions = [r[0] for r in results]
    return jsonify(suggestions)

# Users can reserve books

@app.route('/reserve_book', methods=["POST"])
def reserve_book():
    username = request.form.get("username")
    book_title = request.form.get("book_title")

    conn = database_connection()
    cur = conn.cursor()

    # Check if already reserved
    cur.execute("""
        SELECT * FROM book_reservations
        WHERE username = %s AND book_title = %s AND notified = FALSE
    """, (username, book_title))
    already_reserved = cur.fetchone()

    if already_reserved:
        flash("You’ve already reserved this book.")
    else:
        cur.execute("""
            INSERT INTO book_reservations (username, book_title)
            VALUES (%s, %s)
        """, (username, book_title))
        flash("Book reserved. You’ll be notified when it becomes available.")

    conn.commit()
    cur.close()
    conn.close()

    return redirect(url_for('search'))


# Admin can manage staff accounts

@app.route('/admin/staff')
def manage_staff():
    conn = database_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, username, email, role FROM register_users WHERE role = 'staff'")
    staff = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("manage_staff.html", staff=staff)

@app.route('/admin/promote_to_staff/<int:user_id>', methods=['POST'])
def promote_to_staff(user_id):
    conn = database_connection()
    cur = conn.cursor()
    cur.execute("UPDATE register_users SET role = 'staff' WHERE id = %s", (user_id,))
    conn.commit()
    cur.close()
    conn.close()
    flash("User promoted to staff.")
    return redirect(url_for('manage_staff'))  # or 'manage_staff'

@app.route('/admin/demote_staff/<int:user_id>', methods=['POST'])
def demote_staff(user_id):
    conn = database_connection()
    cur = conn.cursor()
    cur.execute("UPDATE register_users SET role = 'user' WHERE id = %s", (user_id,))
    conn.commit()
    cur.close()
    conn.close()
    flash("Staff demoted to user.")
    return redirect(url_for('manage_staff'))

# AI recommends books based on user reading patterns.
@app.route('/recommendations')
def recommend_books():
    user = request.args.get("user")

    conn = database_connection()
    cur = conn.cursor()

    # Get all genres of books user borrowed
    cur.execute("""
        SELECT DISTINCT b.book_genre 
        FROM issued_books i 
        JOIN book_repo b ON i.issue_book = b.book_title 
        WHERE i.username = %s
    """, (user,))
    genres = [row[0] for row in cur.fetchall()]

    # Fetch recommended books not yet borrowed by user
    cur.execute("""
        SELECT * FROM book_repo 
        WHERE book_genre = ANY(%s) 
        AND book_title NOT IN (
            SELECT issue_book FROM issued_books WHERE username = %s
        )
    """, (genres, user))

    recommendations = cur.fetchall()
    cur.close()
    conn.close()

    return render_template("recommendations.html", recommendations=recommendations, user=user)

# Users can request inter-library loans
@app.route('/inter_library_request', methods=['GET', 'POST'])
def inter_library_request():
    if request.method == 'POST':
        username = request.form['username']
        book_title = request.form['book_title']
        author = request.form.get('author')
        reason = request.form['reason']

        conn = database_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO inter_library_loans (username, book_title, author, reason)
            VALUES (%s, %s, %s, %s)
        """, (username, book_title, author, reason))
        conn.commit()
        cur.close()
        conn.close()
        flash("Your inter-library loan request has been submitted.")
        return redirect(url_for('inter_library_request'))

    return render_template("inter_library_request.html")


@app.route('/admin/inter_library_loans')
def view_ill_requests():
    conn = database_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM inter_library_loans ORDER BY request_date DESC")
    requests = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("manage_ill_requests.html", requests=requests)

# Maintains an audit log of admin activities.

@app.route('/admin/audit_logs')
def view_audit_logs():
    try:
        with open("admin_audit_log.txt", "r") as f:
            logs = f.readlines()
    except FileNotFoundError:
        logs = []
    return render_template("audit_logs.html", logs=logs)

# Admin can track overdue books
@app.route('/admin/overdue_books')
def overdue_books():
    conn = database_connection()
    cur = conn.cursor()

    # Fetch fine per day from settings (optional)
    cur.execute("SELECT setting_value FROM system_settings WHERE setting_name = 'fine_per_day'")
    fine_per_day = int(cur.fetchone()[0])

    # Fetch overdue books
    cur.execute("""
        SELECT 
            i.id,
            i.username,
            r.email,
            i.issue_book,
            i.issue_date,
            i.book_validity,
            i.issue_status,
            i.fine,
            (CURRENT_DATE - (i.issue_date + i.book_validity * interval '1 day')) AS overdue_days
        FROM issued_books i
        JOIN register_users r ON i.username = r.email
        WHERE i.issue_status = 0 AND CURRENT_DATE > (i.issue_date + i.book_validity * interval '1 day')
    """)

    overdue_list = []
    for row in cur.fetchall():
        overdue_days = int(row[8])
        fine = fine_per_day * overdue_days
        overdue_list.append({
            "issue_id": row[0],
            "username": row[1],
            "email": row[2],
            "book": row[3],
            "issue_date": row[4],
            "due_date": row[4] + timedelta(days=row[5]),
            "overdue_days": overdue_days,
            "fine": fine
        })

    cur.close()
    conn.close()

    return render_template("overdue_books.html", overdue_list=overdue_list)

# The System displays library statistics
@app.route('/admin/dashboard')
def admin_dashboard():
    conn = database_connection()
    cur = conn.cursor()

    # Total users
    cur.execute("SELECT COUNT(*) FROM register_users")
    total_users = cur.fetchone()[0]

    # Active users
    cur.execute("SELECT COUNT(*) FROM register_users WHERE is_active = TRUE")
    active_users = cur.fetchone()[0]

    # Total books
    cur.execute("SELECT COUNT(*) FROM book_repo")
    total_books = cur.fetchone()[0]

    # Borrowed books
    cur.execute("SELECT COUNT(*) FROM issued_books WHERE issue_status = 0")
    borrowed_books = cur.fetchone()[0]

    # Overdue books
    cur.execute("""
        SELECT COUNT(*) FROM issued_books 
        WHERE issue_status = 0 AND CURRENT_DATE > (issue_date + book_validity * interval '1 day')
    """)
    overdue_books = cur.fetchone()[0]

    cur.close()
    conn.close()

    return render_template("dashboard.html",
                           total_users=total_users,
                           active_users=active_users,
                           total_books=total_books,
                           borrowed_books=borrowed_books,
                           overdue_books=overdue_books)


@app.route('/homescreen')
def homescreen():
    username = request.args.get("user")
    if not username:
        return redirect(url_for('home'))

    conn = database_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT 
            b.*, 
            CASE 
                WHEN i.issue_book IS NOT NULL AND i.issue_status = 0 THEN 'Unavailable'
                ELSE 'Available'
            END AS availability
        FROM book_repo b
        LEFT JOIN (
            SELECT issue_book, issue_status
            FROM issued_books
            WHERE issue_status = 0
        ) i ON b.book_title = i.issue_book
    """)
    admin_books = cur.fetchall()

    cur.execute("SELECT COUNT(*) FROM register_users")
    active_users = cur.fetchone()

    cur.close()
    conn.close()

    return render_template("index.html", 
                           admin_books=admin_books, 
                           active_users=active_users[0], 
                           username=username)

if __name__ == '__main__':
    app.run(host="0.0.0.0", debug=True)

    