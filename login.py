import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def send_email(recipient_email, subject, message):
    sender_email = "hariharakrishnan117@gmail.com"  # Replace with your email
    sender_password = "einn jmhq fehl pabr"  # Use App Password if using Gmail

    # Setup the MIME
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Subject'] = subject
    msg.attach(MIMEText(message, 'plain'))

    try:
        # Connect to the server
        server = smtplib.SMTP('smtp.gmail.com', 587)  # For Gmail
        server.starttls()  # Secure the connection
        server.login(sender_email, sender_password)  # Login

        # Send email
        server.send_message(msg)
        server.quit()
        print("Email sent successfully!")

    except Exception as e:
        print(f"Failed to send email: {str(e)}")

send_email("krishnan.hari@zappyworks.com", "Test Subject", "Hello! This is a test email.")
