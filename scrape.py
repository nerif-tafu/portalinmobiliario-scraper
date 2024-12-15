import os
os.system('')  # Enable ANSI escape sequences in Windows

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException, NoSuchElementException
import time
import json
import requests
import re
import random
import os
import datetime
import webbrowser
from config import (
    MAX_PAGES_PER_LOCATION,
    LISTINGS_PER_PAGE,
    LISTINGS_PER_LOCATION,
    LOCATIONS,
    get_url_for_location
)

# At the top of the file, add these color constants
ORANGE = '\033[93m'
RESET = '\033[0m'

def get_uf_value():
    try:
        response = requests.get("https://mindicador.cl/api")
        data = response.json()
        return data['uf']['valor']
    except Exception as e:
        print(f"Error fetching UF value: {e}")
        return None

def wait_for_page_load(driver):
    try:
        WebDriverWait(driver, 10).until(
            lambda driver: driver.execute_script('return document.readyState') == 'complete'
        )
    except TimeoutException:
        print("Page load timeout")

def get_element_safely(driver, element, by, selector):
    """Safely get an element with retries for stale elements"""
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            if element:
                return element.find_element(by, selector)
            return driver.find_element(by, selector)
        except StaleElementReferenceException:
            if attempt == max_attempts - 1:
                raise
            continue

def get_elements_safely(driver, element, by, selector):
    """Safely get elements with retries for stale elements"""
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            if element:
                return element.find_elements(by, selector)
            return driver.find_elements(by, selector)
        except StaleElementReferenceException:
            if attempt == max_attempts - 1:
                raise
            continue

def convert_price_to_clp(price_element):
    try:
        # Get the currency symbol and amount
        currency_symbol = price_element.find_element(By.CSS_SELECTOR, ".andes-money-amount__currency-symbol").text
        amount = price_element.find_element(By.CSS_SELECTOR, ".andes-money-amount__fraction").text
        
        # Remove dots and convert to float
        amount = float(amount.replace('.', '').replace(',', '.'))
        
        if currency_symbol == 'UF':
            uf_value = get_uf_value()
            if uf_value:
                return int(amount * uf_value)
            else:
                return None
        elif currency_symbol == '$':
            # If it's already in CLP, just return the amount
            return int(amount)
        else:
            print(f"Unknown currency symbol: {currency_symbol}")
            return None
    except Exception as e:
        print(f"Error converting price: {e}")
        return None

