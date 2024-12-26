from urllib.parse import urlencode, urlparse, parse_qs

def convert_to_embed_src(url):
    """Convert Google Maps URL to embed URL"""
    if not url:
        return None
    
    # Simple replacement to convert to embed URL
    return url.replace('maps/place/', 'maps/embed/place/') 