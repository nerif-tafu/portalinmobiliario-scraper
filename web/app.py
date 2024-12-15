from flask import Flask, render_template, jsonify, request
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from web.models import db, Run, Property, PropertyImage, MetroStation, PropertyPreference
from datetime import datetime, timedelta
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
    latest_run = Run.query.order_by(Run.started_at.desc()).first()
    
    if not latest_run:
        return jsonify({
            'status': 'No runs found',
            'message': 'No scraping runs yet'
        })

    if latest_run.status == 'running':
        started_minutes_ago = int((datetime.utcnow() - latest_run.started_at).total_seconds() / 60)
        message = f"In progress - started {started_minutes_ago} minutes ago"
    elif latest_run.status == 'failed':
        message = f"Failed - {latest_run.error_message}"
    else:  # completed
        if latest_run.next_run_at:
            next_run_str = latest_run.next_run_at.strftime('%Y-%m-%d %H:%M:%S')
            message = f"Waiting - next run at {next_run_str}"
        else:
            # Fallback for runs before we added next_run_at
            message = "Waiting for next run"

    return jsonify({
        'status': latest_run.status,
        'message': message
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
    
    # Get preferences for all properties
    property_urls = [p.original_url for p in properties]
    preferences = {p.property_url: p for p in PropertyPreference.query.filter(
        PropertyPreference.property_url.in_(property_urls)
    ).all()}
    
    # Attach preferences to properties
    for property in properties:
        property.preference = preferences.get(property.original_url)
    
    # Count unique properties by URL
    total_unique_properties = db.session.query(Property.original_url).distinct().count()
    
    return render_template('index.html', 
                         latest_run=run, 
                         total_properties=total_unique_properties,
                         total_runs=total_runs,
                         runs=runs,
                         properties=properties)

@app.route('/property/preference', methods=['POST'])
def set_preference():
    data = request.json
    property_url = data.get('property_url')
    status = data.get('status')
    
    if not property_url or status not in ['liked', 'disliked']:
        return jsonify({'success': False, 'error': 'Invalid data'}), 400
    
    preference = PropertyPreference.query.filter_by(property_url=property_url).first()
    if preference:
        preference.status = status
    else:
        preference = PropertyPreference(property_url=property_url, status=status)
        db.session.add(preference)
    
    db.session.commit()
    return jsonify({'success': True})

@app.route('/property/preference', methods=['DELETE'])
def remove_preference():
    data = request.json
    property_url = data.get('property_url')
    
    if not property_url:
        return jsonify({'success': False, 'error': 'Invalid data'}), 400
    
    preference = PropertyPreference.query.filter_by(property_url=property_url).first()
    if preference:
        db.session.delete(preference)
        db.session.commit()
    
    return jsonify({'success': True})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000) 