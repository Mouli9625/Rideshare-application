# models/driver.py
from datetime import datetime
from utils.db import db
from sqlalchemy import func

class Driver(db.Model):
    __tablename__ = 'drivers'
    
    id = db.Column(db.Integer, primary_key=True)
    driver_id = db.Column(db.String(10), unique=True, nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone_number = db.Column(db.String(15), nullable=False)
    license_number = db.Column(db.String(20), unique=True, nullable=False)
    vehicle_number = db.Column(db.String(20), unique=True, nullable=False)
    vehicle_type = db.Column(db.String(20), nullable=False)
    zone_id = db.Column(db.Integer, db.ForeignKey('zones.id'), nullable=False)
    rating = db.Column(db.Float, nullable=True, default=0.0)
    total_ratings = db.Column(db.Integer, nullable=False, default=0)
    is_available = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def get_full_name(self):
        """Returns the driver's full name."""
        return f"{self.first_name} {self.last_name}"

    def __repr__(self):
        return f'<Driver {self.get_full_name()}>'
    
    def calculate_rating(self):
        """Calculate driver rating based on feedback sentiment scores"""
        from models.ride import Ride, Feedback
        
        # Get all feedback for completed rides by this driver
        feedback_scores = db.session.query(
            func.avg(Feedback.sentiment_score).label('avg_score')
        ).join(
            Ride, Ride.id == Feedback.ride_id
        ).filter(
            Ride.driver_id == self.id,
            Ride.status == 'completed',
            Feedback.sentiment_score.isnot(None)
        ).first()
        
        return round(feedback_scores.avg_score, 1) if feedback_scores.avg_score else 0.0

    def get_recent_feedback(self, limit=5):
        """Get recent feedback with sentiment scores"""
        from models.ride import Ride, Feedback
        
        return db.session.query(Feedback)\
            .join(Ride)\
            .filter(
                Ride.driver_id == self.id,
                Ride.status == 'completed'
            )\
            .order_by(Feedback.created_at.desc())\
            .limit(limit)\
            .all()
    def update_rating(self, rating_stats):
        """
        Update driver rating based on sentiment analysis stats
        
        Args:
            rating_stats (dict): Dictionary containing rating statistics
        """
        if rating_stats['total_ratings'] > 0:
            self.rating = rating_stats['average']
            self.total_ratings = rating_stats['total_ratings']
            return True
        return False
    