"""
Snowplow tracking middleware for automatic page view tracking.
Implements the middleware pattern with performance optimization.
"""

import logging
from django.utils.deprecation import MiddlewareMixin
from django.urls import resolve
from myapp.services.snowplow_services import snowplow_tracker

logger = logging.getLogger(__name__)


class SnowplowTrackingMiddleware(MiddlewareMixin):
    """
    Middleware to automatically track page views and user sessions.
    Implements performance-optimized tracking with configurable exclusions.
    """

    # URLs to exclude from tracking (API endpoints, admin, etc.)
    EXCLUDED_PATHS = [
        '/admin/',
        '/static/',
        '/media/',
        '/api/',
        '/health/',
        '/favicon.ico',
    ]

    def process_response(self, request, response):
        """
        Process response and track page views for successful GET requests.

        Args:
            request: Django request object
            response: Django response object

        Returns:
            response: Unmodified response object
        """
        try:
            # Only track successful GET requests
            if (request.method == 'GET' and
                    response.status_code == 200 and
                    self._should_track_request(request)):
                # Get page information
                page_url = request.build_absolute_uri()
                page_title = self._get_page_title(request)
                referrer = request.META.get('HTTP_REFERER')

                # Track page view
                snowplow_tracker.track_page_view(
                    user=request.user,
                    page_url=page_url,
                    page_title=page_title,
                    referrer=referrer
                )

        except Exception as e:
            # Never let tracking errors affect the user experience
            logger.error(f"Snowplow tracking error: {str(e)}")

        return response

    def _should_track_request(self, request) -> bool:
        """
        Determine if request should be tracked based on path and other criteria.

        Args:
            request: Django request object

        Returns:
            bool: True if request should be tracked
        """
        path = request.path

        # Check excluded paths
        for excluded_path in self.EXCLUDED_PATHS:
            if path.startswith(excluded_path):
                return False

        # Check for AJAX requests (optional exclusion)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return False

        return True

    def _get_page_title(self, request) -> str:
        """
        Extract page title from URL name or path.

        Args:
            request: Django request object

        Returns:
            str: Human-readable page title
        """
        try:
            resolved = resolve(request.path)
            url_name = resolved.url_name

            # Map URL names to human-readable titles
            title_mapping = {
                'index': 'Home',
                'blog': 'Blog',
                'signin': 'Sign In',
                'signup': 'Sign Up',
                'create': 'Create Post',
                'profile': 'User Profile',
                'profileedit': 'Edit Profile',
                'post': 'Post Details',
                'contact': 'Contact Us',
            }

            return title_mapping.get(url_name, url_name.replace('_', ' ').title() if url_name else 'Unknown Page')

        except Exception:
            return request.path
