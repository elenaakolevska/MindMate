class NoCacheMiddleware:
    """
    Middleware to add no-cache headers for HTML pages in development
    This helps prevent Chrome caching issues
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Add no-cache headers for HTML pages when in debug mode
        if hasattr(response, 'content') and response.get('Content-Type', '').startswith('text/html'):
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
        
        return response