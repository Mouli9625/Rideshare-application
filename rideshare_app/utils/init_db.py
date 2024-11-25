from models.zone import Zone
from utils.db import db

def init_zones():
    # Check if zones already exist
    if Zone.query.first() is None:
        # Define the zones to be added
        zones = [
            
        ]
        
        # Add each zone to the session
        db.session.add_all(zones)  # Use add_all for better performance
        
        # Commit the changes to the database
        db.session.commit()
        print("Zones initialized successfully.")
    else:
        print("Zones already exist in the database.")