def extract_listing_details(driver, url, price):
    """Extract detailed information from a listing page"""
    try:
        currently_rate_limited = True
        attempts = 0
        max_attempts = 3

        while currently_rate_limited and attempts < max_attempts:       
            try:
                # Random delay between 1 and 3 seconds
                time.sleep(random.uniform(1, 3))
                
                # Clear browser state
                driver.delete_all_cookies()
                driver.execute_script("window.localStorage.clear();")
                driver.execute_script("window.sessionStorage.clear();")
                
                # Set new random user agent
                driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                    "userAgent": get_random_user_agent()
                })
                
                # Load the page
                clean_base_url = clean_url(url)
                random_param = f"?t={int(time.time())}&r={random.random()}"
                print("Getting", clean_base_url + random_param)
                driver.get(clean_base_url + random_param)
                
                # Wait for main container
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "#ui-pdp-main-container"))
                )
                
                # Perform random interactions
                perform_random_interactions(driver)
                
                currently_rate_limited = False
                
            except TimeoutException:
                attempts += 1
                wait_time = min(300, (2 ** attempts) * 60 + random.uniform(1, 30))
                print(f"Rate limited, attempt {attempts}/{max_attempts}, waiting {int(wait_time)} seconds")
                time.sleep(wait_time)
        
        if currently_rate_limited:
            return None

        # Initialize details with empty values
        details = {
            'images': [],
            'full_address': None,
            'google_maps_link': None,
            'metro_station': None,
            'common_costs': None,
            'has_gym': False,
            'floor': None,
            'total_floors': None,
            'furnished': None,
            'total_area': None,
            'apartment_type': None,
            'total_price': None,
            'description': None
        }

        # Get all images
        try:
            images = driver.find_elements(By.CSS_SELECTOR, ".ui-pdp-image.ui-pdp-gallery__figure__image")
            details['images'] = [img.get_attribute('src') for img in images if img.get_attribute('src')]
        except Exception as e:
            print(f"Error getting images: {e}")

        # Get specifications from the tables
        try:
            # First attempt to find tables
            tables_found = False
            refresh_attempts = 0
            max_refresh_attempts = 3

            while not tables_found and refresh_attempts < max_refresh_attempts:
                try:
                    driver.refresh()
                    time.sleep(random.uniform(2, 4))
                    
                    # Add random interactions after refresh
                    perform_random_interactions(driver)
                    
                    # Wait for tables to be present
                    tables = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".andes-table__body"))
                    )
                    
                    rows = driver.find_elements(By.CSS_SELECTOR, ".andes-table__row")
                    if len(rows) > 0:
                        tables_found = True
                    else:
                        print(f"Tables found but no rows present. Attempt {refresh_attempts + 1}/{max_refresh_attempts}")
                        driver.refresh()
                        time.sleep(random.uniform(2, 4))
                        refresh_attempts += 1
                except TimeoutException:
                    print(f"Tables not found. Attempting refresh. Attempt {refresh_attempts + 1}/{max_refresh_attempts}")
                    driver.refresh()
                    time.sleep(random.uniform(2, 4))
                    refresh_attempts += 1

            if not tables_found:
                print(f"{ORANGE}Warning: Failed to load tables after all refresh attempts{RESET}")
                return None

            # Process the tables as before
            for row in rows:
                try:
                    header = row.find_element(By.CSS_SELECTOR, ".andes-table__header__container").get_attribute("innerHTML")
                    value = row.find_element(By.CSS_SELECTOR, ".andes-table__column--value").get_attribute("innerHTML")

                    mapping = {
                        'Superficie total': ('total_area', value.replace("m²", "")),
                        'Número de piso de la unidad': ('floor', value),
                        'Cantidad de pisos': ('total_floors', value),
                        'Tipo de departamento': ('apartment_type', value),
                        'Amoblado': ('furnished', value == 'Sí'),
                        'Gimnasio': ('has_gym', value == 'Sí'),
                        'Dormitorios': ('bedrooms', value),
                        'Baños': ('bathrooms', value),
                        'Estacionamientos': ('parking_spots', value),
                        'Bodegas': ('storage_units', value),
                    }
                    
                    if header in mapping:
                        key, val = mapping[header]
                        if val is None or val == "":
                            print(f"{ORANGE}Warning: Skipping empty value for {key}{RESET}")
                        details[key] = val

                except Exception as e:
                    print(f"{ORANGE}Warning: Error processing row: {str(e)}{RESET}")
                    continue

        except Exception as e:
            print(f"Error getting specifications: {str(e)}")
            time.sleep(1000)

        try:
            metro_station = driver.find_element(By.CSS_SELECTOR, ".andes-tab-content.ui-vip-poi__tab-content")
            metro_station_holder = metro_station.find_element(By.XPATH, ".//*[text()='Estaciones de metro']")
            if metro_station_holder is None:
                print("No metro station found")
                return details
            metro_station_holder_parent = metro_station_holder.find_element(By.XPATH, "./..")
            metro_station_list = metro_station_holder_parent.find_elements(By.CSS_SELECTOR, ".ui-vip-poi__item")

            for station in metro_station_list:
                metro_station_name = station.find_element(By.CSS_SELECTOR, ".ui-pdp-color--BLACK.ui-pdp-size--XSMALL.ui-pdp-family--REGULAR")
                metro_station_distance = station.find_element(By.CSS_SELECTOR, ".ui-pdp-color--GRAY.ui-pdp-size--XSMALL.ui-pdp-family--REGULAR")
            
            # Format the metro station name and distance into [{'name': 'Santa Isabel', 'walking_minutes': 8, 'distance_meters': 638}]
            details['metro_station'] = [{'name': metro_station_name.text, 'walking_minutes': metro_station_distance.text.split(' ')[0], 'distance_meters': metro_station_distance.text.split(' ')[1]} for station in metro_station_list]
            print("Found metro station", details['metro_station'])

        except NoSuchElementException:
            print(f"No metro stations found.")

        except Exception as e:
            print(f"Error getting metro station: {str(e)}")

        # Get common costs from div
        try:
            common_costs = driver.find_element(By.CSS_SELECTOR, ".ui-pdp-color--GRAY.ui-pdp-size--XSMALL.ui-pdp-family--REGULAR.ui-pdp-maintenance-fee-ltr")
            common_costs_text = common_costs.text.strip()
            common_costs_text = common_costs_text.replace("Gastos comunes aproximados $", "")
            common_costs_text = common_costs_text.replace(".", "")
            common_costs_text = common_costs_text.replace(",", ".")
            common_costs_text = common_costs_text.strip()

            details['common_costs'] = int(common_costs_text)
            print("Found common costs", details['common_costs'])

        except Exception as e:
            print(f"Error getting common costs: {str(e)}")


        # Get description
        try:
            description = driver.find_element(By.CSS_SELECTOR, ".ui-pdp-description__content").text.strip()
            details['description'] = description
        except Exception as e:
            print(f"Error getting description: {str(e)}")


        # Get address information
        try:
            location_container = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".ui-pdp-media.ui-vip-location__subtitle.ui-pdp-color--BLACK"))
            )
            address = location_container.find_element(By.CSS_SELECTOR, "p").text.strip()
            
            # Click on the map image to load it
            map_element = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "#ui-vip-location__map > div > img"))
            )
                        
            driver.execute_script("arguments[0].click();", map_element)
            
            # Wait for the Google Maps link to appear after map loads
            maps_link = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((
                    By.CSS_SELECTOR, 
                    'a[title="Open this area in Google Maps (opens a new window)"]'
                ))
            ).get_attribute('href')
            
            details['full_address'] = address
            details['google_maps_link'] = maps_link
            print(f"Found address: {address}")
            print(f"Found maps link: {maps_link}")
        except Exception as e:
            print(f"Error getting address: {str(e)}")
            details['full_address'] = None
            details['google_maps_link'] = None

        print("Calculating total price", price, details['common_costs'])
        if price is not None:
            details['total_price'] = price + (details['common_costs'] if details['common_costs'] is not None else 0)
        else:
            details['total_price'] = None

        # Before returning
        missing_fields = [k for k, v in details.items() if v is None]
        if missing_fields:
            print(f"{ORANGE}Warning: Missing fields in final details: {', '.join(missing_fields)}{RESET}")

        return details
    
    except Exception as e:
        print(f"{ORANGE}Warning: Error processing listing: {str(e)}{RESET}")
        return None

