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
from scraper.config import (
    LOCATIONS,
    get_url_for_location
)
from urllib.parse import urlencode, urlparse, parse_qs
from scraper.database import (
    save_property, 
    save_single_property, 
    get_db_session, 
    is_duplicate_listing,
    Session  # Add this import
)
from web.models import db, Run  # Add this import
from web.app import app  # Import the Flask app
from datetime import timedelta
from scraper.utils import setup_logger, log_and_print  # Changed this line
from web.utils import convert_to_embed_src  # Update import

# At the top of the file, add these color constants
ORANGE = '\033[93m'
RESET = '\033[0m'

LISTINGS_PER_PAGE = 48

# At the start of the file
logger = setup_logger()

def get_uf_value():
    try:
        response = requests.get("https://mindicador.cl/api")
        data = response.json()
        return data['uf']['valor']
    except Exception as e:
        log_and_print(f"Error fetching UF value: {e}", level='error')
        return None

def wait_for_page_load(driver):
    try:
        WebDriverWait(driver, 10).until(
            lambda driver: driver.execute_script('return document.readyState') == 'complete'
        )
    except TimeoutException:
        log_and_print("Page load timeout", level='warning')

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
            log_and_print(f"Unknown currency symbol: {currency_symbol}", level='warning')
            return None
    except Exception as e:
        log_and_print(f"Error converting price: {e}", level='error')
        return None

