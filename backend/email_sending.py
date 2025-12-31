import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content, TrackingSettings, ClickTracking, OpenTracking
from sentry_sdk import capture_exception, capture_message
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from sentry_sdk import capture_exception
import html
from dotenv import load_dotenv

load_dotenv()

SG_API_KEY = os.getenv('SENDGRID_API_KEY')
FROM_EMAIL = "no-reply@rezify.ai"
FROM_NAME  = "Rezify"

def _sg_client():
    return SendGridAPIClient(SG_API_KEY)

def _disable_tracking(mail: Mail):
    # Keep OTP/transactional emails clean (no rewritten links, no open pixels)
    ts = TrackingSettings()
    ts.click_tracking = ClickTracking(False, False)
    ts.open_tracking = OpenTracking(False)
    mail.tracking_settings = ts

def _send(mail: Mail, log_success: str, log_fail: str):
    try:
        _disable_tracking(mail)
        resp = _sg_client().send(mail)
        if 200 <= resp.status_code < 300:
            capture_message(log_success, level="info")
            return True
        else:
            capture_message(log_fail, level="error")
            return False
    except Exception as e:
        capture_exception(e)
        capture_message(log_fail, level="error")
        return False

def send_info_email_sendgrid(email, subject, first_name, body):
    safe_email = email.replace('@', '[@]').replace('.', '[.]')

    try:
        first_name = (first_name or "").strip()
        if first_name:
            first_name = first_name[0:1].upper() + first_name[1:].lower()

        plain_text = f"""{body}"""

        html_content = f"""\
    <html>
    <body style="font-family: Arial, sans-serif; color: #333;">
        <div style="max-width: 600px; margin: auto; padding: 20px; border: 1px solid #eee; border-radius: 8px;">
            <h1>Hi {first_name}!</h1>
            <p>{body}</p>
            <p>If you have any questions, reply to this email or contact us at <a href="mailto:support@rezify.ai">support@rezify.ai</a>.</p>
            <hr style="margin: 20px 0;">
            <p style="font-size: 12px; color: #777; text-align: center;">
                &copy; 2024 Rezify | <a href="https://rezify.ai" style="color: #777;">rezify.ai</a>
            </p>
        </div>
    </body>
    </html>
    """

        mail = Mail(
            from_email=Email(FROM_EMAIL, FROM_NAME),
            to_emails=To(email),
            subject=subject,
            plain_text_content=Content("text/plain", plain_text),
            html_content=Content("text/html", html_content)
        )

        return _send(mail, f"Info email sent successfully ({safe_email})",
                     f"ERROR: Failed info email ({safe_email})")

    except Exception as e:
        capture_exception(e)
        capture_message(f"ERROR: Failed info email ({safe_email})", level="error")
        return False

def send_verification_email_sendgrid(email, code):
    safe_email = email.replace('@', '[@]').replace('.', '[.]')

    try:
        subject = "Your Rezify Email Verification Code"

        plain_text = f"""\
    Hi there,
    
    Thank you for creating a Rezify account!
    
    Your unique verification code is: {code}
    
    Please enter this code to verify your email address. It will expire in 10 minutes.
    
    If you have any questions, feel free to contact us at support@rezify.ai or visit https://rezify.ai.
    
    – The Rezify Team
    """

        html_content = f"""\
    <html>
    <body style="font-family: Arial, sans-serif; color: #333;">
        <div style="max-width: 600px; margin: auto; padding: 20px; border: 1px solid #eee; border-radius: 8px;">
            <h2 style="color: #ff4500;">Welcome to Rezify!</h2>
            <p>Thank you for creating a Rezify account.</p>
            <p>To complete your registration, please use the following verification code:</p>
            <div style="font-size: 24px; font-weight: bold; background-color: #f9f9f9; padding: 12px; text-align: center; margin: 20px 0;">
                {code}
            </div>
            <p>This code will expire in 10 minutes.</p>
            <p>If you have any questions, reply to this email or contact us at <a href="mailto:support@rezify.ai">support@rezify.ai</a>.</p>
            <hr style="margin: 20px 0;">
            <p style="font-size: 12px; color: #777; text-align: center;">
                &copy; 2024 Rezify | <a href="https://rezify.ai" style="color: #777;">rezify.ai</a>
            </p>
        </div>
    </body>
    </html>
    """

        mail = Mail(
            from_email=Email(FROM_EMAIL, FROM_NAME),
            to_emails=To(email),
            subject=subject,
            plain_text_content=Content("text/plain", plain_text),
            html_content=Content("text/html", html_content)
        )

        return _send(mail, f"REGISTRATION STEP 2 ({safe_email}). Verification email sent successfully.",
                     f"ERROR: Failed verification email. ({safe_email})")
    except Exception as e:
        capture_exception(e)
        capture_message(f"ERROR: Failed verification email. ({safe_email})", level="error")
        return False

