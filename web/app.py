from flask import Flask, render_template, jsonify, request
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from web.models import db, Run, Property, PropertyImage, MetroStation
from datetime import datetime
from sqlalchemy import desc
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev')
db.init_app(app)

# Create admin interface
admin = Admin(app, name='Property Scraper', template_mode='bootstrap3')

# Custom ModelViews
class RunView(ModelView):
    column_list = ('id', 'started_at', 'completed_at', 'status', 'total_properties')
    column_searchable_list = ['status']
    column_filters = ['status', 'started_at']

class PropertyView(ModelView):
    column_list = ('title', 'location', 'price', 'total_price', 'total_area', 'furnished', 'has_gym')
    column_searchable_list = ['title', 'location']
    column_filters = ['location', 'furnished', 'has_gym']
    
    def _price_formatter(view, context, model, name):
        price = getattr(model, name)
        return f"${price:,.0f}" if price else ""
    
    column_formatters = {
        'price': _price_formatter,
        'total_price': _price_formatter
    }

class PropertyImageView(ModelView):
    column_list = ('property', 'image_url')
    column_searchable_list = ['image_url']

class MetroStationView(ModelView):
    column_list = ('property', 'name', 'walking_minutes', 'distance_meters')
    column_searchable_list = ['name']
    column_filters = ['name', 'walking_minutes']

# Add views
admin.add_view(RunView(Run, db.session))
admin.add_view(PropertyView(Property, db.session))
admin.add_view(PropertyImageView(PropertyImage, db.session))
admin.add_view(MetroStationView(MetroStation, db.session))

@app.route('/status')
def status():
    # Get the latest run
    latest_run = Run.query.order_by(Run.started_at.desc()).first()
    
    if not latest_run:
        return jsonify({
            'status': 'No runs found',
            'last_run': None,
            'properties_count': 0
        })

    # Calculate time since last run
    time_since = datetime.utcnow() - latest_run.started_at
    minutes_since = int(time_since.total_seconds() / 60)

    return jsonify({
        'status': latest_run.status,
        'last_run': {
            'id': latest_run.id,
            'started_at': latest_run.started_at.isoformat(),
            'completed_at': latest_run.completed_at.isoformat() if latest_run.completed_at else None,
            'minutes_ago': minutes_since,
            'total_properties': latest_run.total_properties,
            'error_message': latest_run.error_message
        },
        'properties_count': Property.query.count()
    })

@app.route('/')
def index():
    run_id = request.args.get('run_id')
    if run_id:
        run = Run.query.get_or_404(run_id)
    else:
        run = Run.query.order_by(Run.started_at.desc()).first()
    
    total_properties = Property.query.count()
    total_runs = Run.query.count()
    runs = Run.query.order_by(Run.started_at.desc()).all()
    properties = Property.query.filter_by(run_id=run.id if run else None).all()

    # Process Google Maps links
    for property in properties:
        if property.google_maps_link:
            try:
                if '@' in property.google_maps_link:
                    coords = property.google_maps_link.split('@')[1].split(',')[:2]
                else:
                    coords = property.google_maps_link.split('ll=')[1].split('&')[0].split(',')
                property.map_coords = ','.join(coords)
            except:
                property.map_coords = None
    
    return render_template('index.html', 
                         latest_run=run, 
                         total_properties=total_properties,
                         total_runs=total_runs,
                         runs=runs,
                         properties=properties)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000) 