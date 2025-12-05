import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()


def send_bill_email(recipient: str, html_content: str) -> bool:
    """Send bill via email."""
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = '🍽️ Your Restaurant Bill - Thank You!'
        msg['From'] = os.getenv('SMTP_USER')
        msg['To'] = recipient
        
        html_part = MIMEText(html_content, 'html')
        msg.attach(html_part)
        
        with smtplib.SMTP(os.getenv('SMTP_SERVER'), int(os.getenv('SMTP_PORT'))) as server:
            server.starttls()
            server.login(os.getenv('SMTP_USER'), os.getenv('SMTP_PASS'))
            server.send_message(msg)
        
        print(f"✅ Email sent successfully to {recipient}")
        return True
    
    except Exception as e:
        print(f"❌ Email error: {e}")
        return False


def send_reservation_confirmation(recipient: str, reservation_details: dict, order_items: list = None) -> bool:
    """Send reservation confirmation with order summary."""
    try:
        order_html = ""
        if order_items:
            order_html = "<h3>Your Pre-Order:</h3><ul>"
            for item in order_items:
                order_html += f"<li>{item.quantity}x {item.name} - €{item.price * item.quantity:.2f}</li>"
            order_html += "</ul>"
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial; padding: 20px; background: #f5f5f5; }}
                .container {{ max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }}
                h2 {{ color: #667eea; }}
                .detail {{ margin: 10px 0; font-size: 16px; }}
            </style>
        </head>
        <body>
            <div class='container'>
                <h2>🎉 Reservation Confirmed!</h2>
                <p>Thank you for booking with us!</p>
                <div class='detail'><strong>📅 Date:</strong> {reservation_details['date']}</div>
                <div class='detail'><strong>🕐 Time:</strong> {reservation_details['time']}</div>
                <div class='detail'><strong>👥 Party Size:</strong> {reservation_details['people']} people</div>
                {order_html}
                <p style='margin-top: 30px;'>We look forward to serving you! 😊</p>
            </div>
        </body>
        </html>
        """
        
        msg = MIMEMultipart('alternative')
        msg['Subject'] = '✅ Reservation Confirmed - Maison Lumière Restaurant'
        msg['From'] = os.getenv('SMTP_USER')
        msg['To'] = recipient
        
        msg.attach(MIMEText(html, 'html'))
        
        with smtplib.SMTP(os.getenv('SMTP_SERVER'), int(os.getenv('SMTP_PORT'))) as server:
            server.starttls()
            server.login(os.getenv('SMTP_USER'), os.getenv('SMTP_PASS'))
            server.send_message(msg)
        
        print(f"✅ Reservation email sent to {recipient}")
        return True
    
    except Exception as e:
        print(f"❌ Reservation email error: {e}")
        return False