def send_recovery_email_sendgrid(email, code):
    safe_email = email.replace('@', '[@]').replace('.', '[.]')

    try:
        subject = "Rezify Account Recovery"

        plain_text = f"""\
    Hi there,
    
    We received a request to reset your Rezify account password.
    
    Your recovery code is: {code}
    
    Please enter this code to change your password. It will expire in 10 minutes.
    
    If you did not request this, you can safely ignore this email.
    
    – The Rezify Team
    """

        html_content = f"""\
    <html>
    <body style="font-family: Arial, sans-serif; color: #333;">
        <div style="max-width: 600px; margin: auto; padding: 20px; border: 1px solid #eee; border-radius: 8px;">
            <h2 style="color: #ff4500;">Reset Your Rezify Password</h2>
            <p>We received a request to reset your Rezify account password.</p>
            <p>Your recovery code is:</p>
            <div style="font-size: 24px; font-weight: bold; background-color: #f9f9f9; padding: 12px; text-align: center; margin: 20px 0;">
                {code}
            </div>
            <p>Please enter this code to change your password. It will expire in 10 minutes.</p>
            <p>If you did not request this, you can safely ignore this email.</p>
            <hr style="margin: 20px 0;">
            <p style="font-size: 12px; color: #777; text-align: center;">
                &copy; 2024 Rezify | <a href="https://rezify.ai" style="color: #777;">rezify.ai</a>
            </p>
        </div>
    </body>
    </html>
    """

        mail = Mail(
            from_email=Email(FROM_EMAIL, FROM_NAME),
            to_emails=To(email),
            subject=subject,
            plain_text_content=Content("text/plain", plain_text),
            html_content=Content("text/html", html_content)
        )

        return _send(mail, f"({safe_email}). Recovery email sent successfully.",
                 f"ERROR: Failed recovery email. ({safe_email})")

    except Exception as e:
        capture_exception(e)
        capture_message(f"ERROR: Failed recovery email. ({safe_email})", level="error")
        return False


def send_demo_request_email_sendgrid(form):
    try:
        subject = "Rezify Demo Request – " + str(form['name']) + " at " + str(form['university'])

        plain_text = f"""\
    We have received a new demo request from {form['name']} at {form['university']}.
    
    University: {form['university']}
    Name: {form['name']}
    Position: {form['position']}
    Email: {form['email']}
    Questions: {form['questions']}
    """

        html_content = f"""\
    <html>
    <body style="font-family: Arial, sans-serif; color: #333;">
        <div style="max-width: 600px; margin: auto; padding: 20px; border: 1px solid #eee; border-radius: 8px;">
            <h2 style="color: #ff4500;">Rezify Demo Request</h2>
            <p>We have received a new demo request from {form['name']} at {form['university']}.</p>
    
            <table style="border-spacing: 10px">
                <tr>
                    <td style="font-weight: bold; vertical-align: top; padding: 10px">University:</td>
                    <td style="background-color: #f9f9f9; padding: 12px; text-align: left;">
                        {form['university']}
                    </td>
                </tr>
                <tr>
                    <td style="font-weight: bold; vertical-align: top; padding: 10px">Name:</td>
                    <td style="background-color: #f9f9f9; padding: 12px; text-align: left;">
                        {form['name']}
                    </td>
                </tr>
                <tr>
                    <td style="font-weight: bold; vertical-align: top; padding: 10px">Position:</td>
                    <td style="background-color: #f9f9f9; padding: 12px; text-align: left;">
                        {form['position']}
                    </td>
                </tr>
                <tr>
                    <td style="font-weight: bold; vertical-align: top; padding: 10px">Email:</td>
                    <td style="background-color: #f9f9f9; padding: 12px; text-align: left;">
                        {form['email']}
                    </td>
                </tr>
                <tr>
                    <td style="font-weight: bold; vertical-align: top; padding: 10px">Questions:</td>
                    <td style="background-color: #f9f9f9; padding: 12px; text-align: left;">
                        {form['questions']}
                    </td>
                </tr>
            </table>
            <hr style="margin: 20px 0;">
            <p style="font-size: 12px; color: #777; text-align: center;">
                &copy; 2024 Rezify | <a href="https://rezify.ai" style="color: #777;">rezify.ai</a>
            </p>
        </div>
    </body>
    </html>
    """

        mail = Mail(
            from_email=Email(FROM_EMAIL, FROM_NAME),
            to_emails=[To("sales@rezify.ai", "Sales")],
            subject=subject,
            plain_text_content=Content("text/plain", plain_text),
            html_content=Content("text/html", html_content)
        )

        ok = _send(mail, "Demo request email sent successfully (sales@rezify.ai)",
                   "ERROR: Demo Request email failed (sales@rezify.ai)")
        return ok

    except Exception as e:
        capture_exception(e)
        capture_message(f"ERROR: Demo Request email failed (sales@rezify.ai)", level="error")
        return False

