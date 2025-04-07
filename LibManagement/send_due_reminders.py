import psycopg2
import smtplib
from email.message import EmailMessage
from datetime import date, timedelta

def database_connection():
    print("Connecting to the database...")
    return psycopg2.connect(
        dbname="LM",
        user="postgres",
        password="414163",
        host="localhost",
        port="5432"
    )

def send_email(to_email, subject, content):
    print(f"Preparing to send email to {to_email} with subject: '{subject}'")
    msg = EmailMessage()
    msg.set_content(content)
    msg['Subject'] = subject
    msg['From'] = "libraryreminder27@gmail.com"
    msg['To'] = to_email

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login("libraryreminder27@gmail.com", "cxmuxeplqvwchwgw")
            smtp.send_message(msg)
        print(f"✅ Email successfully sent to {to_email}")
    except Exception as e:
        print(f"❌ Failed to send email to {to_email}. Error: {e}")

def send_due_date_reminders():
    try:
        conn = database_connection()
        cur = conn.cursor()
        today = date.today()

        print("Fetching records for due date reminders...")
        cur.execute("""
            SELECT i.username, u.email, i.issue_book, i.issue_date, i.book_validity
            FROM issued_books i
            JOIN register_users u ON i.username = u.email
            WHERE i.issue_status = 0
        """)

        records = cur.fetchall()
        print(f"🔍 Found {len(records)} active issued book(s).")

        for username, email, book, issue_date, validity in records:
            due_date = issue_date + timedelta(days=validity)
            days_left = (due_date - today).days

            print(f"\n📚 Book: {book}")
            print(f"👤 User: {username}, 📧 Email: {email}")
            print(f"📅 Issue Date: {issue_date}, Due Date: {due_date} ({days_left} day(s) left)")

            if days_left == 2:
                send_email(
                    email,
                    f"Reminder: '{book}' is due in 2 days",
                    f"Hi {username},\n\nJust a reminder: the book '{book}' is due in 2 days on {due_date}.\n\n- Library Team"
                )
            elif days_left == 0:
                send_email(
                    email,
                    f"Reminder: '{book}' is due today",
                    f"Hi {username},\n\nThe book '{book}' is due today ({due_date}). Please return it to avoid late fees.\n\n- Library Team"
                )
            elif days_left < 0:
                send_email(
                    email,
                    f"Overdue: '{book}' is overdue",
                    f"Hi {username},\n\nThe book '{book}' was due on {due_date} and is now overdue. Kindly return it ASAP.\n\n- Library Team"
                )
            else:
                print("ℹ️ No email needed today.")

        cur.close()
        conn.close()
        print("\n✅ All reminders processed successfully.")

    except Exception as e:
        print(f"\n❌ An error occurred during reminder processing: {e}")

if __name__ == "__main__":
    print("📬 Starting the Library Due Date Reminder Script...\n")
    send_due_date_reminders()