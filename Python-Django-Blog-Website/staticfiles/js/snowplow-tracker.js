class BlogSnowplowTracker {
    constructor() {
    this.trackerName = 'blogTracker';
    this.appId = 'django-blog-app';

    const hostname = window.location.hostname;
    console.log('window.location.hostname', hostname);

    const isLocalhost = (
        hostname === 'localhost' ||
        hostname === '127.0.0.1' ||
        hostname === '::1' ||
        hostname.includes("localhost.in") ||
        /^192\.168\.\d{1,3}\.\d{1,3}$/.test(hostname) ||
        /^10\.\d{1,3}\.\d{1,3}\.\d{1,3}$/.test(hostname) ||
        /^172\.(1[6-9]|2\d|3[0-1])\.\d{1,3}\.\d{1,3}$/.test(hostname)
    );

    this.collectorUrl = isLocalhost
        ? 'http://localhost:8080'
        : 'https://your-production-collector.com';

    this.userId = document.body.dataset.trackUserId || 'anonymous';

    this.eventTypes = {
        CLICK: 'click',
        HOVER: 'hover',
        SCROLL: 'scroll',
        DOUBLE_CLICK: 'dblclick',
        MOUSEDOWN: 'mousedown',
        MOUSEUP: 'mouseup',
        FOCUS: 'focus',
        BLUR: 'blur',
        SUBMIT: 'submit',
        CHANGE: 'change',
        KEYPRESS: 'keypress',
        TOUCH: 'touch'
    };

    this.initialize();
}

    initialize() {
        // Configure tracker
        window.snowplow('newTracker', this.trackerName, this.collectorUrl, {
            appId: this.appId,
            platform: 'web',
            cookieDomain: window.location.hostname,
            discoverRootDomain: true,
            contexts: {
                webPage: true,
                performanceTiming: true,
                gaCookies: true,
                geolocation: true
            },
            post: true,
            bufferSize: 1,
            respectDoNotTrack: false
        });

        // Enable automatic tracking
        window.snowplow('enableActivityTracking', {
            minimumVisitLength: 10,
            heartbeatDelay: 10
        });

        window.snowplow('enableLinkClickTracking');
        window.snowplow('enableFormTracking');
        window.snowplow('enableErrorTracking');

        // Track initial page view with additional context
        this.trackPageView();

        console.log('✅ Snowplow initialized for user:', this.userId);
    }

    trackPageView() {
        const pageTitle = document.title;
        const referrer = document.referrer;
        const url = window.location.href;

        window.snowplow('trackPageView', {
            title: pageTitle,
            referrer: referrer,
            url: url
        }, [
            {
                schema: 'iglu:com.snowplowanalytics.snowplow/web_page/jsonschema/1-0-0',
                data: {
                    id: this.generatePageViewId(),
                    url: url,
                    title: pageTitle
                }
            },
            {
                schema: 'iglu:com.snowplowanalytics.snowplow/client_session/jsonschema/1-0-1',
                data: {
                    userId: this.userId,
                    sessionId: this.generateSessionId(),
                    deviceType: this.getDeviceType()
                }
            }
        ]);
    }

    setupEnhancedTracking() {
        this.trackClicks();
        this.trackHovers();
        this.trackScrollDepth();
        this.trackFormInteractions();
        this.trackMediaEngagement();
        this.trackKeyboardInteractions();
        this.trackMouseMovements();
    }

    trackClicks() {
        document.addEventListener('click', (e) => {
            const target = e.target;
            const path = this.getElementPath(target);

            this.trackStructEvent('ui_interaction', 'click', path, {
                element: target.tagName.toLowerCase(),
                id: target.id || 'none',
                class: target.className || 'none',
                text: target.textContent?.trim().substring(0, 100) || 'none',
                href: target.href || 'none',
                position: this.getClickPosition(e),
                page: window.location.pathname
            });
        }, true);
    }

    trackHovers() {
        const hoverThreshold = 1000; // 1 second
        let hoverTimer;
        let hoverTarget = null;
        let hoverStartTime = 0;

        document.addEventListener('mouseover', (e) => {
            const target = e.target;
            if (target !== hoverTarget) {
                clearTimeout(hoverTimer);
                hoverTarget = target;
                hoverStartTime = Date.now();

                hoverTimer = setTimeout(() => {
                    const hoverDuration = Date.now() - hoverStartTime;
                    const path = this.getElementPath(target);

                    this.trackStructEvent('ui_interaction', 'hover', path, {
                        element: target.tagName.toLowerCase(),
                        duration: hoverDuration,
                        position: this.getMousePosition(e),
                        page: window.location.pathname
                    });
                }, hoverThreshold);
            }
        });

        document.addEventListener('mouseout', (e) => {
            if (hoverTarget && hoverTarget !== e.relatedTarget) {
                clearTimeout(hoverTimer);
                hoverTarget = null;
            }
        });
    }

    trackScrollDepth() {
        const thresholds = [25, 50, 75, 100];
        const trackedThresholds = new Set();

        window.addEventListener('scroll', () => {
            const scrollPosition = window.scrollY;
            const pageHeight = document.body.scrollHeight - window.innerHeight;
            const scrollPercent = Math.round((scrollPosition / pageHeight) * 100);

            thresholds.forEach(threshold => {
                if (scrollPercent >= threshold && !trackedThresholds.has(threshold)) {
                    trackedThresholds.add(threshold);
                    this.trackStructEvent('page_interaction', 'scroll_depth', 'percentage', {
                        value: threshold,
                        position: scrollPosition,
                        max: pageHeight,
                        url: window.location.pathname
                    });
                }
            });
        }, { passive: true });
    }

    trackFormInteractions() {
        document.addEventListener('focusin', (e) => {
            if (['INPUT', 'TEXTAREA', 'SELECT'].includes(e.target.tagName)) {
                this.trackStructEvent('form_interaction', 'field_focus', e.target.name || 'unnamed', {
                    type: e.target.type,
                    page: window.location.pathname
                });
            }
        });

        document.addEventListener('change', (e) => {
            if (['INPUT', 'TEXTAREA', 'SELECT'].includes(e.target.tagName)) {
                this.trackStructEvent('form_interaction', 'field_change', e.target.name || 'unnamed', {
                    type: e.target.type,
                    value: e.target.value?.substring(0, 100) || 'empty',
                    page: window.location.pathname
                });
            }
        });
    }

    trackMediaEngagement() {
        document.querySelectorAll('img, video').forEach(media => {
            const observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        this.trackStructEvent('media', 'view', media.tagName.toLowerCase(), {
                            src: media.src || 'none',
                            alt: media.alt || 'none',
                            inViewport: Math.round(entry.intersectionRatio * 100),
                            page: window.location.pathname
                        });
                        observer.unobserve(media);
                    }
                });
            }, { threshold: 0.5 });

            observer.observe(media);
        });
    }

    trackKeyboardInteractions() {
        document.addEventListener('keydown', (e) => {
            if (e.target.tagName === 'BODY') {
                this.trackStructEvent('keyboard', 'key_press', 'global', {
                    key: e.key,
                    code: e.code,
                    page: window.location.pathname
                });
            }
        });
    }

    trackMouseMovements() {
        let mouseMoveCount = 0;
        let lastPosition = { x: 0, y: 0 };

        document.addEventListener('mousemove', (e) => {
            mouseMoveCount++;
            if (mouseMoveCount % 10 === 0) {
                const distance = Math.sqrt(
                    Math.pow(e.clientX - lastPosition.x, 2) +
                    Math.pow(e.clientY - lastPosition.y, 2)
                );

                this.trackStructEvent('mouse', 'movement', 'tracking', {
                    x: e.clientX,
                    y: e.clientY,
                    distance: Math.round(distance),
                    page: window.location.pathname
                });

                lastPosition = { x: e.clientX, y: e.clientY };
            }
        });
    }

    // Helper methods
    getElementPath(element) {
        const path = [];
        let current = element;

        while (current && current !== document.body) {
            let selector = current.tagName.toLowerCase();
            if (current.id) {
                selector += `#${current.id}`;
            } else if (current.className && typeof current.className === 'string') {
                selector += `.${current.className.split(' ').join('.')}`;
            }
            path.unshift(selector);
            current = current.parentNode;
        }

        return path.join(' > ') || 'root';
    }

    getClickPosition(event) {
        return {
            x: event.clientX,
            y: event.clientY,
            screenX: event.screenX,
            screenY: event.screenY,
            pageX: event.pageX,
            pageY: event.pageY
        };
    }

    getMousePosition(event) {
        return {
            x: event.clientX,
            y: event.clientY
        };
    }

    generatePageViewId() {
        return 'pv-' + Math.random().toString(36).substring(2, 15);
    }

    generateSessionId() {
        return 'sess-' + Math.random().toString(36).substring(2, 15);
    }

    getDeviceType() {
        const width = window.innerWidth;
        if (width < 576) return 'mobile';
        if (width < 992) return 'tablet';
        return 'desktop';
    }

    trackStructEvent(category, action, label, properties = {}) {
        const eventData = {
            category: category,
            action: action,
            label: typeof label === 'string' ? label : JSON.stringify(label),
            property: JSON.stringify({
                ...properties,
                userId: this.userId,
                url: window.location.pathname,
                timestamp: new Date().toISOString()
            })
        };

        window.snowplow('trackStructEvent', eventData);

        // For debugging
        console.debug(`[TRACK] ${category}.${action}`, label, properties);
    }
}

// Initialize when DOM is ready
if (typeof snowplow !== 'undefined') {
    document.addEventListener('DOMContentLoaded', () => {
        window.blogTracker = new BlogSnowplowTracker();
        window.blogTracker.setupEnhancedTracking();
    });
} else {
    console.error('Snowplow tracker not loaded');
}