def extract_listing_details(url, price):
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-software-rasterizer")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument(f"--user-agent={get_random_user_agent()}")
    chrome_options.binary_location = "/usr/bin/chromium"

    max_retries = 3
    retry_count = 0

    while retry_count < max_retries:
        try:
            driver = webdriver.Chrome(options=chrome_options)
            """Extract detailed information from a listing page"""
            try:
                currently_rate_limited = True
                attempts = 0
                max_attempts = 3

                while currently_rate_limited and attempts < max_attempts:       
                    try:
                        # Random delay between 1 and 3 seconds
                        time.sleep(random.uniform(1, 3))
                        
                        # Clear browser state safely
                        driver.delete_all_cookies()
                        try:
                            driver.execute_script("window.localStorage.clear();")
                            driver.execute_script("window.sessionStorage.clear();")
                        except Exception:
                            # Ignore localStorage/sessionStorage errors
                            pass
                        
                        # Set new random user agent
                        driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                            "userAgent": get_random_user_agent()
                        })
                        
                        # Load the page with clean URL
                        clean_base_url = clean_url(url)
                        log_and_print(f"Getting {clean_base_url}")
                        driver.get(clean_base_url)
                        
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
                        log_and_print(f"Rate limited, attempt {attempts}/{max_attempts}, waiting {int(wait_time)} seconds")
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
                    log_and_print(f"Error getting images: {e}", level='error')

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
                                log_and_print(f"Tables found but no rows present. Attempt {refresh_attempts + 1}/{max_refresh_attempts}")
                                driver.refresh()
                                time.sleep(random.uniform(2, 4))
                                refresh_attempts += 1
                        except TimeoutException:
                            log_and_print(f"Tables not found. Attempting refresh. Attempt {refresh_attempts + 1}/{max_refresh_attempts}")
                            driver.refresh()
                            time.sleep(random.uniform(2, 4))
                            refresh_attempts += 1

                    if not tables_found:
                        log_and_print(f"{ORANGE}Warning: Failed to load tables after all refresh attempts{RESET}", level='warning')
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
                                    log_and_print(f"{ORANGE}Warning: Skipping empty value for {key}{RESET}", level='warning')
                                details[key] = val

                        except Exception as e:
                            log_and_print(f"{ORANGE}Warning: Error processing row: {str(e)}{RESET}", level='warning')
                            continue

                except Exception as e:
                    log_and_print(f"Error getting specifications: {str(e)}", level='error')
                    time.sleep(10)

                try:
                    metro_station = driver.find_element(By.CSS_SELECTOR, ".andes-tab-content.ui-vip-poi__tab-content")
                    metro_station_holder = metro_station.find_element(By.XPATH, ".//*[text()='Estaciones de metro']")
                    if metro_station_holder is None:
                        log_and_print("No metro station found")
                        return details
                    metro_station_holder_parent = metro_station_holder.find_element(By.XPATH, "./..")
                    metro_station_list = metro_station_holder_parent.find_elements(By.CSS_SELECTOR, ".ui-vip-poi__item")

                    all_metro_stations = []

                    for station in metro_station_list:
                        metro_station_name = station.find_element(By.CSS_SELECTOR, ".ui-pdp-color--BLACK.ui-pdp-size--XSMALL.ui-pdp-family--REGULAR")
                        metro_station_distance = station.find_element(By.CSS_SELECTOR, ".ui-pdp-color--GRAY.ui-pdp-size--XSMALL.ui-pdp-family--REGULAR")
                        
                        # Parse Spanish format: "10 mins - 751 metros" or "12 mins - 1.523 metros"
                        distance_text = metro_station_distance.text
                        parts = distance_text.split(' - ')  # Split by the dash
                        walking_minutes = parts[0].split(' ')[0]  # Get "10" from "10 mins"
                        distance_meters = parts[1].split(' ')[0].replace('.', '')  # Get "1523" from "1.523"
                        
                        all_metro_stations.append({
                            'name': metro_station_name.text,
                            'walking_minutes': walking_minutes,
                            'distance_meters': distance_meters
                        })
                    details['metro_station'] = all_metro_stations
                    log_and_print(f"Found metro station {details['metro_station']}")

                except NoSuchElementException:
                    log_and_print("No metro stations found.")

                except Exception as e:
                    log_and_print(f"Error getting metro station: {str(e)}", 
                                  level='error', 
                                  color=ORANGE)

                # Get common costs from div
                try:
                    common_costs = driver.find_element(By.CSS_SELECTOR, ".ui-pdp-color--GRAY.ui-pdp-size--XSMALL.ui-pdp-family--REGULAR.ui-pdp-maintenance-fee-ltr")
                    common_costs_text = common_costs.text.strip()
                    common_costs_text = common_costs_text.replace("Gastos comunes aproximados $", "")
                    common_costs_text = common_costs_text.replace("Gastos comunes desde $", "")
                    common_costs_text = common_costs_text.replace(".", "")
                    common_costs_text = common_costs_text.replace(",", ".")
                    common_costs_text = common_costs_text.strip()

                    details['common_costs'] = int(common_costs_text)
                    log_and_print("Found common costs", details['common_costs'])

                except NoSuchElementException:
                    log_and_print("No common costs found")

                except Exception as e:
                    log_and_print(f"Error getting common costs: {str(e)}", level='error')


                # Get description
                try:
                    description = driver.find_element(By.CSS_SELECTOR, ".ui-pdp-description__content").text.strip()
                    details['description'] = description
                except Exception as e:
                    log_and_print(f"Error getting description: {str(e)}", level='error')


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
                    log_and_print(f"Found address: {address}")
                    log_and_print(f"Found maps link: {maps_link}")
                except Exception as e:
                    log_and_print(f"Error getting address: {str(e)}", level='error')
                    details['full_address'] = None
                    details['google_maps_link'] = None

                log_and_print("Calculating total price", price, details['common_costs'])
                if price is not None:
                    details['total_price'] = price + (details['common_costs'] if details['common_costs'] is not None else 0)
                else:
                    details['total_price'] = None

                # Before returning
                missing_fields = [k for k, v in details.items() if v is None]
                if missing_fields:
                    log_and_print(f"Warning: Missing fields in final details: {', '.join(missing_fields)}", 
                                  level='warning', 
                                  color=ORANGE)

                return details
            
            except Exception as e:
                log_and_print(f"{ORANGE}Warning: Error processing listing: {str(e)}{RESET}", level='warning')
                return None
        except Exception as e:
            retry_count += 1
            log_and_print(f"Attempt {retry_count}/{max_retries} failed: {str(e)}", level='warning')
            try:
                driver.quit()
            except:
                pass
            if retry_count == max_retries:
                raise
            time.sleep(random.uniform(5, 10))

