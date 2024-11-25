from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file
from flask_login import login_required, current_user
from utils.decorators import role_required
from models.drivers import Driver
from models.user import User
from models.zone import Zone
from utils.db import db
from models.ride import RiderAddress, Ride
from datetime import datetime
from models.ride import Ride
from sqlalchemy import func, extract
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from io import BytesIO
from datetime import datetime
import re



bp = Blueprint('manager', __name__, url_prefix='/manager')

@bp.route('/dashboard')
@login_required
@role_required('manager')
def dashboard():
    try:
        # Get current date for today's statistics
        today = datetime.utcnow().date()
        
        # Calculate statistics
        stats = {
            'total_drivers': Driver.query.count(),
            'active_drivers': Driver.query.filter_by(is_available=True).count(),
            'active_zones': Zone.query.count(),
            'today_rides': Ride.query.filter(
                func.date(Ride.created_at) == today
            ).count(),
            'completed_rides': Ride.query.filter(
                func.date(Ride.created_at) == today,
                Ride.status == 'completed'
            ).count(),
            'avg_rating': db.session.query(func.avg(Driver.rating)).scalar() or 0,
            'total_ratings': Driver.query.filter(Driver.rating > 0).count(),
        }
        
        # Calculate average drivers per zone
        if stats['active_zones'] > 0:
            stats['drivers_per_zone'] = round(stats['total_drivers'] / stats['active_zones'], 1)
        else:
            stats['drivers_per_zone'] = 0
            
        # Get recent drivers (last 5)
        recent_drivers = Driver.query.order_by(Driver.id.desc()).limit(5).all()
        
        # Get recent addresses (last 5)
        recent_addresses = RiderAddress.query.order_by(RiderAddress.created_at.desc()).limit(5).all()

        
        
        return render_template('manager/dashboard.html',
                             stats=stats,
                             recent_drivers=recent_drivers,
                             recent_addresses=recent_addresses)
                             
    except Exception as e:
        print(f"Error in dashboard route: {str(e)}")
        flash(f'Error loading dashboard: {str(e)}', 'error')
        return render_template('manager/dashboard.html',
                             stats={},
                             recent_drivers=[],
                             recent_addresses=[])

@bp.route('/drivers')
@login_required
@role_required('manager')
def drivers():
    try:
        drivers = Driver.query.all()
        return render_template('manager/drivers.html', drivers=drivers)
    except Exception as e:
        print(f"Error in drivers route: {str(e)}")
        flash(f'Error loading drivers: {str(e)}', 'error')
        return render_template('manager/drivers.html', drivers=[])

@bp.route('/add_driver', methods=['GET', 'POST'])
@login_required
@role_required('manager')
def add_driver():
    try:
        # Get all zones - removed is_active filter since it doesn't exist
        zones = Zone.query.all()
        
        if not zones:
            flash('No zones available. Please add zones first.', 'error')
            return redirect(url_for('manager.dashboard'))
            
        if request.method == 'POST':
            # Get form data
            first_name = request.form['first_name'].strip()
            last_name = request.form['last_name'].strip()
            email = request.form['email'].strip()
            phone_number = request.form['phone_number'].strip()
            license_number = request.form['license_number'].strip()
            vehicle_number = request.form['vehicle_number'].strip()
            vehicle_type = request.form['vehicle_type']
            zone_name = request.form.get('zone_name')

            # Basic validation
            if not all([first_name, last_name, email, phone_number, license_number, vehicle_number, vehicle_type, zone_name]):
                flash('All fields are required', 'error')
                return render_template('manager/add_driver.html', zones=zones)

            # Check if email already exists
            if Driver.query.filter_by(email=email).first() or User.query.filter_by(email=email).first():
                flash('Email already registered', 'error')
                return render_template('manager/add_driver.html', zones=zones)

            # Find zone by name - removed is_active filter
            zone = Zone.query.filter_by(name=zone_name).first()
            if not zone:
                flash('Selected zone is not valid', 'error')
                return render_template('manager/add_driver.html', zones=zones)
            
            zone_id = zone.id

            # Generate driver_id
            latest_driver = Driver.query.order_by(Driver.id.desc()).first()
            next_id = 1 if not latest_driver else latest_driver.id + 1
            driver_id = f'DRV{next_id:04d}'

            # Create new driver
            driver = Driver(
                driver_id=driver_id,
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone_number=phone_number,
                license_number=license_number,
                vehicle_number=vehicle_number,
                vehicle_type=vehicle_type,
                zone_id=zone_id,
                rating=0.0,
                is_available=True
            )

            # Create user account for driver
            username = f"{first_name.lower()}_{driver_id}"
            password = f"{first_name.lower()}_{driver_id}"  # Initial password
            
            user = User(
                username=username,
                email=email,
                role='driver',
                zone_id=zone_id,
                is_available=True
            )
            user.set_password(password)

            # Add to database
            db.session.add(driver)
            db.session.add(user)
            db.session.commit()

            flash(f'Driver added successfully! Username: {username}, Password: {password}', 'success')
            return redirect(url_for('manager.drivers'))

    except Exception as e:
        db.session.rollback()
        print(f"Error in add_driver route: {str(e)}")
        flash(f'Error adding driver: {str(e)}', 'error')
        zones = []  # Set zones to empty list in case of error
        
    return render_template('manager/add_driver.html', zones=zones)