def send_demo_request_confirmation_failed_email_sendgrid(form):
    try:
        subject = "Rezify Demo Request – " + str(form['name']) + " at " + str(form['university'])

        plain_text = f"""\
    Failed to send a confirmation email to: {form['email']}. This email may be incorrect, and the requester has been asked to verify and resubmit if necessary.
    
    University: {form['university']}
    Name: {form['name']}
    Position: {form['position']}
    Email: {form['email']}
    Questions: {form['questions']}
    """

        html_content = f"""\
    <html>
    <body style="font-family: Arial, sans-serif; color: #333;">
        <div style="max-width: 600px; margin: auto; padding: 20px; border: 1px solid #eee; border-radius: 8px;">
            <h2 style="color: #ff4500;">Rezify Demo Request</h2>
            <p>Failed to send a confirmation email to: {form['email']}. This email may be incorrect.</p>
    
            <table style="border-spacing: 10px">
                <tr>
                    <td style="font-weight: bold; vertical-align: top; padding: 10px">University:</td>
                    <td style="background-color: #f9f9f9; padding: 12px; text-align: left;">
                        {form['university']}
                    </td>
                </tr>
                <tr>
                    <td style="font-weight: bold; vertical-align: top; padding: 10px">Name:</td>
                    <td style="background-color: #f9f9f9; padding: 12px; text-align: left;">
                        {form['name']}
                    </td>
                </tr>
                <tr>
                    <td style="font-weight: bold; vertical-align: top; padding: 10px">Position:</td>
                    <td style="background-color: #f9f9f9; padding: 12px; text-align: left;">
                        {form['position']}
                    </td>
                </tr>
                <tr>
                    <td style="font-weight: bold; vertical-align: top; padding: 10px">Email:</td>
                    <td style="background-color: #f9f9f9; padding: 12px; text-align: left;">
                        {form['email']}
                    </td>
                </tr>
                <tr>
                    <td style="font-weight: bold; vertical-align: top; padding: 10px">Questions:</td>
                    <td style="background-color: #f9f9f9; padding: 12px; text-align: left;">
                        {form['questions']}
                    </td>
                </tr>
            </table>
            <hr style="margin: 20px 0;">
            <p style="font-size: 12px; color: #777; text-align: center;">
                &copy; 2024 Rezify | <a href="https://rezify.ai" style="color: #777;">rezify.ai</a>
            </p>
        </div>
    </body>
    </html>
    """

        mail = Mail(
            from_email=Email(FROM_EMAIL, FROM_NAME),
            to_emails=[To("sales@rezify.ai", "Sales")],
            subject=subject,
            plain_text_content=Content("text/plain", plain_text),
            html_content=Content("text/html", html_content)
        )

        ok = _send(mail, "Demo request confirmation-failed email sent (sales@rezify.ai).",
                   "ERROR: Failed demo request confirmation-failed email (sales@rezify.ai)")
        return ok

    except Exception as e:
        capture_exception(e)
        capture_message("ERROR: Failed demo request confirmation-failed email (sales@rezify.ai)", level="error")
        return False