def scrape_properties():
    """
    Scrape property listings using configuration settings
    """
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument(f"--user-agent={get_random_user_agent()}")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=chrome_options
    )

    driver.maximize_window()

    all_properties = []

    try:
        for location in LOCATIONS:
            print(f"\nScraping location: {location}")
            current_offset = 0
            location_properties_count = 0

            for page in range(MAX_PAGES_PER_LOCATION):
                if location_properties_count >= LISTINGS_PER_LOCATION:
                    print(f"\nReached listings limit of {LISTINGS_PER_LOCATION} for {location}")
                    break

                url = get_url_for_location(location, current_offset)
                print(f"\nScraping page {page + 1} (offset: {current_offset})")
                
                # Store the links and titles first
                listing_data = []
                
                driver.get(url)
                wait_for_page_load(driver)

                try:
                    # Wait for listings container
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "ol.ui-search-layout"))
                    )
                    
                    # Get all listing elements
                    listings = WebDriverWait(driver, 10).until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "li.ui-search-layout__item"))
                    )

                    if not listings:
                        print("No listings found on this page. Stopping.")
                        break

                    if LISTINGS_PER_PAGE:
                        listings = listings[:LISTINGS_PER_PAGE]

                    print(f"Found {len(listings)} listings on page {page + 1}")

                    # First pass: collect all the necessary data from the listing preview
                    for listing in listings:
                        try:
                            title = WebDriverWait(listing, 10).until(
                                EC.presence_of_element_located((By.CSS_SELECTOR, ".ui-search-item__title-label-grid"))
                            ).text
                            
                            price_element = WebDriverWait(listing, 10).until(
                                EC.presence_of_element_located((By.CSS_SELECTOR, ".andes-money-amount"))
                            )
                            
                            link = WebDriverWait(listing, 10).until(
                                EC.presence_of_element_located((By.CSS_SELECTOR, "a.ui-search-link"))
                            ).get_attribute("href")
                            link = clean_url(link)
                            
                            price = convert_price_to_clp(price_element)
                            
                            listing_data.append({
                                "title": title,
                                "price": price,
                                "link": link
                            })
                            
                        except Exception as e:
                            print(f"Error collecting listing preview data: {str(e)}")
                            continue

                    # Second pass: visit each listing page
                    for data in listing_data:
                        if location_properties_count >= LISTINGS_PER_LOCATION:
                            break
                            
                        try:
                            # Get detailed info from listing page
                            listing_details = extract_listing_details(driver, data["link"], data["price"])

                            if listing_details:
                                combined_property = {
                                    **data,
                                    "location": location,
                                    **listing_details
                                }
                                all_properties.append(combined_property)
                                location_properties_count += 1
                                print(f"Successfully processed listing: {data['title']} ({location_properties_count}/{LISTINGS_PER_LOCATION} for {location})")

                        except Exception as e:
                            print(f"Error processing listing details: {str(e)}")
                            continue

                    current_offset += LISTINGS_PER_PAGE

                except TimeoutException:
                    print(f"Timeout waiting for listings on page {page + 1}")
                    continue

            print(f"Completed scraping {location}: {location_properties_count} properties found")

        return all_properties

    finally:
        driver.quit()

