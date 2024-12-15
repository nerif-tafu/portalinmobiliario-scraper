from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
from datetime import datetime

from web.models import Run, Property, PropertyImage, MetroStation

# Create database engine
engine = create_engine(os.getenv('DATABASE_URL'))
Session = sessionmaker(bind=engine)

def save_properties(properties, run_id):
    """Save scraped properties to database"""
    if not properties:
        print("No properties to save")
        return

    session = Session()
    try:
        for prop_data in properties:
            # Create property
            property = Property(
                run_id=run_id,
                location=prop_data['location'],
                title=prop_data['title'],
                price=prop_data['price'],
                common_costs=prop_data.get('common_costs'),
                total_price=prop_data.get('total_price'),
                total_area=float(prop_data['total_area']) if prop_data.get('total_area') else None,
                floor=prop_data.get('floor'),
                total_floors=prop_data.get('total_floors'),
                furnished=prop_data.get('furnished'),
                has_gym=prop_data.get('has_gym'),
                original_url=prop_data['link'],
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
            for station_data in prop_data.get('metro_station', []):
                station = MetroStation(
                    property_id=property.id,
                    name=station_data['name'],
                    walking_minutes=station_data['walking_minutes'],
                    distance_meters=station_data['distance_meters']
                )
                session.add(station)

        session.commit()
        print(f"Successfully saved {len(properties)} properties to database")

    except Exception as e:
        session.rollback()
        print(f"Error in save_properties: {str(e)}")
        raise
    finally:
        session.close() 