def send_demo_request_confirmation_email_sendgrid(form):
    try:
        subject = "Rezify Demo Request Confirmation"

        plain_text = f"""\
    We have received your demo request for Rezify. A member of our team will reach out to you shortly.
    
    University: {form['university']}
    Name: {form['name']}
    Position: {form['position']}
    Email: {form['email']}
    Questions: {form['questions']}
    """

        html_content = f"""\
    <html>
    <body style="font-family: Arial, sans-serif; color: #333;">
        <div style="max-width: 600px; margin: auto; padding: 20px; border: 1px solid #eee; border-radius: 8px;">
            <h2 style="color: #ff4500;">Rezify Demo Request</h2>
            <p>Hello {form['name']},</p>
    
            <p>We have received your demo request for Rezify. A member of our team will reach out to you shortly.</p>
    
            <table style="border-spacing: 10px">
                <tr>
                    <td style="font-weight: bold; vertical-align: top; padding: 10px">University:</td>
                    <td style="background-color: #f9f9f9; padding: 12px; text-align: left;">
                        {form['university']}
                    </td>
                </tr>
                <tr>
                    <td style="font-weight: bold; vertical-align: top; padding: 10px">Name:</td>
                    <td style="background-color: #f9f9f9; padding: 12px; text-align: left;">
                        {form['name']}
                    </td>
                </tr>
                <tr>
                    <td style="font-weight: bold; vertical-align: top; padding: 10px">Position:</td>
                    <td style="background-color: #f9f9f9; padding: 12px; text-align: left;">
                        {form['position']}
                    </td>
                </tr>
                <tr>
                    <td style="font-weight: bold; vertical-align: top; padding: 10px">Email:</td>
                    <td style="background-color: #f9f9f9; padding: 12px; text-align: left;">
                        {form['email']}
                    </td>
                </tr>
                <tr>
                    <td style="font-weight: bold; vertical-align: top; padding: 10px">Questions:</td>
                    <td style="background-color: #f9f9f9; padding: 12px; text-align: left;">
                        {form['questions']}
                    </td>
                </tr>
            </table>
            <hr style="margin: 20px 0;">
            <p style="font-size: 12px; color: #777; text-align: center;">
                &copy; 2024 Rezify | <a href="https://rezify.ai" style="color: #777;">rezify.ai</a>
            </p>
        </div>
    </body>
    </html>
    """

        mail = Mail(
            from_email=Email(FROM_EMAIL, FROM_NAME),
            to_emails=To(form['email']),
            subject=subject,
            plain_text_content=Content("text/plain", plain_text),
            html_content=Content("text/html", html_content)
        )

        ok = _send(mail, f"Demo request confirmation email sent ({form['email']}).",
                   f"ERROR: Failed demo request confirmation email ({form['email']})")
        return ok

    except Exception as e:
        capture_exception(e)
        return False

def _send_internal_email(subject: str, recipient: str, plain_text: str, html_content: str) -> int:
    """
    Sends an email via your Google Workspace SMTP (no external API).
    Returns 200 on success, 500 on failure (to mirror your previous return style).
    """

    # Configure these via env vars so it works locally and on prod:
    # SENDER_EMAIL:     "peter@rezify.ai" (or "peter.h@rezify.ai" if that's the active inbox)
    # SENDER_PASSWORD:  App password or normal password if allowed
    # SMTP_HOST:        "smtp.gmail.com"
    # SMTP_PORT:        "587"
    sender_email = os.getenv("SENDER_EMAIL", "peter@rezify.ai")
    sender_password = os.getenv("SENDER_PASSWORD")
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))

    # Build a clean multipart/alternative (text + HTML)
    msg = MIMEMultipart("alternative")
    msg["From"] = sender_email
    msg["To"] = recipient
    msg["Subject"] = subject

    # Attach both parts
    msg.attach(MIMEText(plain_text or "", "plain"))
    msg.attach(MIMEText(html_content or "", "html"))

    try:
        server = smtplib.SMTP(smtp_host, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, [recipient], msg.as_string())
        server.quit()
        logging.debug(f"Email '{subject}' sent to {recipient}")
        return 200
    except Exception as e:
        capture_exception(e)
        logging.debug(f"Failed to send '{subject}' to {recipient}: {e}")
        return 500



