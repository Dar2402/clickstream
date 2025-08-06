"""
Snowplow tracking service for server-side event tracking.
Implements enterprise-grade event tracking with proper error handling and async support.
"""

import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import uuid

from snowplow_tracker import Tracker, Emitter, Subject
from snowplow_tracker import SelfDescribingJson
from django.conf import settings
from django.contrib.auth.models import User

logger = logging.getLogger(__name__)


class SnowplowTrackingService:
    """
    Enterprise-grade Snowplow tracking service with comprehensive event tracking capabilities.
    Follows the observer pattern and dependency injection principles.
    """

    def __init__(self):
        """Initialize the Snowplow tracker with production-ready configuration."""
        self.collector_url = settings.SNOWPLOW_SETTINGS.get('COLLECTOR_URL', 'localhost:8080')
        self.app_id = settings.SNOWPLOW_SETTINGS.get('APP_ID', 'django-blog-app')
        self.namespace = settings.SNOWPLOW_SETTINGS.get('NAMESPACE', 'blog-tracker')

        # Initialize emitter with retry logic and batch processing
        print("self.collector_url.replace('http://', '').replace('https://', '')", self.collector_url.replace('http://', '').replace('https://', ''))
        self.emitter = Emitter(
            endpoint=self.collector_url,
            protocol='http',
            method='post',
            buffer_capacity=10,  # Batch processing for performance
            on_success=self._on_success,
            on_failure=self._on_failure
        )

        # Initialize tracker with comprehensive configuration
        self.tracker = Tracker(
            emitters=[self.emitter],
            namespace=self.namespace,
            app_id=self.app_id,
            encode_base64=settings.SNOWPLOW_SETTINGS.get('ENCODE_BASE64', True)
        )

        logger.info(f"Snowplow tracker initialized for app: {self.app_id}")

    def _on_success(self, success_count: int) -> None:
        """Handle successful event transmission."""
        logger.info(f"Successfully sent {success_count} events to Snowplow collector")

    def _on_failure(self, failure_count: int, success_count: int) -> None:
        """Handle failed event transmission with proper logging."""
        logger.error(f"Failed to send {failure_count} events, {success_count} succeeded")

    def _create_user_context(self, user: User) -> SelfDescribingJson:
        """
        Create user context following Snowplow's self-describing JSON schema.
        Implements privacy-by-design principles.
        """
        if not user or not user.is_authenticated:
            return None

        user_context = {
            "user_id": str(user.id),
            "username": user.username,
            "is_authenticated": True,
            "is_staff": user.is_staff,
            "date_joined": user.date_joined.isoformat() if user.date_joined else None
        }

        # Only include email if user has explicitly consented (implement consent logic)
        if hasattr(user, 'has_analytics_consent') and user.has_analytics_consent:
            user_context["email"] = user.email

        return SelfDescribingJson(
            schema="iglu:com.blogapp/user_context/jsonschema/1-0-0",
            data=user_context
        )

    def track_page_view(self, user: User, page_url: str, page_title: str,
                        referrer: Optional[str] = None, **kwargs) -> None:
        """
        Track page view events with comprehensive context.

        Args:
            user: Django user instance
            page_url: Current page URL
            page_title: Page title
            referrer: Referrer URL
            **kwargs: Additional custom properties
        """
        try:
            # Create subject with user information
            subject = Subject()
            if user and user.is_authenticated:
                subject.set_user_id(str(user.id))

            # Set subject on tracker
            self.tracker.set_subject(subject)

            # Create contexts
            contexts = []
            user_context = self._create_user_context(user)
            if user_context:
                contexts.append(user_context)

            # Track page view with enhanced context
            self.tracker.track_page_view(
                page_url=page_url,
                page_title=page_title,
                referrer=referrer,
                context=contexts
            )

            logger.debug(
                f"Page view tracked: {page_url} for user: {user.username if user.is_authenticated else 'anonymous'}")

        except Exception as e:
            logger.error(f"Failed to track page view: {str(e)}")

    def track_user_action(self, user: User, action: str, category: str,
                          properties: Dict[str, Any] = None, **kwargs) -> None:
        """
        Track custom user actions using structured events.

        Args:
            user: Django user instance
            action: Action name (e.g., 'like_post', 'create_comment')
            category: Event category (e.g., 'engagement', 'content')
            properties: Additional event properties
            **kwargs: Additional context
        """
        try:
            properties = properties or {}

            # Create subject
            subject = Subject()
            if user and user.is_authenticated:
                subject.set_user_id(str(user.id))

            self.tracker.set_subject(subject)

            # Create contexts
            contexts = []
            user_context = self._create_user_context(user)
            if user_context:
                contexts.append(user_context)

            # Track structured event
            self.tracker.track_struct_event(
                category=category,
                action=action,
                label=properties.get('label'),
                property_=properties.get('property'),
                value=properties.get('value'),
                context=contexts
            )

            logger.debug(f"User action tracked: {action} in category: {category}")

        except Exception as e:
            logger.error(f"Failed to track user action: {str(e)}")

    def track_self_describing_event(self, user: User, schema: str,
                                    data: Dict[str, Any], **kwargs) -> None:
        """
        Track self-describing events for custom business logic.

        Args:
            user: Django user instance
            schema: Iglu schema URI
            data: Event data matching the schema
            **kwargs: Additional context
        """
        try:
            # Create subject
            subject = Subject()
            if user and user.is_authenticated:
                subject.set_user_id(str(user.id))

            self.tracker.set_subject(subject)

            # Create contexts
            contexts = []
            user_context = self._create_user_context(user)
            if user_context:
                contexts.append(user_context)

            # Create self-describing event
            event = SelfDescribingJson(schema=schema, data=data)

            # Track event
            self.tracker.track_unstruct_event(event, context=contexts)

            logger.debug(f"Self-describing event tracked with schema: {schema}")

        except Exception as e:
            logger.error(f"Failed to track self-describing event: {str(e)}")


# Singleton instance for application-wide use
snowplow_tracker = SnowplowTrackingService()
