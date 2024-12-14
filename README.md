# Property Scraper for Portal Inmobiliario

A Python web scraper designed to collect rental property listings from Portal Inmobiliario.

## Features

- Scrapes detailed property information including:
  - Property title and price
  - Images
  - Full address with Google Maps link
  - Nearby metro stations with walking distances
  - Common costs
  - Property specifications (area, floor, bedrooms, etc.)
  - Amenities (gym, furnished status, etc.)
- Rate limiting protection and retry mechanisms
- Random delays and user agent rotation
- Exports data to both JSON and HTML formats
- Automatic HTML report generation with visual representation

## Prerequisites

- Python 3.7+
- Google Chrome browser
- pip (Python package installer)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/nerif-tafu/portalinmobiliario-scraper.git
cd portalinmobiliario-scraper
```

2. Create a virtual environment (recommended):
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
```

3. Install required packages:
```bash
pip install -r requirements.txt
```

## Usage

Run the scraper with default settings:
```bash
python scrape.py
```

The script will:
1. Scrape property listings from Portal Inmobiliario
2. Save the data in JSON format
3. Generate an HTML report
4. Automatically open the HTML report in your default browser

### Configuration

You can modify these parameters in `config.py`:
- `max_pages`: Maximum number of pages to scrape
- `listings_per_page`: Number of listings to scrape per page
- `total_listings_limit`: Total number of listings to collect
- `location`: Target area for property search
- `min_price_clp`: Minimum price in CLP
- `max_price_clp`: Maximum price in CLP
- `min_bedrooms`: Minimum number of bedrooms
- `only_used`: Whether to only show used properties

Example configuration in `config.py`:
```python
# Scraping limits
MAX_PAGES = 1
LISTINGS_PER_PAGE = 48
TOTAL_LISTINGS_LIMIT = 48

# Search filters
LOCATION = "providencia-metropolitana"
MIN_PRICE_CLP = 0
MAX_PRICE_CLP = 1200000
MIN_BEDROOMS = 2
ONLY_USED = True
```

## Output

The script creates a `scraped-data` directory containing:
- `properties_[timestamp].json`: Raw data in JSON format
- `properties_[timestamp].html`: Formatted HTML report

## Rate Limiting and Error Handling

The scraper includes:
- Random delays between requests
- User agent rotation
- Automatic retry mechanism for rate-limited requests
- Graceful error handling for missing data

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Disclaimer

This tool is for educational purposes only. Make sure to review and comply with Portal Inmobiliario's terms of service before use. The developers are not responsible for any misuse of this tool or violation of Portal Inmobiliario's terms of service.