def send_feedback_email(email, feedback_form):
    """
    Sends a feedback email internally via SendGrid (no Mailgun).
    Keeps same signature/return pattern (200 on success, 500 on failure).
    """
    safe_email = (email or "").replace('@', '[@]').replace('.', '[.]')

    try:
        subject = "Rezify Feedback Form Submission"

        plain_text = f"""\
        A user has submitted feedback via the Rezify website.

        Email: {feedback_form.get('email', '')}
        Results Rating (1-10): {feedback_form.get('results-rating', '')}
        Ease of Use Rating (1-10): {feedback_form.get('ease-rating', '')}
        Improvement Ideas: {feedback_form.get('improvements', '')}
        Additional Comments: {feedback_form.get('comments', '')}
        """

        html_content = f"""\
        <html>
        <body style="font-family: Arial, sans-serif; color: #333;">
            <div style="max-width: 600px; margin: auto; padding: 20px; border: 1px solid #eee; border-radius: 8px;">
                <h2 style="color: #ff4500;">Rezify Feedback Form Submission</h2>

                <p>A user has submitted feedback via the Rezify website.</p>
                
                <p><strong>Email:</strong> {feedback_form.get('email', '')}</p>

                <table style="border-spacing: 10px">
                    <tr>
                        <td style="font-weight: bold; vertical-align: top; padding: 10px">Results Rating (1-10):</td>
                        <td style="background-color: #f9f9f9; padding: 12px; text-align: left;">
                            {feedback_form.get('results-rating', '')}
                        </td>
                    </tr>
                    <tr>
                        <td style="font-weight: bold; vertical-align: top; padding: 10px">Ease of Use Rating (1-10)</td>
                        <td style="background-color: #f9f9f9; padding: 12px; text-align: left;">
                            {feedback_form.get('ease-rating', '')}
                        </td>
                    </tr>
                    <tr>
                        <td style="font-weight: bold; vertical-align: top; padding: 10px">Improvement Ideas:</td>
                        <td style="background-color: #f9f9f9; padding: 12px; text-align: left;">
                            {feedback_form.get('improvements', '')}
                        </td>
                    </tr>
                    <tr>
                        <td style="font-weight: bold; vertical-align: top; padding: 10px">Additional Comments:</td>
                        <td style="background-color: #f9f9f9; padding: 12px; text-align: left;">
                            {feedback_form.get('comments', '')}
                        </td>
                    </tr>
                </table>
                <hr style="margin: 20px 0;">
                <p style="font-size: 12px; color: #777; text-align: center;">
                    &copy; 2024 Rezify | <a href="https://rezify.ai" style="color: #777;">rezify.ai</a>
                </p>
            </div>
        </body>
        </html>
        """

        mail = Mail(
            from_email=Email(FROM_EMAIL, FROM_NAME),
            to_emails=To(email),
            subject=subject,
            plain_text_content=Content("text/plain", plain_text),
            html_content=Content("text/html", html_content),
        )

        ok = _send(
            mail,
            f"Feedback email sent successfully ({safe_email})",
            f"ERROR: Failed feedback email ({safe_email})"
        )
        return ok

    except Exception as e:
        capture_exception(e)
        capture_message(f"ERROR: Failed feedback email ({safe_email})", level="error")
        return False


