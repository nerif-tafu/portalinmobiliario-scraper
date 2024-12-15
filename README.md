# Property Scraper

A web scraping system that collects rental property listings from Portal Inmobiliario. Built with Python, Flask, PostgreSQL, and Docker.

## Features

- Scrapes rental properties from multiple locations:
  - Providencia
  - Ñuñoa
  - Las Condes
  - Vitacura
- Stores detailed property information:
  - Price and common costs
  - Area and floor details
  - Metro station proximity with walking times
  - Google Maps location
  - Property images
- Web interface for viewing and managing scraped data
- Property preference tracking (like/dislike)
- Automated scraping at configurable intervals

## Tech Stack

### Backend
- Python 3.11
- Flask & SQLAlchemy
- PostgreSQL
- Selenium with Chromium

### Frontend
- HTML/CSS
- JavaScript
- Bootstrap

### Infrastructure
- Docker & Docker Compose

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/property-scraper.git
cd property-scraper
```

2. Start the services:
```bash
docker-compose up --build
```

## Configuration

### Docker Environment Variables (docker-compose.yml)
```yaml
# Database settings
POSTGRES_DB: property_scraper
POSTGRES_USER: scraper
POSTGRES_PASSWORD: scraper_password

# Scraper settings
SCRAPE_INTERVAL: 60              # Seconds between scrapes
MAX_PAGES_PER_LOCATION: -1       # Number of pages to scrape (-1 for all)
```

### Scraper Configuration (scraper/config.py)
```python
LOCATIONS = [
    "providencia-metropolitana",
    "nunoa-metropolitana",
    "las-condes-metropolitana",
    "vitacura-metropolitana"
]
```

## Usage

### Web Interface
- Main dashboard: `http://localhost:3000`
- View specific run: `http://localhost:3000/?run_id=<run_id>`
- Check scraper status: `http://localhost:3000/status`

### Database Management
```bash
# Connect to database
docker-compose exec db psql -U scraper -d property_scraper

# Apply migrations manually if needed
docker-compose exec db psql -U scraper -d property_scraper -f /docker-entrypoint-initdb.d/init.sql
```

### Maintenance
```bash
# View logs
docker-compose logs -f scraper

# Restart services
docker-compose restart

# Clean up and rebuild
docker-compose down -v
docker system prune -a --volumes
docker-compose up --build
```

## Project Structure
```
.
├── docker/                 # Docker configuration
│   ├── scraper/           # Scraper service
│   └── web/               # Web service
├── migrations/            # Database migrations
├── scraper/              # Scraper code
│   ├── config.py         # Scraping configuration
│   ├── database.py       # Database operations
│   └── scraper.py        # Main scraping logic
├── web/                  # Web application
│   ├── templates/        # HTML templates
│   ├── app.py           # Flask application
│   └── models.py        # Database models
└── docker-compose.yml    # Service orchestration
```

## Database Schema

### Tables
- `runs`: Scraping run metadata and status
- `properties`: Property listings and details
- `property_images`: Property image URLs
- `metro_stations`: Nearby metro stations with walking times
- `property_preferences`: User property preferences (liked/disliked)

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
