from urllib.parse import urlencode, urlparse, parse_qs

def convert_to_embed_src(url):
    """Convert Google Maps URL to embed URL"""
    if not url:
        return None
        
    try:
        # Parse the input URL
        parsed_url = urlparse(url)
        
        # Try to get coordinates from query parameters
        query_params = parse_qs(parsed_url.query)
        if 'll' in query_params:
            coords = query_params['ll'][0]
            return f"https://www.google.com/maps?q={coords}&z=12&output=embed"
            
        # Fallback to path parsing if needed
        path_parts = parsed_url.path.split('@')
        if len(path_parts) > 1:
            coords = ','.join(path_parts[1].split(',')[:2])  # Just get lat,lng
            return f"https://www.google.com/maps?q={coords}&z=12&output=embed"
            
        return None
        
    except Exception as e:
        print(f"Error converting map URL: {str(e)}")
        return None 