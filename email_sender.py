import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config.email_config import EMAIL_ADDRESS, EMAIL_PASSWORD, SMTP_SERVER, SMTP_PORT


def send_unlock_email(to_email, unlock_link):
    # sends unlock email to user, link expires in 15 mins
    
    subject = "AuthShield — Account Unlock Request"
    body = f"""
    <html>
        <body style="font-family: Arial, sans-serif; color: #333;">
            <p>Hello,</p>
            <p>We detected multiple failed login attempts on your AuthShield account.</p>
            <p>To unlock your account, click the link below:</p>
            <p>
                <a href="{unlock_link}" style="color: #0077ff;">{unlock_link}</a>
            </p>
            <p><strong>This link will expire in 15 minutes.</strong></p>
            <p>If you did not attempt to log in, please ignore this email.</p>
            <br>
            <p>— AuthShield Security</p>
        </body>
    </html>
    """

    msg = MIMEMultipart()
    msg['From'] = f"AuthShield Security <{EMAIL_ADDRESS}>"
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'html'))

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.send_message(msg)
            print(f"[INFO] Unlock email sent to {to_email} at {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    except Exception as e:
        print(f"[ERROR] Could not send unlock email to {to_email}: {e}")
