from flask import current_app, render_template_string
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
from typing import Dict, Any

class EmailService:
    def __init__(self, app=None):
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
        self.sender_email = "vtu20132soc.cse@gmail.com"
        self.sender_password = "fync btvv ugfz xefe"
        
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        app.email_service = self

    def send_ride_completion_email(self, ride_data: Dict[str, Any]) -> bool:
        """
        Send ride completion email to rider
        """
        try:
            # Create message container
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f'Ride Completed - Receipt for Ride #{ride_data["ride_id"]}'
            msg['From'] = f"Ride Share Service <{self.sender_email}>"
            msg['To'] = ride_data['rider_email']

            # Create the HTML email content with proper string formatting
            html_content = f"""
            <!DOCTYPE html>
           <!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Your Ride Receipt</title>
</head>
<body style="font-family: Arial, sans-serif; background-color: #f4f7fa; color: #333; margin: 0; padding: 0;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px; background-color: #fff; box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1); border-radius: 10px;">
        <h2 style="text-align: center; color: #2c3e50; margin-bottom: 20px; font-size: 24px;">Your Ride Receipt</h2>
        
        <div style="background-color: #f8f9fa; padding: 20px; border-radius: 10px; margin-bottom: 20px;">
            <h3 style="color: #34495e; font-size: 20px; margin-top: 0;">Ride Details</h3>
            <p style="font-size: 16px; margin: 8px 0; line-height: 1.6;"><strong style="color: #2c3e50;">Ride ID:</strong> #{ride_data['ride_id']}</p>
            <p style="font-size: 16px; margin: 8px 0; line-height: 1.6;"><strong style="color: #2c3e50;">Date:</strong> {ride_data['completion_time']}</p>
            <p style="font-size: 16px; margin: 8px 0; line-height: 1.6;"><strong style="color: #2c3e50;">Pickup Location:</strong> {ride_data['pickup_address']}</p>
        </div>
        
        <div style="background-color: #f8f9fa; padding: 20px; border-radius: 10px; margin-bottom: 20px;">
            <h3 style="color: #34495e; font-size: 20px; margin-top: 0;">Driver Information</h3>
            <p style="font-size: 16px; margin: 8px 0; line-height: 1.6;"><strong style="color: #2c3e50;">Driver Name:</strong> {ride_data['driver_name']}</p>
            <p style="font-size: 16px; margin: 8px 0; line-height: 1.6;"><strong style="color: #2c3e50;">Vehicle Number:</strong> {ride_data['vehicle_number']}</p>
        </div>

        <div style="background-color: #f8f9fa; padding: 20px; border-radius: 10px; margin-bottom: 20px;">
            <h3 style="color: #34495e; font-size: 20px; margin-top: 0;">Fare Details</h3>
            <p style="font-size: 18px; font-weight: bold; color: #16a085; margin: 8px 0; line-height: 1.6;"><strong style="color: #2c3e50;">Total Fare:</strong> ₹{ride_data['fare']}</p>
            <p style="font-size: 18px; font-weight: bold; color: #16a085; margin: 8px 0; line-height: 1.6;"><strong style="color: #2c3e50;">Split Among:</strong> {ride_data['total_riders']} riders</p>
            <p style="font-size: 18px; font-weight: bold; color: #16a085; margin: 8px 0; line-height: 1.6;"><strong style="color: #2c3e50;">Your Share:</strong> ₹{ride_data['fare_per_rider']}</p>
        </div>
        
        
        <p style="font-size: 14px; color: #7f8c8d; text-align: center; margin-top: 30px;">
            Thank you for using our service! If you have any questions, feel free to <a href="mailto:support@rideservice.com" style="color: #3498db; text-decoration: none;">contact us</a>.
        </p>
    </div>
</body>
</html>

            """

            # No need for render_template_string anymore since we're using f-strings
            msg.attach(MIMEText(html_content, 'html'))

            # Create SMTP session
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()  # Enable TLS
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)

            current_app.logger.info(f"Ride completion email sent for ride #{ride_data['ride_id']}")
            return True

        except Exception as e:
            current_app.logger.error(f"Failed to send ride completion email: {str(e)}")
            return False