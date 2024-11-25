from utils.db import db

class Zone(db.Model):
    __tablename__ = 'zones'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(200))
    drivers = db.relationship('User', backref='zone', lazy=True)
    
    def __repr__(self):
        return f'<Zone {self.name}>'