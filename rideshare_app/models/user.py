from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from utils.db import db

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    @staticmethod
    def get_user(user_id):
        # Updated to use Session.get() instead of Query.get()
        return db.session.get(User, int(user_id))

    
    # Add these new fields for driver functionality
    zone_id = db.Column(db.Integer, db.ForeignKey('zones.id'))
    is_available = db.Column(db.Boolean, default=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
        
    def get_driver_details(self):
        if self.role == 'driver':
            return {
                'id': self.id,
                'username': self.username,
                'is_available': self.is_available,
                'zone_name': self.zone.name if self.zone else 'Unassigned'
            }
        return None

    def __repr__(self):
        return f'<User {self.username}>'
    