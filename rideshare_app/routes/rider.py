# routes/rider.py
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from utils.decorators import role_required
from models.zone import Zone
from models.drivers import Driver
from models.ride import Ride, Feedback, RiderAddress
from utils.db import db
from flask_socketio import emit
import logging
import json
from utils.recommendations import RideRecommender
from config import Config
import uuid
from utils import ride_utils
import time

bp = Blueprint('rider', __name__, url_prefix='/rider')
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)
recommender = RideRecommender()  # No need to pass API key anymore



@bp.route('/dashboard')
@login_required
@role_required('rider')
def dashboard():
    zones = Zone.query.all()
    selected_zone_id = request.args.get('zone_id', type=int)
    
    drivers = []
    available_drivers = []
    selected_zone = None
    recommended_driver = None
    recommendation_reason = None
    
    if selected_zone_id:
        # Only show drivers who are marked as available and have less than 4 active/pending rides
        available_drivers = []
        potential_drivers = Driver.query.filter_by(
            zone_id=selected_zone_id,
            is_available=True
        ).all()
        
        for driver in potential_drivers:
            is_available, current_riders = ride_utils.get_driver_availability(driver.id)
            if is_available:
                available_drivers.append(driver)
        
        drivers = available_drivers
        selected_zone = Zone.query.get(selected_zone_id)

        if drivers:
            try:
                print(f"Getting recommendation for rider {current_user.id}")
                recommended_driver_id, recommendation_reason = recommender.get_recommendation(
                current_user.id,
                drivers
                )
                print(f"Recommendation received: Driver {recommended_driver_id}")
                print(f"Reason: {recommendation_reason}")
                recommended_driver = next((d for d in drivers if d.id == recommended_driver_id), None)
                if recommended_driver:
                    print(f"Found recommended driver: {recommended_driver.get_full_name()}")
                else:
                    print("Could not find recommended driver in available drivers list")
            except Exception as e:
                print(f"Error in dashboard route: {str(e)}")
                recommended_driver = None
                recommendation_reason = None


    active_ride = Ride.query.filter(
        Ride.rider_id == current_user.id,
        Ride.status.in_(['requested', 'accepted', 'rejected'])
    ).order_by(Ride.created_at.desc()).first()

    completed_rides = Ride.query.filter_by(
        rider_id=current_user.id,
        status='completed'
    ).order_by(
        Ride.updated_at.desc()
    ).limit(5).all()
        

    
    return render_template('rider/dashboard.html',
                         zones=zones,
                         drivers=drivers,
                         selected_zone=selected_zone,
                         active_ride=active_ride,
                         completed_rides=completed_rides,
                         ride_utils=ride_utils,
                         recommended_driver=recommended_driver,
                         recommendation_reason=recommendation_reason)

@bp.route('/request_ride/<int:driver_id>', methods=['POST'])
@login_required
@role_required('rider')
def request_ride(driver_id):
    try:
        # Check if user already has an active ride request
        active_ride = Ride.query.filter(
            Ride.rider_id == current_user.id,
            Ride.status.in_(['requested', 'accepted'])
        ).first()
        
        if active_ride:
            flash('You already have an active ride request.', 'error')
            return redirect(url_for('rider.dashboard'))
        
        driver = Driver.query.get_or_404(driver_id)
        
        # Get or create ride group
        active_group = Ride.query.filter_by(
            driver_id=driver_id,
            status='accepted'
        ).first()
        
        ride_group_id = active_group.ride_group_id if active_group else str(uuid.uuid4())
        
        # Check available seats
        if Ride.is_ride_full(ride_group_id):
            flash('This ride is full. Please choose another driver.', 'error')
            return redirect(url_for('rider.dashboard'))
        
        # Get rider's address
        rider_address = RiderAddress.query.filter_by(email=current_user.email).first()
        if not rider_address:
            flash('Please update your address information first.', 'error')
            return redirect(url_for('rider.dashboard'))
        
        # Create new ride request
        ride = Ride(
            rider_id=current_user.id,
            driver_id=driver.id,
            status='requested',
            pickup_zone_id=driver.zone_id,
            pickup_address=f"{rider_address.street_address}, {rider_address.city}",
            rider_phone=rider_address.phone_number,
            ride_group_id=ride_group_id
        )
        
        # Set initial fare
        ride.calculate_fare()
        
        db.session.add(ride)
        db.session.commit()
        
        flash('Ride request sent successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash('Something went wrong. Please try again.', 'error')
    
    return redirect(url_for('rider.dashboard'))


@bp.route('/check_ride_status')
@login_required
@role_required('rider')
def check_ride_status():
    try:
        active_ride = Ride.query.filter(
            Ride.rider_id == current_user.id,
            Ride.status.in_(['requested', 'accepted', 'cancelled'])
        ).first()
        
        if active_ride:
            return jsonify({
                'success': True,
                'status': active_ride.status,
                'driver': {
                    'name': f"{active_ride.driver.first_name} {active_ride.driver.last_name}",
                    'phone': active_ride.driver.phone_number,
                    'vehicle': active_ride.driver.vehicle_number
                } if active_ride.status == 'accepted' else None
            })
        
        return jsonify({
            'success': True,
            'status': None
        })
        
    except Exception as e:
        logger.error(f"Error checking ride status: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

# Socket.IO event handlers
def handle_ride_status_change(ride_id, status):
    """Emit ride status change to relevant clients"""
    ride = Ride.query.get(ride_id)
    if ride and ride.rider_id:
        emit('ride_status_update', {
            'ride_id': ride_id,
            'status': status,
            'driver': {
                'name': f"{ride.driver.first_name} {ride.driver.last_name}",
                'phone': ride.driver.phone_number,
                'vehicle': ride.driver.vehicle_number
            } if status == 'accepted' else None
        }, room=f"user_{ride.rider_id}")

# Add to routes/rider.py
@bp.route('/submit_feedback/<int:ride_id>', methods=['POST'])
@login_required
@role_required('rider')
def submit_feedback(ride_id):
    try:
        ride = Ride.query.get_or_404(ride_id)
        
        # Verify the ride belongs to current user
        if ride.rider_id != current_user.id:
            flash('Unauthorized access.', 'error')
            return redirect(url_for('rider.dashboard'))
            
        # Check if feedback already exists
        if Feedback.query.filter_by(ride_id=ride_id).first():
            flash('Feedback already submitted for this ride.', 'error')
            return redirect(url_for('rider.dashboard'))
            
        comment = request.form.get('comment', '').strip()
        
        # Validate comment
        if not comment:
            flash('Please provide feedback comment.', 'error')
            return redirect(url_for('rider.dashboard'))
            
        # Create feedback
        feedback = Feedback(
            ride_id=ride_id,
            comment=comment
        )
        
        db.session.add(feedback)
        db.session.commit()
        
        flash('Thank you for your feedback!', 'success')
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error submitting feedback: {str(e)}")
        flash('Something went wrong. Please try again.', 'error')
        
    return redirect(url_for('rider.dashboard'))