# Update the HTML generation to include new fields
def generate_html(properties):
    html = """
    <html>
    <head>
        <title>Property Listings</title>
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .property { border: 1px solid #ccc; padding: 15px; margin-bottom: 20px; }
            .price { font-size: 1.2em; font-weight: bold; color: #2c5282; }
            .details { margin: 10px 0; }
            .images { display: flex; gap: 10px; overflow-x: auto; margin: 10px 0; }
            .images img { max-width: 200px; height: auto; }
            .maps-container { display: flex; gap: 10px; margin: 10px 0; height: 300px; }
            .map { flex: 1; }
            .attributes { margin: 10px 0; color: #666; }
            .links { margin-top: 10px; }
            .links a { display: inline-block; margin-right: 10px; color: #2c5282; text-decoration: none; }
            .links a:hover { text-decoration: underline; }
        </style>
    </head>
    <body>
        <h1>Property Listings</h1>
    """

    # Santiago center coordinates
    santiago_center = [-33.4489, -70.6693]

    for idx, prop in enumerate(properties):
        # Extract coordinates from Google Maps link
        coords = None
        if prop.get('google_maps_link'):
            match = re.search(r'@(-?\d+\.\d+),(-?\d+\.\d+)', prop['google_maps_link'])
            if match:
                coords = [float(match.group(1)), float(match.group(2))]

        html += f"""
        <div class="property">
            <h2>{prop['title']}</h2>
            <div class="price">${'{:,.0f}'.format(prop['total_price'] if prop['total_price'] is not None else 0)}</div>
            <div class="images">
                {''.join(f'<img src="{img}" alt="Property Image">' for img in prop['images'])}
            </div>
        """

        if coords:
            html += f"""
            <div class="maps-container">
                <div id="propertyMap{idx}" class="map"></div>
                <div id="contextMap{idx}" class="map"></div>
            </div>
            <script>
                // Property location map
                var propertyMap{idx} = L.map('propertyMap{idx}').setView({coords}, 15);
                L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
                    attribution: '© OpenStreetMap contributors'
                }}).addTo(propertyMap{idx});
                L.marker({coords}).addTo(propertyMap{idx});

                // Context map
                var contextMap{idx} = L.map('contextMap{idx}').setView({santiago_center}, 11);
                L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
                    attribution: '© OpenStreetMap contributors'
                }}).addTo(contextMap{idx});
                L.marker({coords}).addTo(contextMap{idx});
            </script>
            """

        html += f"""
            <div class="attributes">
                <p><strong>Location:</strong> {prop.get('location', 'N/A')}</p>
                <p><strong>Address:</strong> {prop.get('full_address', 'N/A')}</p>
                <p><strong>Metro Stations:</strong></p>
                {'<ul>' + ''.join(f'<li>{station["name"]} - {station["walking_minutes"]} mins - {station["distance_meters"]} meters</li>' for station in prop.get('metro_station', [])) + '</ul>' if prop.get('metro_station') else '<p>No metro stations nearby</p>'}
                <p><strong>Rent:</strong> {prop.get('price', 'N/A')}</p>
                <p><strong>Common Costs:</strong> {prop.get('common_costs', 'N/A')}</p>
                <p><strong>Gym:</strong> {'Yes' if prop.get('has_gym') else 'No'}</p>
                <p><strong>Floor:</strong> {prop.get('floor', 'N/A')}</p>
                <p><strong>Total Floors:</strong> {prop.get('total_floors', 'N/A')}</p>
                <p><strong>Furnished:</strong> {prop.get('furnished', 'N/A')}</p>
                <p><strong>Total Area:</strong> {prop.get('total_area', 'N/A')}</p>
                <p><strong>Apartment Type:</strong> {prop.get('apartment_type', 'N/A')}</p>
            </div>
            <div class="links">
                <a href="{prop['link']}" target="_blank">View Property</a>
                {f'<a href="{prop.get("google_maps_link")}" target="_blank">View Maps</a>' if prop.get('google_maps_link') else ''}
            </div>
        </div>
        """

    html += """
    </body>
    </html>
    """

    return html

