# utils/recommendations.py
from huggingface_hub import InferenceClient
from models.ride import Ride, Feedback
from models.drivers import Driver
from sqlalchemy import desc
from utils.db import db

class RideRecommender:
    def __init__(self):
        self.client = InferenceClient(token="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")
        
    def _get_rider_history(self, rider_id):
        """Get detailed rider history with feedback"""
        # Get completed rides with feedback, ordered by most recent
        rides_with_feedback = db.session.query(Ride, Feedback)\
            .outerjoin(Feedback)\
            .filter(
                Ride.rider_id == rider_id,
                Ride.status == 'completed'
            )\
            .order_by(desc(Ride.created_at))\
            .all()
        
        history = []
        for ride, feedback in rides_with_feedback:
            ride_data = {
                'driver_id': ride.driver_id,
                'driver_name': f"{ride.driver.first_name} {ride.driver.last_name}",
                'vehicle_type': ride.driver.vehicle_type,
                'driver_rating': float(ride.driver.rating) if ride.driver.rating else None,
                'pickup_zone': ride.pickup_zone.name,
                'feedback': feedback.comment if feedback else None,
                'ride_date': ride.created_at.strftime('%Y-%m-%d'),
                # Count how many times this rider has ridden with this driver
                'rides_with_driver': Ride.query.filter_by(
                    rider_id=rider_id,
                    driver_id=ride.driver_id,
                    status='completed'
                ).count()
            }
            history.append(ride_data)
            
        return history
    
    def _analyze_driver_performance(self, driver_id):
        """Analyze driver's overall performance"""
        # Get driver's completed rides
        completed_rides = Ride.query.filter_by(
            driver_id=driver_id,
            status='completed'
        ).count()
        
        # Get driver's feedback
        positive_feedback = Feedback.query\
            .join(Ride)\
            .filter(
                Ride.driver_id == driver_id,
                Ride.status == 'completed'
            ).count()
            
        return {
            'completed_rides': completed_rides,
            'feedback_received': positive_feedback
        }
    
    def _get_driver_rating_weight(self, driver):
        """Calculate weighted score for driver based on rating and experience"""
        rating = float(driver.rating) if driver.rating else 0
        total_rides = len(driver.rides) if hasattr(driver, 'rides') else 0
        
        # Weight rating more heavily as number of rides increases
        rating_weight = min(1.0, total_rides / 50.0)  # Caps at 50 rides
        return rating * (1 + rating_weight)
    
    def _score_driver(self, driver, rider_history):
        """Score a driver based on multiple factors"""
        # Base score from rating
        score = self._get_driver_rating_weight(driver)
        
        # Analyze driver performance
        performance = self._analyze_driver_performance(driver.id)
        
        # Boost score based on completed rides
        experience_boost = min(2.0, performance['completed_rides'] / 25.0)  # Caps at 25 rides
        score *= (1 + experience_boost)
        
        # Check rider's history with this driver
        for ride in rider_history:
            if ride['driver_id'] == driver.id:
                # Boost score if rider has had good experiences with this driver
                if ride['feedback'] and any(good_word in ride['feedback'].lower() 
                                          for good_word in ['good', 'great', 'excellent', 'amazing', 'best']):
                    score *= 1.2
                # Boost score based on number of rides with this driver
                score *= (1 + (ride['rides_with_driver'] * 0.1))  # 10% boost per previous ride
                break
                
        return score
    
    def get_recommendation(self, rider_id, available_drivers):
        """Get driver recommendation based on comprehensive analysis"""
        try:
            if not available_drivers:
                return None, "No drivers available"
                
            rider_history = self._get_rider_history(rider_id)
            
            # For new riders, use simple rating-based recommendation
            if not rider_history:
                best_driver = max(available_drivers, 
                                key=lambda d: (float(d.rating) if d.rating else 0))
                return best_driver.id, (
                    f"Recommended based on high rating ({best_driver.rating:.1f} stars) "
                    f"and experience ({len(best_driver.rides) if hasattr(best_driver, 'rides') else 0} rides)"
                )
            
            # Score each available driver
            scored_drivers = []
            for driver in available_drivers:
                score = self._score_driver(driver, rider_history)
                scored_drivers.append((driver, score))
            
            # Sort by score and get best driver
            best_driver, best_score = max(scored_drivers, key=lambda x: x[1])
            
            # Generate recommendation reason
            performance = self._analyze_driver_performance(best_driver.id)
            previous_rides = next(
                (h['rides_with_driver'] for h in rider_history 
                 if h['driver_id'] == best_driver.id), 
                0
            )
            
            reason_parts = []
            if best_driver.rating:
                reason_parts.append(f"{best_driver.rating:.1f} star rating")
            if performance['completed_rides'] > 0:
                reason_parts.append(f"{performance['completed_rides']} completed rides")
            if previous_rides > 0:
                reason_parts.append(f"you've had {previous_rides} successful rides with this driver")
            
            recommendation_reason = "Recommended based on " + ", ".join(reason_parts)
            
            return best_driver.id, recommendation_reason
            
        except Exception as e:
            print(f"Error in recommendation system: {str(e)}")
            # Fallback to highest rated driver
            best_driver = max(available_drivers, 
                            key=lambda d: (float(d.rating) if d.rating else 0))
            return best_driver.id, "Recommended based on highest rating (fallback)"