@bp.route('/edit_driver/<string:driver_id>', methods=['GET', 'POST'])
@login_required
@role_required('manager')
def edit_driver(driver_id):
    try:
        driver = Driver.query.filter_by(driver_id=driver_id).first()
        if not driver:
            flash('Driver not found', 'error')
            return redirect(url_for('manager.drivers'))

        zones = Zone.query.all()
        
        if request.method == 'POST':
            # Get form data
            first_name = request.form['first_name'].strip()
            last_name = request.form['last_name'].strip()
            email = request.form['email'].strip()
            phone_number = request.form['phone_number'].strip()
            license_number = request.form['license_number'].strip()
            vehicle_number = request.form['vehicle_number'].strip()
            vehicle_type = request.form['vehicle_type']
            zone_name = request.form.get('zone_name')

            # Basic validation
            if not all([first_name, last_name, email, phone_number, license_number, vehicle_number, vehicle_type, zone_name]):
                flash('All fields are required', 'error')
                return render_template('manager/edit_driver.html', driver=driver, zones=zones)

            # Check if email already exists and it's not the current driver's email
            existing_driver = Driver.query.filter(Driver.email == email, Driver.driver_id != driver_id).first()
            existing_user = User.query.filter(User.email == email, User.email != driver.email).first()
            if existing_driver or existing_user:
                flash('Email already registered', 'error')
                return render_template('manager/edit_driver.html', driver=driver, zones=zones)

            # Find zone by name
            zone = Zone.query.filter_by(name=zone_name).first()
            if not zone:
                flash('Selected zone is not valid', 'error')
                return render_template('manager/edit_driver.html', driver=driver, zones=zones)
            
            # Update driver information
            driver.first_name = first_name
            driver.last_name = last_name
            driver.email = email
            driver.phone_number = phone_number
            driver.license_number = license_number
            driver.vehicle_number = vehicle_number
            driver.vehicle_type = vehicle_type
            driver.zone_id = zone.id

            # Update associated user account
            user = User.query.filter_by(email=driver.email).first()
            if user:
                user.email = email
                user.zone_id = zone.id

            db.session.commit()
            flash('Driver updated successfully!', 'success')
            return redirect(url_for('manager.drivers'))

        return render_template('manager/edit_driver.html', driver=driver, zones=zones)

    except Exception as e:
        db.session.rollback()
        print(f"Error in edit_driver route: {str(e)}")
        flash(f'Error updating driver: {str(e)}', 'error')
        return redirect(url_for('manager.drivers'))