def scrape_links_from_location():
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument(f"--user-agent={get_random_user_agent()}")
    chrome_options.binary_location = "/usr/bin/chromium"

    timeout_reattempt = 0;

    driver = webdriver.Chrome(options=chrome_options)
    session = get_db_session()

    try:
        all_properties = []
        
        for location in LOCATIONS:
            log_and_print(f"\nScraping location: {location}")
            

            page = 0
            still_scraping_properties = True
            
            while still_scraping_properties:

                url = get_url_for_location(location, page * LISTINGS_PER_PAGE)
                log_and_print(f"\nScraping page {page + 1} (offset: {page * LISTINGS_PER_PAGE})")
                log_and_print(f"{url}")
                
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
                        log_and_print("No listings found on this page. Stopping.", level='warning')
                        still_scraping_properties = False
                        continue
                    else:
                        log_and_print(f"Found {len(listings)} listings on page {page + 1}")

                    if LISTINGS_PER_PAGE:
                        listings = listings[:LISTINGS_PER_PAGE]

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
                            
                            all_properties.append({
                                "title": title,
                                "price": price,
                                "link": link
                            })

                            timeout_reattempt = 0;
                            
                        except Exception as e:
                            log_and_print(f"Error collecting listing preview data: {str(e)}", level='error')
                            continue

                except TimeoutException:
                    log_and_print(f"Timeout waiting for listings on page {page + 1}", level='warning')

                    # Check if we are just at the end of the listing page.
                    # Check if we have an elemet with the innerHTML of En esta categoría no hay inmuebles que coincidan con tu búsqueda.

                    try:
                        # Check for "no results" message
                        no_results = driver.find_element(By.CSS_SELECTOR, ".ui-search-rescue__title")
                        if no_results and "no hay inmuebles que coincidan con tu búsqueda" in no_results.text.lower():
                            log_and_print(f"No more listings found on page {page + 1}", level='warning')
                            still_scraping_properties = False
                            continue
                    except NoSuchElementException:
                        log_and_print(f"No 'no results' message found on page {page + 1}", level='warning')
                        # Check if we are getting rate limited

                        timeout_reattempt += 1
                        wait_time = min(300, (2 ** timeout_reattempt) * 60 + random.uniform(1, 30))
                        log_and_print(f"Rate limited, attempt {timeout_reattempt}/{3}, waiting {int(wait_time)} seconds")
                        time.sleep(wait_time)
                        pass

                    continue
                page += 1

        return all_properties

        

    finally:
        Session.remove()  # Use Session.remove() instead of session.remove()
        driver.quit()

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
        log_and_print(f"Error during random interactions: {e}", level='error')

if __name__ == "__main__":
    from scraper.database import save_property
    import time
    
    SCRAPE_INTERVAL = int(os.getenv('SCRAPE_INTERVAL', 3600))  # Default to 1 hour if not set
    log_and_print(f"Starting scraper with {SCRAPE_INTERVAL} seconds interval")
    
    while True:
        try:
            log_and_print(f"\nStarting new scraping run at {datetime.datetime.now()}")
            
            # Use Flask app context
            with app.app_context():
                # Create a new run with 'running' status
                run = Run(
                    started_at=datetime.datetime.utcnow(),
                    status='running'
                )
                db.session.add(run)
                db.session.commit()
                
                try:
                    # Get properties using configuration settings
                    property_links = scrape_links_from_location()
                    session = get_db_session()  # Get a new session

                    if not property_links:
                        log_and_print("No properties were scraped!", level='warning')
                        run.status = 'completed'
                        run.total_properties = 0
                    else:
                        log_and_print(f"Scraped {len(property_links)} properties")

                    for data in property_links:
                        if is_duplicate_listing(session, data["link"]):
                            log_and_print(f"Skipping duplicate listing: {data['title']}")
                            continue

                        log_and_print(f"Extracting details for {data['title']}")
                        listing_details = extract_listing_details(data["link"], data["price"])
                    
                        if listing_details:
                            combined_property = {
                                **data,
                                **listing_details
                            }
                            save_property(combined_property, run.id)

                    try:
                        run.status = 'completed'
                        run.total_properties = 123
                        log_and_print(f"\nSuccessfully scraped and saved {123} total properties")
                    except Exception as e:
                        log_and_print(f"Error saving to database: {str(e)}", level='error')
                        run.status = 'failed'
                        run.error_message = f"Database error: {str(e)}"

                    # Update run completion time and next run time
                    run.completed_at = datetime.datetime.utcnow()
                    run.next_run_at = run.completed_at + timedelta(seconds=SCRAPE_INTERVAL)
                    db.session.commit()

                except Exception as e:
                    log_and_print(f"Error during scraping: {str(e)}", level='error')
                    run.status = 'failed'
                    run.error_message = f"Scraping error: {str(e)}"
            
        except Exception as e:
            log_and_print(f"Critical error: {str(e)}", level='error')
