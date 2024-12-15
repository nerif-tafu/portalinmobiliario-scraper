# Scraper configuration settings

# Scraping limits (per location)
MAX_PAGES_PER_LOCATION = 1
LISTINGS_PER_PAGE = 48
LISTINGS_PER_LOCATION = 1  # Changed from TOTAL_LISTINGS_LIMIT

# Search filters
LOCATIONS = [
    "providencia-metropolitana",
    "nunoa-metropolitana",
    # "las-condes-metropolitana",
    # "la-reina-metropolitana",
    # "vitacura-metropolitana",
    # "lo-barnechea-metropolitana"
]
MIN_PRICE_CLP = 0
MAX_PRICE_CLP = 1200000
MIN_BEDROOMS = 2
ONLY_USED = True

# Base URL template
def get_url_for_location(location, offset):
    return (
        "https://www.portalinmobiliario.com/arriendo/departamento/propiedades-usadas"
        f"/{location}/_Desde_{offset}_OrderId_BEGINS*DESC_PriceRange_{MIN_PRICE_CLP}CLP-{MAX_PRICE_CLP}CLP"
        f"_BEDROOMS_{MIN_BEDROOMS}-*_NoIndex_{str(ONLY_USED)}"
    )

# Example URL Format
# https://www.portalinmobiliario.com/arriendo/departamento/propiedades-usadas/providencia-metropolitana/_Desde_0_PriceRange_0CLP-1200000CLP_BEDROOMS_2-*_NoIndex_True
