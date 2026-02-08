import time
from django.conf import settings

def cache_busting(request):
    """Add cache busting version to templates"""
    return {
        'cache_version': str(int(time.time())) if settings.DEBUG else '1.0'
    }