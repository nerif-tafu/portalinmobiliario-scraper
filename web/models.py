from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Run(db.Model):
    __tablename__ = 'runs'
    
    id = db.Column(db.Integer, primary_key=True)
    started_at = db.Column(db.DateTime, nullable=False)
    completed_at = db.Column(db.DateTime)
    next_run_at = db.Column(db.DateTime)
    status = db.Column(db.String(20), nullable=False)
    total_properties = db.Column(db.Integer)
    error_message = db.Column(db.Text)
    
    properties = db.relationship('Property', backref='run', lazy=True)

    def __str__(self):
        return f"Run {self.id} ({self.started_at})"

class Property(db.Model):
    __tablename__ = 'properties'
    
    id = db.Column(db.Integer, primary_key=True)
    run_id = db.Column(db.Integer, db.ForeignKey('runs.id'))
    location = db.Column(db.String(100), nullable=False)
    title = db.Column(db.Text, nullable=False)
    price = db.Column(db.Integer, nullable=False)
    common_costs = db.Column(db.Integer)
    total_price = db.Column(db.Integer)
    total_area = db.Column(db.Float)
    floor = db.Column(db.Integer)
    total_floors = db.Column(db.Integer)
    furnished = db.Column(db.Boolean)
    has_gym = db.Column(db.Boolean)
    original_url = db.Column(db.Text, nullable=False)
    google_maps_link = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    images = db.relationship('PropertyImage', backref='property', lazy=True)
    metro_stations = db.relationship('MetroStation', backref='property', lazy=True)

    def __str__(self):
        return self.title

class PropertyImage(db.Model):
    __tablename__ = 'property_images'
    
    id = db.Column(db.Integer, primary_key=True)
    property_id = db.Column(db.Integer, db.ForeignKey('properties.id'))
    image_url = db.Column(db.Text, nullable=False)

    def __str__(self):
        return f"Image {self.id} for Property {self.property_id}"

class MetroStation(db.Model):
    __tablename__ = 'metro_stations'
    
    id = db.Column(db.Integer, primary_key=True)
    property_id = db.Column(db.Integer, db.ForeignKey('properties.id'))
    name = db.Column(db.String(100), nullable=False)
    walking_minutes = db.Column(db.Integer, nullable=False)
    distance_meters = db.Column(db.Integer, nullable=False)

    def __str__(self):
        return f"{self.name} ({self.walking_minutes} min)" 

class PropertyPreference(db.Model):
    __tablename__ = 'property_preferences'
    
    id = db.Column(db.Integer, primary_key=True)
    property_url = db.Column(db.Text, nullable=False, unique=True)
    status = db.Column(db.String(10), nullable=False)  # 'liked', 'disliked'
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow) 