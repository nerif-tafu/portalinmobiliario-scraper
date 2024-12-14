# Scraper configuration settings

# Scraping limits
MAX_PAGES = 1
LISTINGS_PER_PAGE = 48
TOTAL_LISTINGS_LIMIT = 4

# Search filters
LOCATION = "providencia-metropolitana"
MIN_PRICE_CLP = 0
MAX_PRICE_CLP = 1200000
MIN_BEDROOMS = 2
ONLY_USED = True

# Base URL template
BASE_URL = (
    "https://www.portalinmobiliario.com/arriendo/departamento/propiedades-usadas"
    f"/{LOCATION}/_Desde_{{offset}}_PriceRange_{MIN_PRICE_CLP}CLP-{MAX_PRICE_CLP}CLP"
    f"_BEDROOMS_{MIN_BEDROOMS}-*_NoIndex_{str(ONLY_USED)}"
) 