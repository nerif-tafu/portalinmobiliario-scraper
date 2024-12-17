from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
import os
from datetime import datetime
from tenacity import retry, stop_after_attempt, wait_exponential

from web.models import Run, Property, PropertyImage, MetroStation

# Create database engine
engine = create_engine(os.getenv('DATABASE_URL'))
SessionFactory = sessionmaker(bind=engine)
Session = scoped_session(SessionFactory)

# Export Session for use in other modules
__all__ = ['Session', 'get_db_session', 'save_property', 'save_single_property', 'is_duplicate_listing']

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def get_db_session():
    """Get a scoped database session with retry logic"""
    try:
        session = Session()
        # Test the connection
        session.execute("SELECT 1")
        return session
    except Exception as e:
        log_and_print(f"Database connection failed: {str(e)}", level='error')
        raise

def clean_area(area_str):
    """Clean and convert area string to float"""
    if not area_str:
        return None
        
    try:
        # Remove any non-numeric characters except decimal point
        area_str = area_str.strip()
        
        # If it's a range, take the first number
        if ' a ' in area_str:
            area_str = area_str.split(' a ')[0]
            
        # Remove any remaining non-numeric chars except decimal
        clean_str = ''.join(c for c in area_str if c.isdigit() or c == '.')
        return float(clean_str) if clean_str else None
        
    except (ValueError, TypeError):
        print(f"Warning: Could not convert area '{area_str}' to float")
        return None

def is_duplicate_listing(session, url):
    """Check if a listing URL has been scraped before"""
    return session.query(Property).filter(Property.original_url == url).first() is not None

def save_property(prop_data, run_id):
    """Save a single property to database"""
    if not prop_data:
        print("No property data to save")
        return None

    session = Session()
    try:
        # Create property
        property = Property(
            run_id=run_id,
            location=prop_data.get('location', ''),
            title=prop_data.get('title', ''),
            price=prop_data.get('price', 0),
            common_costs=prop_data.get('common_costs'),
            total_price=prop_data.get('total_price'),
            total_area=clean_area(prop_data.get('total_area')),
            floor=prop_data.get('floor'),
            total_floors=prop_data.get('total_floors'),
            furnished=prop_data.get('furnished'),
            has_gym=prop_data.get('has_gym'),
            original_url=prop_data.get('link', ''),
            google_maps_link=prop_data.get('google_maps_link')
        )
        session.add(property)
        session.flush()  # Get property.id

        # Add images
        for image_url in prop_data.get('images', []):
            image = PropertyImage(
                property_id=property.id,
                image_url=image_url
            )
            session.add(image)

        # Add metro stations
        metro_stations = prop_data.get('metro_station', []) or []
        for station_data in metro_stations:
            station = MetroStation(
                property_id=property.id,
                name=station_data['name'],
                walking_minutes=station_data['walking_minutes'],
                distance_meters=station_data['distance_meters']
            )
            session.add(station)

        session.commit()
        print(f"Successfully saved property: {prop_data.get('title')}")
        return property

    except Exception as e:
        session.rollback()
        print(f"Error saving property: {str(e)}")
        raise
    finally:
        session.close()

def save_single_property(prop_data, run_id):
    """Save a single property to database"""
    session = Session()
    try:
        # Check if listing already exists
        if is_duplicate_listing(session, prop_data.get('link', '')):
            return None

        # Create property
        property = Property(
            run_id=run_id,
            location=prop_data.get('location', ''),
            title=prop_data.get('title', ''),
            price=prop_data.get('price', 0),
            common_costs=prop_data.get('common_costs'),
            total_price=prop_data.get('total_price'),
            total_area=clean_area(prop_data.get('total_area')),
            floor=prop_data.get('floor'),
            total_floors=prop_data.get('total_floors'),
            furnished=prop_data.get('furnished'),
            has_gym=prop_data.get('has_gym'),
            original_url=prop_data.get('link', ''),
            google_maps_link=prop_data.get('google_maps_link')
        )
        session.add(property)
        session.flush()

        # Add images
        for image_url in prop_data.get('images', []):
            image = PropertyImage(
                property_id=property.id,
                image_url=image_url
            )
            session.add(image)

        # Add metro stations
        metro_stations = prop_data.get('metro_station', []) or []
        for station_data in metro_stations:
            station = MetroStation(
                property_id=property.id,
                name=station_data['name'],
                walking_minutes=station_data['walking_minutes'],
                distance_meters=station_data['distance_meters']
            )
            session.add(station)

        session.commit()
        return property

    except Exception as e:
        session.rollback()
        raise
    finally:
        session.close() 