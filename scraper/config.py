# Scraper configuration settings

import os

# Scraping limits (per location)
MAX_PAGES_PER_LOCATION = int(os.getenv('MAX_PAGES_PER_LOCATION', 1))
LISTINGS_PER_PAGE = int(os.getenv('LISTINGS_PER_PAGE', 48))  # Set to None for all listings on page

# Search filters
LOCATIONS = [
    # "providencia-metropolitana",
    # "nunoa-metropolitana",
    # "las-condes-metropolitana",
    "la-reina-metropolitana",
    # "vitacura-metropolitana",
    # "lo-barnechea-metropolitana"
]
MIN_PRICE_CLP = 0
MAX_PRICE_CLP = 1200000
MIN_BEDROOMS = 2
ONLY_USED = True

# Base URL template
def get_url_for_location(location, offset=0):
    """Get URL for location with offset"""
    base_url = 'https://www.portalinmobiliario.com/arriendo/departamento'
    return f'{base_url}/{location}/_Desde_{offset + 1}_NoIndex_True'

# Example URL Format
# https://www.portalinmobiliario.com/arriendo/departamento/propiedades-usadas/providencia-metropolitana/_Desde_0_PriceRange_0CLP-1200000CLP_BEDROOMS_2-*_NoIndex_True
