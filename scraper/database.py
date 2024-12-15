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
        return []

    if not isinstance(properties, list):
        print(f"Error: properties must be a list, got {type(properties)}")
        print(f"Properties value: {properties}")
        return []

    session = Session()
    try:
        for i, prop_data in enumerate(properties):
            try:
                # Create property
                if not isinstance(prop_data, dict):
                    print(f"Error: property data must be a dict, got {type(prop_data)}")
                    print(f"Property data at index {i}: {prop_data}")
                    continue

                property = Property(
                    run_id=run_id,
                    location=prop_data.get('location', ''),
                    title=prop_data.get('title', ''),
                    price=prop_data.get('price', 0),
                    common_costs=prop_data.get('common_costs'),
                    total_price=prop_data.get('total_price'),
                    total_area=float(prop_data['total_area']) if prop_data.get('total_area') else None,
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

                # Add metro stations if they exist
                metro_stations = prop_data.get('metro_station', []) or []  # Convert None to empty list
                for station_data in metro_stations:
                    station = MetroStation(
                        property_id=property.id,
                        name=station_data['name'],
                        walking_minutes=station_data['walking_minutes'],
                        distance_meters=station_data['distance_meters']
                    )
                    session.add(station)

            except Exception as e:
                print(f"Error processing property at index {i}:")
                print(f"Property data: {prop_data}")
                print(f"Error: {str(e)}")
                raise

        session.commit()
        print(f"Successfully saved {len(properties)} properties to database")
        return properties

    except Exception as e:
        session.rollback()
        print(f"Error in save_properties:")
        print(f"Properties type: {type(properties)}")
        print(f"Properties value: {properties}")
        print(f"Error: {str(e)}")
        raise
    finally:
        session.close() 