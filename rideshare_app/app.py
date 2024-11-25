from flask import Flask, redirect, url_for
from flask_login import LoginManager
from utils.db import db
from config import Config
from models.user import User
from utils.init_db import init_zones
from flask_socketio import SocketIO


app = Flask(__name__)
app.config.from_object(Config)



# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.role_selection'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)

# Register blueprints
from routes.auth import bp as auth_bp
from routes.driver import bp as driver_bp
from routes.rider import bp as rider_bp
from routes.manager import bp as manager_bp

app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(driver_bp, url_prefix='/driver')
app.register_blueprint(rider_bp, url_prefix='/rider')
app.register_blueprint(manager_bp, url_prefix='/manager')

# Create database tables and initialize data
def init_db():
    with app.app_context():
        db.create_all()
        init_zones()  # Initialize zones

@app.route('/')
def index():
    return redirect(url_for('auth.role_selection'))

if __name__ == '__main__':
    init_db()  # Initialize database tables and zones
    app.run(debug=True)