def send_help_request_email(email, sender_email, text):
    """
    Sends a help request email internally via SendGrid (no Mailgun).
    Keeps same signature/return pattern (200 on success, 500 on failure).
    """
    safe_email = (email or "").replace('@', '[@]').replace('.', '[.]')

    try:
        subject = f"Rezify Help Request: {sender_email}"

        plain_text = f"""\
            A user has submitted a help request via the Rezify website.

            User Email: {sender_email}
            Problem Description: {text}
            """

        html_content = f"""\
            <html>
            <body style="font-family: Arial, sans-serif; color: #333;">
                <div style="max-width: 600px; margin: auto; padding: 20px; border: 1px solid #eee; border-radius: 8px;">
                    <h2 style="color: #ff4500;">Rezify Help Request</h2>
                    <p>A user has submitted a help request via the Rezify website.</p>
                    <p><strong>User Email:</strong> {sender_email}</p>
                    <p><strong>Problem Description:</strong></p>
                    <p>{text}</p>

                    <hr style="margin: 20px 0;">
                    <p style="font-size: 12px; color: #777; text-align: center;">
                        &copy; 2024 Rezify | <a href="https://rezify.ai" style="color: #777;">rezify.ai</a>
                    </p>
                </div>
            </body>
            </html>
            """

        mail = Mail(
            from_email=Email(FROM_EMAIL, FROM_NAME),
            to_emails=To(email),
            subject=subject,
            plain_text_content=Content("text/plain", plain_text),
            html_content=Content("text/html", html_content),
        )

        ok = _send(
            mail,
            f"Help request email sent successfully ({safe_email})",
            f"ERROR: Failed help request email ({safe_email})"
        )
        return ok

    except Exception as e:
        capture_exception(e)
        capture_message(f"ERROR: Failed help request email ({safe_email})", level="error")
        return False



def send_verification_email_support(email):
    try:
        subject = f"Verification Never Received ({email})"

        plain_text = f"""\
    A user ({email}) attempting to register reported that they never received their confirmation email.
    """

        html_content = f"""\
    <html>
    <body style="font-family: Arial, sans-serif; color: #333;">
        <div style="max-width: 600px; margin: auto; padding: 20px; border: 1px solid #eee; border-radius: 8px;">
            <h2 style="color: #ff4500;">Verification Never Received Report</h2>
            <p>A user ({email}) attempting to register reported that they never received their confirmation email.</p>

            <hr style="margin: 20px 0;">
            <p style="font-size: 12px; color: #777; text-align: center;">
                &copy; 2024 Rezify | <a href="https://rezify.ai" style="color: #777;">rezify.ai</a>
            </p>
        </div>
    </body>
    </html>
    """

        mail = Mail(
            from_email=Email(FROM_EMAIL, FROM_NAME),
            to_emails=[To("support@rezify.ai", "Support")],
            subject=subject,
            plain_text_content=Content("text/plain", plain_text),
            html_content=Content("text/html", html_content)
        )

        ok = _send(mail, "Verification error email sent successfully (support@rezify.ai)",
                   "ERROR: Verification error email failed (support@rezify.ai)")
        return ok

    except Exception as e:
        capture_exception(e)
        capture_message(f"ERROR: Verification error email failed (support@rezify.ai)", level="error")
        return False

def send_password_recovery_email_support(email):
    try:
        subject = f"Password Recovery Email Never Received ({email})"

        plain_text = f"""\
    A user ({email}) reported that they never received their email to recover their password.
    """

        html_content = f"""\
    <html>
    <body style="font-family: Arial, sans-serif; color: #333;">
        <div style="max-width: 600px; margin: auto; padding: 20px; border: 1px solid #eee; border-radius: 8px;">
            <h2 style="color: #ff4500;">Password Recovery Email Never Received Report</h2>
            <p>A user ({email}) reported that they never received their email to recover their password.</p>

            <hr style="margin: 20px 0;">
            <p style="font-size: 12px; color: #777; text-align: center;">
                &copy; 2024 Rezify | <a href="https://rezify.ai" style="color: #777;">rezify.ai</a>
            </p>
        </div>
    </body>
    </html>
    """

        mail = Mail(
            from_email=Email(FROM_EMAIL, FROM_NAME),
            to_emails=[To("support@rezify.ai", "Support")],
            subject=subject,
            plain_text_content=Content("text/plain", plain_text),
            html_content=Content("text/html", html_content)
        )

        ok = _send(mail, "Password recovery notification email sent successfully (support@rezify.ai)",
                   "ERROR: Password recovery notification email failed (support@rezify.ai)")
        return ok

    except Exception as e:
        capture_exception(e)
        capture_message(f"ERROR: Password recovery notification  email failed (support@rezify.ai)", level="error")
        return False


if __name__ == "__main__":
    # simple local test (set SENDGRID_API_KEY first)
    print('emailsending.py')