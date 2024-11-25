# routes/driver.py
from flask import Blueprint, render_template, flash, redirect, url_for, jsonify, current_app
from flask_login import login_required, current_user
from utils.decorators import role_required
from models.ride import Ride, Feedback
from models.drivers import Driver
from utils.db import db
from utils.sentiment import SentimentAnalyzer
from config import Config
from utils import ride_utils
from utils.ride_utils import update_ride_fares, get_driver_availability, check_and_update_driver_availability,calculate_ride_fares
from datetime import datetime
from utils.email_service import EmailService


bp = Blueprint('driver', __name__, url_prefix='/driver')
sentiment_analyzer = SentimentAnalyzer(api_key=Config.HUGGINGFACE_API_TOKEN)
@bp.route('/dashboard')
@login_required
@role_required('driver')
def dashboard():
    # Get the driver profile for the current user
    driver = Driver.query.filter_by(email=current_user.email).first()
    
    if not driver:
        flash('Driver profile not found.', 'error')
        return redirect(url_for('main.index'))
    
    # Get active rides (requested or in-progress)
    active_rides = Ride.query.filter_by(
        driver_id=driver.id
    ).filter(
        Ride.status.in_(['requested', 'accepted'])
    ).order_by(
        Ride.created_at.desc()
    ).all()
    
    # Get completed rides history
    completed_rides = Ride.query.filter_by(
        driver_id=driver.id,
        status='completed'
    ).order_by(
        Ride.updated_at.desc()
    ).limit(5).all()

    all_feedback = db.session.query(Feedback)\
        .join(Ride)\
        .filter(
            Ride.driver_id == driver.id,
            Ride.status == 'completed'
        ).order_by(
            Feedback.created_at.desc()
        ).all()

    
    rating_stats = sentiment_analyzer.update_driver_rating(driver, all_feedback)
    
    return render_template('driver/dashboard.html',
                         driver=driver,
                         active_rides=active_rides,
                         completed_rides=completed_rides,
                         rating_stats=rating_stats,
                         ride_utils=ride_utils)

# Update the driver route to recalculate fares (routes/driver.py)
@bp.route('/ride/<int:ride_id>/accept', methods=['POST'])
@login_required
@role_required('driver')
def accept_ride(ride_id):
    ride = Ride.query.get_or_404(ride_id)
    
    try:
        # Update ride status
        ride.status = 'accepted'
        
        # Calculate and update fares for all rides in the group
        new_fare = calculate_ride_fares(ride.ride_group_id)
        
        # Update driver availability
        check_and_update_driver_availability(ride.driver_id)
        
        # Cancel any pending requests if ride is now full
        is_available, current_riders = get_driver_availability(ride.driver_id)
        if not is_available:
            pending_rides = Ride.query.filter_by(
                driver_id=ride.driver_id,
                status='requested'
            ).all()
            for pending_ride in pending_rides:
                pending_ride.status = 'cancelled'
        
        db.session.commit()
        flash(f'Ride accepted successfully! Updated fare: ₹{new_fare:.2f}', 'success')
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error accepting ride: {str(e)}")
        flash('Something went wrong. Please try again.', 'error')
    
    return redirect(url_for('driver.dashboard'))



# Initialize EmailService
email_service = EmailService()

@bp.route('/ride/<int:ride_id>/complete', methods=['POST'])
@login_required
@role_required('driver')
def complete_ride(ride_id):
    ride = Ride.query.get_or_404(ride_id)
    
    if ride.status != 'accepted':
        flash('This ride cannot be completed.', 'error')
        return redirect(url_for('driver.dashboard'))
    
    try:
        # Complete the ride
        ride.status = 'completed'
        ride.completed_at = datetime.utcnow()
        
        # Check remaining active rides in the group
        remaining_active_rides = Ride.query.filter_by(
            ride_group_id=ride.ride_group_id,
            status='accepted'
        ).filter(
            Ride.id != ride_id
        ).count()
        
        if remaining_active_rides == 0:
            driver = ride.driver
            driver.is_available = True
        
        # Calculate CURRENT riders in THIS ride group only
        current_riders = Ride.query.filter_by(
            ride_group_id=ride.ride_group_id,
            status='accepted'
        ).count()
        
        # Include the current ride being completed
        if ride.status == 'completed':
            current_riders = max(1, current_riders)
        
        db.session.commit()
        
        try:
            fare = float(ride.get_formatted_fare())
            fare_per_rider = round(fare / current_riders, 2)
        except (ValueError, TypeError) as e:
            current_app.logger.error(f"Error calculating fare: {str(e)}")
            fare = 0
            fare_per_rider = 0
        
        ride_data = {
            'ride_id': ride.id,
            'completion_time': ride.completed_at.strftime('%Y-%m-%d %H:%M'),
            'pickup_address': ride.pickup_address,
            'driver_name': ride.driver.get_full_name(),
            'vehicle_number': ride.driver.vehicle_number,
            'fare': fare,
            'total_riders': current_riders,  # Using current_riders instead of total_riders
            'fare_per_rider': fare_per_rider,
            'rider_email': ride.rider.email
        }
        
        # Send email notification
        email_sent = email_service.send_ride_completion_email(ride_data)
        
        if email_sent:
            flash('Ride completed successfully! Receipt sent to rider.', 'success')
        else:
            flash('Ride completed successfully! (Failed to send receipt email)', 'warning')
            
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error completing ride: {str(e)}")
        flash('Something went wrong. Please try again.', 'error')
    
    return redirect(url_for('driver.dashboard'))


@bp.route('/ride/<int:ride_id>/reject', methods=['POST'])
@login_required
@role_required('driver')
def reject_ride(ride_id):
    ride = Ride.query.get_or_404(ride_id)
    
    if ride.status != 'requested':
        return jsonify({'success': False, 'message': 'This ride cannot be rejected'}), 400
    
    try:
        # Update ride status
        ride.status = 'cancelled'
        
        # Make driver available
        driver = ride.driver
        driver.is_available = True
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Ride rejected successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error rejecting ride: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'An error occurred while rejecting the ride'
        }), 500
    
@bp.route('/feedback/<int:feedback_id>/analyze', methods=['POST'])
@login_required
@role_required('driver')
def analyze_feedback(feedback_id):
    feedback = Feedback.query.get_or_404(feedback_id)
    
    # Check if this feedback belongs to the current driver
    if feedback.ride.driver_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Analyze sentiment if not already analyzed
    if feedback.sentiment_score is None:
        score = feedback.analyze_sentiment(sentiment_analyzer)
        if score is not None:
            try:
                # Get all feedback for this driver to update overall rating
                all_feedback = db.session.query(Feedback)\
                    .join(Ride)\
                    .filter(
                        Ride.driver_id == feedback.ride.driver_id,
                        Ride.status == 'completed'
                    ).all()
                
                # Update rating stats and driver rating
                rating_stats = sentiment_analyzer.update_driver_rating(
                    feedback.ride.driver, 
                    all_feedback
                )
                db.session.commit()
                return jsonify({
                    'success': True,
                    'score': score,
                    'new_rating': rating_stats['average']
                })
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Error saving sentiment score: {str(e)}")
                return jsonify({'error': 'Database error'}), 500
    
    return jsonify({'error': 'Already analyzed'}), 400