def clean_url(url):
    """Remove tracking and unnecessary query parameters from URLs"""
    # Remove everything after the '#' symbol first
    base_url = url.split('#')[0]
    
    # Then remove everything after the '?' symbol
    base_url = base_url.split('?')[0]
    
    # Remove any tracking_id parameters that might be in the path
    base_url = re.sub(r'/\?tracking_id=[^/]*', '', base_url)
    
    # Remove t and r query parameters if they exist
    base_url = re.sub(r'\?t=\d+&r=[\d.]+', '', base_url)
    
    return base_url

def get_random_user_agent():
    """Generate a random Chrome-based user agent"""
    chrome_versions = [
        '90.0.4430.212',
        '91.0.4472.124',
        '92.0.4515.159',
        '93.0.4577.82',
        '94.0.4606.81',
        '95.0.4638.69',
        '96.0.4664.45',
        '97.0.4692.71',
        '98.0.4758.102',
        '99.0.4844.51'
    ]
    
    os_versions = [
        'Windows NT 10.0; Win64; x64',
        'Windows NT 10.0; WOW64',
        'Macintosh; Intel Mac OS X 10_15_7',
        'X11; Linux x86_64',
        'X11; Ubuntu; Linux x86_64'
    ]
    
    chrome_version = random.choice(chrome_versions)
    os_version = random.choice(os_versions)
    
    return f'Mozilla/5.0 ({os_version}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_version} Safari/537.36'

def perform_random_interactions(driver):
    """Simulate random human-like interactions on the page"""
    try:
        # List of possible interactions
        interactions = [
            # Scroll to different positions
            lambda: driver.execute_script(f"window.scrollTo(0, {random.randint(100, 700)});"),
            lambda: driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);"),
            lambda: driver.execute_script("window.scrollTo(0, document.body.scrollHeight);"),
            
            # Move mouse to safe elements
            lambda: driver.execute_script("""
                let elements = document.querySelectorAll('textarea, .ui-pdp-color--BLACK.ui-pdp-size--XSMALL.ui-pdp-family--REGULAR');
                let randElement = elements[Math.floor(Math.random() * elements.length)];
                if(randElement) {
                    randElement.scrollIntoView({behavior: 'smooth', block: 'center'});
                }
            """),
            
            # Simulate mouse movements
            lambda: driver.execute_script("""
                let event = new MouseEvent('mousemove', {
                    'view': window,
                    'bubbles': true,
                    'cancelable': true,
                    'clientX': Math.random() * window.innerWidth,
                    'clientY': Math.random() * window.innerHeight
                });
                document.dispatchEvent(event);
            """)
        ]
        
        # Perform 2-4 random interactions
        for _ in range(random.randint(2, 4)):
            random.choice(interactions)()
            time.sleep(random.uniform(0.5, 2))
            
    except Exception as e:
        print(f"Error during random interactions: {e}")

if __name__ == "__main__":
    # Create the scraped-data directory if it doesn't exist
    os.makedirs('scraped-data', exist_ok=True)
    
    # Generate timestamp for filename
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Get properties using configuration settings
    properties = scrape_properties()
    
    # Save results to JSON file with timestamp
    json_filename = f'scraped-data/properties_{timestamp}.json'
    with open(json_filename, 'w', encoding='utf-8') as f:
        json.dump(properties, f, ensure_ascii=False, indent=2)
    
    # Generate and save HTML with timestamp
    html_filename = f'scraped-data/properties_{timestamp}.html'
    html_content = generate_html(properties)
    with open(html_filename, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"\nScraped {len(properties)} total properties")
    print(f"Saved to {json_filename}")
    print(f"HTML saved to {html_filename}")
    
    # Open the HTML file in the default browser
    webbrowser.open(html_filename)
