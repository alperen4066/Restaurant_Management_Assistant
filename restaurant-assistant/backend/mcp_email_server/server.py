import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")


def send_email(recipient: str, subject: str, html_body: str):
    """Send email via SMTP."""
    try:
        msg = MIMEMultipart('alternative')
        msg["Subject"] = subject
        msg["From"] = SMTP_USER
        msg["To"] = recipient
        
        html_part = MIMEText(html_body, "html")
        msg.attach(html_part)
        
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
        
        return {"status": "success", "message": f"Email sent to {recipient}"}
    
    except Exception as e:
        return {"status": "error", "message": str(e)}


# MCP Server setup (pseudo-code - adapt to your MCP SDK)
# This is a simplified version - you'll need to use the actual MCP SDK from your course

"""
from mcp.server import MCPServer

server = MCPServer("email_server")

@server.tool(
    name="send_invoice_email",
    description="Send restaurant invoice by email"
)
def send_invoice_email(recipient_email: str, subject: str, html_body: str):
    return send_email(recipient_email, subject, html_body)

if __name__ == "__main__":
    server.run(port=5000)
"""

# For now, simple function-based approach
if __name__ == "__main__":
    print("MCP Email Server running...")
    print(f"SMTP configured: {SMTP_SERVER}:{SMTP_PORT}")
    print("Waiting for email requests...")
    # In production, this would be an actual MCP server loop
