# models/booking.py
from datetime import datetime
import uuid
from utils.db import db
from flask_login import current_user

class Booking(db.Model):
    """
    Booking model to store ride bookings between riders and drivers
    """
    __tablename__ = 'bookings'
    
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.String(10), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    driver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    zone_id = db.Column(db.Integer, db.ForeignKey('zones.id'), nullable=False)
    pickup_location = db.Column(db.String(255), nullable=True)
    dropoff_location = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(20), nullable=False, default='pending')
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', foreign_keys=[user_id], backref='rider_bookings')
    driver = db.relationship('User', foreign_keys=[driver_id], backref='driver_bookings')
    zone = db.relationship('Zone', backref='bookings')
    
    def __init__(self, user_id, driver_id, zone_id, pickup_location=None, dropoff_location=None):
        self.booking_id = self._generate_booking_id()
        self.user_id = user_id
        self.driver_id = driver_id
        self.zone_id = zone_id
        self.pickup_location = pickup_location
        self.dropoff_location = dropoff_location
        self.status = 'pending'
    
    def _generate_booking_id(self):
        """Generate a unique booking ID"""
        return f'BK{uuid.uuid4().hex[:8].upper()}'
    
    @property
    def driver_name(self):
        """Get the driver's username"""
        return self.driver.username if self.driver else 'Unknown Driver'
    
    @property
    def zone_name(self):
        """Get the zone name"""
        return self.zone.zone_name if self.zone else 'Unknown Zone'
    
    def update_status(self, new_status):
        """Update booking status"""
        valid_statuses = ['pending', 'accepted', 'in_progress', 'completed', 'cancelled']
        if new_status not in valid_statuses:
            raise ValueError(f'Invalid status. Must be one of: {", ".join(valid_statuses)}')
        self.status = new_status
        self.updated_at = datetime.utcnow()
        db.session.commit()
    
    def to_dict(self):
        """Convert booking to dictionary"""
        return {
            'booking_id': self.booking_id,
            'driver_name': self.driver_name,
            'zone_name': self.zone_name,
            'pickup_location': self.pickup_location,
            'dropoff_location': self.dropoff_location,
            'status': self.status,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

    @staticmethod
    def get_user_bookings(user_id):
        """Get all bookings for a specific user"""
        return Booking.query.filter_by(user_id=user_id).order_by(Booking.created_at.desc()).all()
    
    @staticmethod
    def get_driver_bookings(driver_id):
        """Get all bookings for a specific driver"""
        return Booking.query.filter_by(driver_id=driver_id).order_by(Booking.created_at.desc()).all()