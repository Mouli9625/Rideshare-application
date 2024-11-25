# utils/ride_utils.py
from models.ride import Ride
from models.drivers import Driver

def get_total_riders(ride_group_id):
    """Get total number of accepted riders in a ride group"""
    return Ride.query.filter_by(
        ride_group_id=ride_group_id,
        status='accepted'
    ).count()

def get_pending_requests(ride_group_id):
    """Get number of pending ride requests in a ride group"""
    return Ride.query.filter_by(
        ride_group_id=ride_group_id,
        status='requested'
    ).count()

def get_available_seats(ride_group_id):
    """Get number of available seats for a ride group"""
    total_riders = get_total_riders(ride_group_id)
    MAX_SEATS = 4
    return MAX_SEATS - total_riders

# utils/ride_utils.py

def get_driver_availability(driver_id):
    """
    Get driver availability and current number of accepted riders
    Returns:
        tuple: (is_available: bool, current_riders: int)
    """
    from models.ride import Ride
    
    # Count only accepted rides for the latest ride group
    latest_ride = Ride.query.filter_by(
        driver_id=driver_id,
    ).order_by(Ride.created_at.desc()).first()
    
    if not latest_ride:
        return True, 0
        
    # Get all accepted rides in the current ride group
    current_riders = Ride.query.filter_by(
        ride_group_id=latest_ride.ride_group_id,
        status='accepted'
    ).count()
    
    # Driver is available if they have less than 4 accepted riders
    is_available = current_riders < 4
    
    return is_available, current_riders

def get_total_riders(ride_group_id):
    """
    Get total number of riders in a ride group (both accepted and requested)
    """
    from models.ride import Ride
    
    return Ride.query.filter(
        Ride.ride_group_id == ride_group_id,
        Ride.status.in_(['accepted', 'requested'])
    ).count()

def update_ride_fares(ride_group_id):
    """
    Update fares for all rides in a group based on number of accepted riders
    """
    from models.ride import Ride
    from utils.db import db
    
    # Get all accepted rides in the group
    accepted_rides = Ride.query.filter_by(
        ride_group_id=ride_group_id,
        status='accepted'
    ).all()
    
    # Calculate individual fare
    num_riders = len(accepted_rides)
    if num_riders > 0:
        individual_fare = 400.0 / num_riders  # Base fare divided by number of riders
        
        # Update fare for each accepted ride
        for ride in accepted_rides:
            ride.current_fare = individual_fare
            
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise e

def check_and_update_driver_availability(driver_id):
    """
    Check and update driver availability based on current rides
    """
    from models.ride import Ride
    from models.drivers import Driver
    from utils.db import db
    
    # Get latest ride group for the driver
    latest_ride = Ride.query.filter_by(
        driver_id=driver_id
    ).order_by(Ride.created_at.desc()).first()
    
    if latest_ride:
        # Count accepted rides in the current group
        accepted_count = Ride.query.filter_by(
            ride_group_id=latest_ride.ride_group_id,
            status='accepted'
        ).count()
        
        # Update driver availability
        driver = Driver.query.get(driver_id)
        if driver:
            driver.is_available = accepted_count < 4
            
            try:
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                raise e

def update_driver_status(driver_id):
    """Update driver availability status based on current rides"""
    driver = Driver.query.get(driver_id)
    if not driver:
        return False
        
    is_available, current_riders = get_driver_availability(driver_id)
    
    # If driver has 4 accepted rides, they should not be available
    if current_riders >= 4:
        is_available = False
    
    driver.is_available = is_available
    return True

def can_accept_ride(ride_id):
    """
    Check if a ride can be accepted based on available seats
    Returns tuple of (can_accept, message)
    """
    ride = Ride.query.get(ride_id)
    if not ride:
        return False, "Ride not found"
        
    if ride.status != 'requested':
        return False, "Ride is not in requested status"
    
    # Get current number of accepted rides
    accepted_rides = Ride.query.filter(
        Ride.driver_id == ride.driver_id,
        Ride.status == 'accepted'
    ).count()
    
    # Check if driver already has 4 accepted rides
    if accepted_rides >= 4:
        return False, "Driver has reached maximum capacity"
    
    # Check available seats in the ride group
    available_seats = get_available_seats(ride.ride_group_id)
    if available_seats <= 0:
        return False, "No seats available in this ride"
    
    # Check driver availability based only on accepted rides
    is_available, _ = get_driver_availability(ride.driver_id)
    if not is_available:
        return False, "Driver is not available"
    
    return True, "Ride can be accepted"

def calculate_individual_fare(ride_group_id):
    """
    Calculate individual fare based on number of accepted riders
    Returns:
        float: Individual fare amount
    """
    from models.ride import Ride
    
    base_fare = 400.0  # Fixed base fare
    accepted_riders = Ride.get_total_accepted_riders(ride_group_id)
    
    if accepted_riders == 0:
        return base_fare
    
    return base_fare / accepted_riders

def update_ride_fares(ride_group_id):
    """
    Update fares for all rides in a group when acceptance status changes
    """
    from models.ride import Ride
    from utils.db import db
    
    rides = Ride.query.filter_by(
        ride_group_id=ride_group_id,
        status='accepted'
    ).all()
    
    for ride in rides:
        ride.calculate_fare()
    
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise e
    
def calculate_ride_fares(ride_group_id):
    """
    Calculate and update fares for all rides in a group
    Returns the individual fare amount
    """
    from models.ride import Ride
    from utils.db import db
    
    # Get all accepted rides in the group
    accepted_rides = Ride.query.filter_by(
        ride_group_id=ride_group_id,
        status='accepted'
    ).all()
    
    # Calculate individual fare
    num_riders = len(accepted_rides)
    if num_riders > 0:
        individual_fare = 400.0 / num_riders  # Base fare divided by number of riders
        
        # Update fare for each accepted ride
        for ride in accepted_rides:
            ride.current_fare = individual_fare
        
        try:
            db.session.commit()
            return individual_fare
        except Exception as e:
            db.session.rollback()
            raise e
            
    return 0.0