@bp.route('/delete_driver/<string:driver_id>', methods=['POST'])
@login_required
@role_required('manager')
def delete_driver(driver_id):
    try:
        driver = Driver.query.filter_by(driver_id=driver_id).first()
        if not driver:
            flash('Driver not found', 'error')
            return redirect(url_for('manager.drivers'))

        # Delete associated user account
        user = User.query.filter_by(email=driver.email).first()
        if user:
            db.session.delete(user)

        # Delete driver
        db.session.delete(driver)
        db.session.commit()

        flash('Driver deleted successfully!', 'success')
        return redirect(url_for('manager.drivers'))

    except Exception as e:
        db.session.rollback()
        print(f"Error in delete_driver route: {str(e)}")
        flash(f'Error deleting driver: {str(e)}', 'error')
        return redirect(url_for('manager.drivers'))
    
@bp.route('/rider_address', methods=['GET', 'POST'])
@login_required
@role_required('manager')
def rider_address():
    try:
        if request.method == 'POST':
            email = request.form.get('email', '').strip()
            
            if not email:
                flash('Please enter an email address', 'error')
                return render_template('manager/rider_address.html')
            
            rider_address = RiderAddress.query.filter_by(email=email).first()
            
            if not rider_address:
                flash('No address found for this email address', 'error')
                return render_template('manager/rider_address.html')
                
            return render_template('manager/rider_address.html', rider_address=rider_address)
            
        return render_template('manager/rider_address.html')
        
    except Exception as e:
        print(f"Error in rider_address route: {str(e)}")
        flash(f'Error looking up address: {str(e)}', 'error')
        return render_template('manager/rider_address.html')

@bp.route('/add_rider_address', methods=['GET', 'POST'])
@login_required
@role_required('manager')
def add_rider_address():
    try:
        if request.method == 'POST':
            email = request.form.get('email', '').strip()
            phone_number = request.form.get('phone_number', '').strip()
            street_address = request.form.get('street_address', '').strip()
            city = request.form.get('city', '').strip()
            state = request.form.get('state', '').strip()
            postal_code = request.form.get('postal_code', '').strip()
            country = request.form.get('country', 'India').strip()
            
            if not all([email, street_address, city, state, postal_code]):
                flash('All fields are required', 'error')
                return render_template('manager/add_rider_address.html')
            
            # Check if address already exists for this email
            existing_address = RiderAddress.query.filter_by(email=email).first()
            if existing_address:
                flash('Address already exists for this email. Use edit function instead.', 'error')
                return render_template('manager/add_rider_address.html')
            
            rider_address = RiderAddress(
                email=email,
                phone_number=phone_number,
                street_address=street_address,
                city=city,
                state=state,
                postal_code=postal_code,
                country=country
            )
            
            db.session.add(rider_address)
            db.session.commit()
            
            flash('Rider address added successfully!', 'success')
            return redirect(url_for('manager.rider_address'))
            
        return render_template('manager/add_rider_address.html')
        
    except Exception as e:
        db.session.rollback()
        print(f"Error in add_rider_address route: {str(e)}")
        flash(f'Error adding address: {str(e)}', 'error')
        return render_template('manager/add_rider_address.html')
    

