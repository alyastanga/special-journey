import cv2
import qrcode
from pyzbar.pyzbar import decode
import datetime
import sqlite3
import smtplib
import ssl
from email.message import EmailMessage
from PIL import Image, ImageOps

    
email_sender = 'your email'
email_password = 'your password'

def setup_database():
    conn = sqlite3.connect('attendance_systems(2).db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            student_id INTEGER PRIMARY KEY,
            student_name TEXT,
            parent_email TEXT

        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            student_id INTEGER,
            timestamp DATETIME,            FOREIGN KEY (student_id) REFERENCES students (student_id)
        )
    ''')
    conn.commit()
    return conn

def generate_qr_code(student_id, student_name):
    data = f"Student ID: {student_id}\nStudent Name: {student_name}"
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")
    #overlay = Image.open(student_picture)
    #overlay = overlay.resize((50,50))
    #withborder = ImageOps.expand(overlay, border=5, fill="white")

    #position = ((qr_img.size[0]) // 2, (qr_img.size[1]) // 2)
    #qr_img.paste(position)
    qr_img.save(f"student_qr_{student_name}.png")


def send_email_to_parents(parent_email, student_name):
    subject = 'Attendance Notification'
    body = f"{student_name} is marked as present on class at {datetime.datetime.now()}"

    em = EmailMessage()
    em['From'] = email_sender
    em['To'] = parent_email
    em['Subject'] = subject
    em.set_content(body)

    em.add_alternative(body, subtype='html')

    context = ssl.create_default_context()

    with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=context) as smtp:
        smtp.login(email_sender, email_password)
        smtp.sendmail(email_sender, parent_email, em.as_string())
    
    print(f"Email sent to parent:{parent_email}")


def mark_attendance(cursor):
    cap = cv2.VideoCapture(0)
    while True:
        ret, frame = cap.read()
        decoded_objects = decode(frame)
        for obj in decoded_objects:
            data = obj.data.decode('utf-8')

            # Extract student ID and name from QR code data
            student_info = data.split('\n')
            if len(student_info) >= 2:
                student_id = student_info[0].split(': ')[1]
                student_name = student_info[1].split(': ')[1]

                # Record attendance in the database
                cursor.execute('INSERT INTO attendance (student_id, timestamp) VALUES (?, ?)',
                               (student_id, datetime.datetime.now()))
                cursor.connection.commit()

                # Retrieve parent phone number from the database
                cursor.execute('SELECT parent_email FROM students WHERE student_id = ?', (student_id,))
                parent_email = cursor.fetchone()[0]

                # Send SMS to parents
                send_email_to_parents(parent_email, student_name)

        cv2.imshow("Attendance System", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    cap.release()
    cv2.destroyAllWindows()
    
if __name__ == "__main__":
    conn = setup_database()
    cursor = conn.cursor()

    while True:
        option = input("Choose an option (1: Register Student, 2: Mark Attendance, q: Quit): ")

        if option == '1':
            student_name = input("Enter Student Name: ")
            parent_email = input("Parent email address.: ")
            #student_picture = input("input the path: ")

            # Add the student to the database
            cursor.execute('INSERT INTO students (student_name, parent_email) VALUES (?, ?)', (student_name, parent_email))
            cursor.connection.commit()

            # Generate a QR code for the student
            cursor.execute('SELECT student_id FROM students WHERE student_name = ?', (student_name,))
            student_id = cursor.fetchone()[0]
            generate_qr_code(student_id, student_name)

        elif option == '2':
            mark_attendance(cursor)

        elif option.lower() == 'q':
            break

    conn.close()
