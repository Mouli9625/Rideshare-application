# models/ride.py
from utils.db import db
from datetime import datetime

class Ride(db.Model):
    __tablename__ = 'rides'
    
    id = db.Column(db.Integer, primary_key=True)
    rider_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    driver_id = db.Column(db.Integer, db.ForeignKey('drivers.id'), nullable=False)  # Changed to reference drivers table
    pickup_zone_id = db.Column(db.Integer, db.ForeignKey('zones.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')  # requested, accepted, completed, cancelled
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    pickup_address = db.Column(db.String(255), nullable=False)
    rider_phone = db.Column(db.String(20), nullable=False)
    base_fare = db.Column(db.Float, default=400.0)  # Fixed base fare of ₹400
    current_fare = db.Column(db.Float, nullable=False, default=0.0)  # Individual rider's share
    ride_group_id = db.Column(db.String(36), nullable=False)
    
    # Relationships
    rider = db.relationship('User', backref='rides_as_rider')  # Changed backref name
    driver = db.relationship('Driver', backref='rides_as_driver')  # Changed relationship
    pickup_zone = db.relationship('Zone', backref='rides')

    def calculate_fare(self):
        """Calculate and update the current fare based on number of riders"""
        if self.status == 'accepted':
            accepted_rides = Ride.query.filter_by(
                ride_group_id=self.ride_group_id,
                status='accepted'
            ).count()
            
            if accepted_rides > 0:
                self.current_fare = 400.0 / accepted_rides
            else:
                self.current_fare = 400.0
        else:
            self.current_fare = 0.0

    def get_formatted_fare(self):
        """Return formatted fare with 2 decimal places"""
        return "{:.2f}".format(self.current_fare if self.current_fare is not None else 0)
            
    @classmethod
    def get_available_seats(cls, ride_group_id):
        """
        Get number of available seats for a ride group based only on accepted rides
        Returns:
            int: Number of available seats (0-4)
        """
        accepted_riders = cls.query.filter_by(
            ride_group_id=ride_group_id,
            status='accepted'
        ).count()
        return max(0, 4 - accepted_riders)
    @classmethod
    def is_ride_full(cls, ride_group_id):
        """
        Check if a ride group is full based on accepted rides
        Returns:
            bool: True if no seats available, False otherwise
        """
        return cls.get_available_seats(ride_group_id) == 0  # Maximum 4 riders
    @classmethod
    def get_total_accepted_riders(cls, ride_group_id):
        """
        Get total number of accepted riders in a ride group
        Returns:
            int: Number of accepted riders
        """
        return cls.query.filter_by(
            ride_group_id=ride_group_id,
            status='accepted'
        ).count()

    def get_status_class(self):
        """Returns CSS class based on ride status"""
        status_classes = {
            'requested': 'status-pending',
            'accepted': 'status-accepted',
            'rejected': 'status-rejected',
            'completed': 'status-completed'
        }
        return status_classes.get(self.status, '')

    def __repr__(self):
        return f'<Ride {self.id}: {self.status}>', f'<Feedback {self.id} for Ride {self.ride_id}>', f'<Feedback {self.id} Rating: {self.rating}>'
    
# models/feedback.py
from utils.db import db
from datetime import datetime

class Feedback(db.Model):
    __tablename__ = 'feedback'
    
    id = db.Column(db.Integer, primary_key=True)
    ride_id = db.Column(db.Integer, db.ForeignKey('rides.id'), nullable=False, unique=True)
    comment = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    ride = db.relationship('Ride', backref=db.backref('feedback', uselist=False))

    def analyze_sentiment(self, analyzer):
        """Analyze the feedback comment and store the sentiment score"""
        if self.comment:
            self.sentiment_score = analyzer.analyze(self.comment)
            return self.sentiment_score
        return None
    def __repr__(self):
        return f'<Feedback {self.id} Rating: {self.rating}>'
    @property
    def rating_value(self):
        """Safe getter for rating"""
        return min(max(int(self.rating), 1), 5) if self.rating is not None else None
    

class RiderAddress(db.Model):
    __tablename__ = 'rider_addresses'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone_number = db.Column(db.String(20), nullable=False, server_default='Not Provided')
    street_address = db.Column(db.String(255), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    state = db.Column(db.String(100), nullable=False)
    postal_code = db.Column(db.String(20), nullable=False)
    country = db.Column(db.String(100), default='India')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    
    def __repr__(self):
        return f'<RiderAddress {self.email}>'
