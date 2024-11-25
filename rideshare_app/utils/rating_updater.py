# utils/rating_updater.py
from models.drivers import Driver
from models.ride import Ride
from models.ride import Feedback
from utils.db import db
from sqlalchemy import func

def update_driver_rating(driver_id):
    """
    Update driver's rating based on sentiment analysis of their feedback
    
    Args:
        driver_id (int): ID of the driver to update
    """
    try:
        # Get all feedback for the driver's completed rides
        feedback_scores = db.session.query(
            Feedback.sentiment_score
        ).join(
            Ride, Ride.id == Feedback.ride_id
        ).filter(
            Ride.driver_id == driver_id,
            Ride.status == 'completed',
            Feedback.sentiment_score.isnot(None)  # Only consider feedback with sentiment scores
        ).all()
        
        # Calculate new rating
        scores = [score[0] for score in feedback_scores if score[0] is not None]
        if scores:
            new_rating = sum(scores) / len(scores)
            total_ratings = len(scores)
        else:
            new_rating = 0.0
            total_ratings = 0
            
        # Update driver's rating
        driver = Driver.query.get(driver_id)
        if driver:
            driver.rating = round(new_rating, 2)
            driver.total_ratings = total_ratings
            db.session.commit()
            
        return True
        
    except Exception as e:
        print(f"Error updating driver rating: {str(e)}")
        db.session.rollback()
        return False