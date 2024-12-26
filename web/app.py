from flask import Flask, render_template, jsonify, request
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from web.models import db, Run, Property, PropertyImage, MetroStation, PropertyPreference
from datetime import datetime, timedelta
from sqlalchemy import desc
import os
from markupsafe import Markup
from web.utils import convert_to_embed_src

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev')
db.init_app(app)

# Create admin interface
admin = Admin(app, name='Property Scraper', template_mode='bootstrap3')

# Custom ModelViews
class RunView(ModelView):
    column_list = (
        'id', 
        'started_at', 
        'completed_at', 
        'next_run_at', 
        'status', 
        'total_properties', 
        'error_message'
    )
    column_searchable_list = ['status']
    column_filters = ['status', 'started_at', 'completed_at']
    column_formatters = {
        'started_at': lambda v, c, m, p: m.started_at.strftime('%Y-%m-%d %H:%M:%S'),
        'completed_at': lambda v, c, m, p: m.completed_at.strftime('%Y-%m-%d %H:%M:%S') if m.completed_at else '',
        'next_run_at': lambda v, c, m, p: m.next_run_at.strftime('%Y-%m-%d %H:%M:%S') if m.next_run_at else ''
    }

class PropertyView(ModelView):
    column_list = (
        'title', 
        'location', 
        'price', 
        'common_costs',
        'total_price', 
        'total_area', 
        'floor',
        'total_floors',
        'furnished', 
        'has_gym',
        'google_maps_link',
        'created_at'
    )
    column_searchable_list = ['title', 'location', 'original_url', 'google_maps_link']
    column_filters = [
        'location', 
        'furnished', 
        'has_gym',
        'price',
        'total_area',
        'created_at'
    ]
    
    def _price_formatter(view, context, model, name):
        price = getattr(model, name)
        return f"${price:,.0f}" if price else ""
    
    def _maps_link_formatter(view, context, model, name):
        link = getattr(model, name)
        if link:
            return Markup(f'<a href="{link}" target="_blank">View on Maps</a>')
        return ''
    
    column_formatters = {
        'price': _price_formatter,
        'common_costs': _price_formatter,
        'total_price': _price_formatter,
        'created_at': lambda v, c, m, p: m.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        'google_maps_link': _maps_link_formatter
    }
    
    # Allow HTML in the google_maps_link column
    can_view_details = True
    column_display_pk = True

class PropertyImageView(ModelView):
    column_list = ('property', 'image_url')
    column_searchable_list = ['image_url']

class MetroStationView(ModelView):
    column_list = (
        'property', 
        'name', 
        'walking_minutes', 
        'distance_meters'
    )
    column_searchable_list = ['name']
    column_filters = [
        'name', 
        'walking_minutes'
    ]
    column_sortable_list = [
        'walking_minutes', 
        'distance_meters'
    ]

class PropertyPreferenceView(ModelView):
    column_list = (
        'property_url',
        'status',
        'created_at'
    )
    column_searchable_list = ['property_url', 'status']
    column_filters = ['status', 'created_at']
    column_formatters = {
        'created_at': lambda v, c, m, p: m.created_at.strftime('%Y-%m-%d %H:%M:%S')
    }

# Add views
admin.add_view(RunView(Run, db.session))
admin.add_view(PropertyView(Property, db.session))
admin.add_view(PropertyImageView(PropertyImage, db.session))
admin.add_view(MetroStationView(MetroStation, db.session))
admin.add_view(PropertyPreferenceView(PropertyPreference, db.session))

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

@app.route('/api/properties')
def get_properties():
    page = request.args.get('page', 1, type=int)
    per_page = 100
    
    # Get paginated properties
    query = (
        db.session.query(Property)
        .join(Run)
        .order_by(Run.started_at.desc())
    )
    
    # Get total count
    total_count = query.count()
    
    # Apply pagination
    properties = query.offset((page - 1) * per_page).limit(per_page).all()
    
    # Get preferences for these properties
    property_urls = [p.original_url for p in properties]
    preferences = {
        pref.property_url: pref.status 
        for pref in PropertyPreference.query.filter(
            PropertyPreference.property_url.in_(property_urls)
        ).all()
    }
    
    # Format properties for JSON response
    properties_data = []
    for prop in properties:
        property_data = {
            'url': prop.original_url,
            'title': prop.title,
            'location': prop.location,
            'price': prop.price,
            'common_costs': prop.common_costs,
            'total_price': prop.total_price,
            'total_area': prop.total_area,
            'floor': prop.floor,
            'total_floors': prop.total_floors,
            'furnished': prop.furnished,
            'has_gym': prop.has_gym,
            'google_maps_link': prop.google_maps_link,
            'created_at': prop.run.started_at.strftime('%Y-%m-%d %H:%M'),
            'images': [{'url': img.image_url} for img in prop.images],
            'metro_stations': [
                {
                    'name': station.name,
                    'walking_minutes': station.walking_minutes
                } for station in prop.metro_stations
            ],
            'preference': preferences.get(prop.original_url)
        }
        properties_data.append(property_data)
    
    return jsonify({
        'properties': properties_data,
        'total': total_count,
        'page': page,
        'per_page': per_page,
        'total_pages': (total_count + per_page - 1) // per_page
    })

@app.route('/')
def index():
    run_id = request.args.get('run_id')
    page = request.args.get('page', 1, type=int)
    per_page = 100
    
    # Get filter parameters
    hide_liked = request.args.get('hide_liked') == 'true'
    hide_disliked = request.args.get('hide_disliked') == 'true'
    hide_unseen = request.args.get('hide_unseen') == 'true'
    
    # Get all properties across all runs, ordered by newest first
    query = (
        db.session.query(Property)
        .join(Run)
        .order_by(Run.started_at.desc())
    )
    
    # Get total count for pagination
    total_count = query.count()
    total_pages = (total_count + per_page - 1) // per_page
    
    # Apply pagination
    properties = query.offset((page - 1) * per_page).limit(per_page).all()
    
    # Get preferences for these properties
    property_urls = [p.original_url for p in properties]
    preferences = {
        pref.property_url: pref 
        for pref in PropertyPreference.query.filter(
            PropertyPreference.property_url.in_(property_urls)
        ).all()
    }
    
    # Attach preferences to properties
    for prop in properties:
        prop.preference = preferences.get(prop.original_url)
    
    # Group properties by location
    properties_by_location = {}
    for prop in properties:
        if prop.location not in properties_by_location:
            properties_by_location[prop.location] = []
        properties_by_location[prop.location].append(prop)

    return render_template(
        'index.html',
        properties_by_location=properties_by_location,
        total_properties=total_count,
        current_page=page,
        total_pages=total_pages,
        hide_liked=hide_liked,
        hide_disliked=hide_disliked,
        hide_unseen=hide_unseen
    )

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

@app.template_filter('format_number')
def format_number(value):
    """Format number with thousands separator"""
    return "{:,.0f}".format(value) if value else ""

@app.template_filter('convert_to_embed')
def convert_to_embed_filter(url):
    """Template filter to convert Google Maps URL to embed URL"""
    return convert_to_embed_src(url)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000) 