@bp.route('/ride_history_report', methods=['GET', 'POST'])
@login_required
@role_required('manager')
def ride_history_report():
    """
    Generate a ride history report with properly formatted addresses
    """
    try:
        # Handle GET request
        if request.method == 'GET':
            years = db.session.query(extract('year', Ride.created_at).distinct()).order_by().all()
            years = [int(year[0]) for year in years]
            return render_template('manager/ride_history_report.html', years=years)
        
        # Handle POST request
        if request.method == 'POST':
            year = int(request.form.get('year'))
            month = int(request.form.get('month'))
            
            rides = Ride.query.filter(
                extract('year', Ride.created_at) == year,
                extract('month', Ride.created_at) == month
            ).all()
            
            if not rides:
                flash(f'No rides found for {datetime(year, month, 1).strftime("%B %Y")}', 'warning')
                return redirect(url_for('manager.ride_history_report'))
            
            # Create PDF
            buffer = BytesIO()
            doc = SimpleDocTemplate(
                buffer,
                pagesize=landscape(letter),
                rightMargin=30,
                leftMargin=30,
                topMargin=30,
                bottomMargin=30
            )
            
            # Get styles
            styles = getSampleStyleSheet()
            
            # Create custom style for address cells
            address_style = ParagraphStyle(
                'AddressStyle',
                parent=styles['Normal'],
                fontSize=8,
                leading=10,
                wordWrap='CJK',
                alignment=1  # Center alignment
            )
            
            # Create custom style for other cells
            cell_style = ParagraphStyle(
                'CellStyle',
                parent=styles['Normal'],
                fontSize=8,
                leading=10,
                alignment=1  # Center alignment
            )
            
            # Prepare data for the table
            data = [[
                Paragraph('<b>Ride ID</b>', cell_style),
                Paragraph('<b>Rider</b>', cell_style),
                Paragraph('<b>Driver</b>', cell_style),
                Paragraph('<b>Pickup Address</b>', cell_style),
                Paragraph('<b>Status</b>', cell_style),
                Paragraph('<b>Created At</b>', cell_style)
            ]]
            
            # Format address function
            def format_address(address):
                if not address:
                    return "N/A"
                
                # Split address by commas
                parts = address.split(',')
                
                # Group parts into 2-3 lines
                if len(parts) > 4:
                    # For very long addresses
                    formatted_parts = [
                        ', '.join(parts[:2]),
                        ', '.join(parts[2:4]),
                        ', '.join(parts[4:])
                    ]
                else:
                    # For shorter addresses
                    mid = len(parts) // 2
                    formatted_parts = [
                        ', '.join(parts[:mid]),
                        ', '.join(parts[mid:])
                    ]
                
                return '<br/>'.join(formatted_parts)
            
            # Add ride data
            for ride in rides:
                formatted_address = format_address(ride.pickup_address)
                
                row = [
                    Paragraph(str(ride.id), cell_style),
                    Paragraph(ride.rider.username if ride.rider else 'N/A', cell_style),
                    Paragraph(f"{ride.driver.first_name} {ride.driver.last_name}" if ride.driver else 'N/A', cell_style),
                    Paragraph(formatted_address, address_style),
                    Paragraph(ride.status, cell_style),
                    Paragraph(ride.created_at.strftime('%Y-%m-%d<br/>%H:%M:%S'), cell_style)
                ]
                data.append(row)
            
            # Create table with specific column widths
            col_widths = [40, 80, 100, 280, 60, 80]  # Adjusted widths
            table = Table(data, colWidths=col_widths, repeatRows=1)
            
            # Add table styling
            table.setStyle(TableStyle([
                # Headers
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                
                # Cell alignment
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                
                # Borders
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                ('BOX', (0, 0), (-1, -1), 1, colors.black),
                
                # Row colors
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
                
                # Padding
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                ('LEFTPADDING', (0, 0), (-1, -1), 3),
                ('RIGHTPADDING', (0, 0), (-1, -1), 3),
            ]))
            
            # Create title
            title = Paragraph(
                f"Ride History Report - {datetime(year, month, 1).strftime('%B %Y')}",
                styles['Title']
            )
            
            # Add statistics
            total_rides = len(rides)
            completed_rides = sum(1 for ride in rides if ride.status == 'completed')
            stats = Paragraph(
                f"""
                <br/>
                <b>Total Rides:</b> {total_rides}<br/>
                <b>Completed Rides:</b> {completed_rides}<br/>
                <b>Completion Rate:</b> {(completed_rides/total_rides*100 if total_rides > 0 else 0):.1f}%
                """,
                styles['Normal']
            )
            
            # Build PDF
            elements = [
                title,
                Spacer(1, 20),
                stats,
                Spacer(1, 20),
                table
            ]
            
            doc.build(elements)
            
            # Prepare file for download
            buffer.seek(0)
            return send_file(
                buffer,
                as_attachment=True,
                download_name=f'ride_history_{year}_{month:02d}.pdf',
                mimetype='application/pdf'
            )
            
    except Exception as e:
        print(f"Error in ride history report route: {str(e)}")
        flash(f'Error generating report: {str(e)}', 'error')
        return redirect(url_for('manager.dashboard'))