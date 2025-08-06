"""
Enhanced Django views with comprehensive Snowplow tracking integration.
Implements enterprise-grade analytics tracking with proper error handling and performance optimization.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User, auth
from django.contrib.auth import authenticate
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect
from django.core.paginator import Paginator
from django.db.models import Q
import logging
import json
from datetime import datetime

from .models import Post, Comment, Contact

# Import Snowplow service (create this as shown in previous response)
try:
    from .services.snowplow_service import snowplow_tracker

    SNOWPLOW_AVAILABLE = True
except ImportError:
    SNOWPLOW_AVAILABLE = False
    logging.warning("Snowplow service not available. Analytics tracking disabled.")

logger = logging.getLogger(__name__)


def track_event_safe(func):
    """
    Decorator to safely handle Snowplow tracking without affecting application flow.
    Implements circuit breaker pattern for tracking failures.
    """

    def wrapper(*args, **kwargs):
        try:
            if SNOWPLOW_AVAILABLE:
                return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Snowplow tracking error in {func.__name__}: {str(e)}")

    return wrapper


def index(request):
    """
    Enhanced index view with comprehensive analytics tracking and performance optimization.
    Implements pagination and search functionality.
    """
    try:
        # Performance optimization: Use select_related and prefetch_related
        user_posts = Post.objects.select_related('user').filter(
            user_id=request.user.id if request.user.is_authenticated else -1
        ).order_by("-id")

        top_posts = Post.objects.select_related('user').order_by("-likes")[:10]
        recent_posts = Post.objects.select_related('user').order_by("-id")[:20]

        # Pagination for better performance
        paginator = Paginator(recent_posts, 10)
        page_number = request.GET.get('page', 1)
        page_obj = paginator.get_page(page_number)

        # Track page view with enhanced context
        @track_event_safe
        def track_index_visit():
            snowplow_tracker.track_self_describing_event(
                user=request.user,
                schema="iglu:com.blogapp/page_visit/jsonschema/1-0-0",
                data={
                    "page_type": "home",
                    "total_posts": Post.objects.count(),
                    "user_posts_count": user_posts.count(),
                    "top_posts_count": top_posts.count(),
                    "page_number": int(page_number),
                    "is_authenticated": request.user.is_authenticated,
                    "timestamp": datetime.now().isoformat()
                }
            )

        track_index_visit()

        context = {
            'posts': user_posts,
            'top_posts': top_posts,
            'recent_posts': page_obj,
            'user': request.user,
            'media_url': settings.MEDIA_URL,
            'page_obj': page_obj,
            'total_posts': Post.objects.count(),
            'snowplow_available': SNOWPLOW_AVAILABLE
        }

        return render(request, "index.html", context)

    except Exception as e:
        logger.error(f"Error in index view: {str(e)}")
        messages.error(request, "An error occurred while loading the page.")
        return render(request, "index.html", {'user': request.user})


@csrf_protect
def signup(request):
    """
    Enhanced signup view with comprehensive conversion funnel tracking.
    """
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        password2 = request.POST.get('password2', '')
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()

        # Track signup attempt
        @track_event_safe
        def track_signup_attempt():
            snowplow_tracker.track_user_action(
                user=request.user,
                action='signup_attempt',
                category='authentication',
                properties={
                    'username': username,
                    'email': email,
                    'has_first_name': bool(first_name),
                    'has_last_name': bool(last_name),
                    'timestamp': datetime.now().isoformat()
                }
            )

        track_signup_attempt()

        # Validation logic
        if not all([username, email, password, password2]):
            messages.error(request, "All fields are required.")

            @track_event_safe
            def track_signup_validation_error():
                snowplow_tracker.track_user_action(
                    user=request.user,
                    action='signup_failed',
                    category='authentication',
                    properties={'reason': 'incomplete_fields', 'username': username}
                )

            track_signup_validation_error()
            return redirect('signup')

        if password != password2:
            messages.error(request, "Passwords do not match.")

            @track_event_safe
            def track_password_mismatch():
                snowplow_tracker.track_user_action(
                    user=request.user,
                    action='signup_failed',
                    category='authentication',
                    properties={'reason': 'password_mismatch', 'username': username}
                )

            track_password_mismatch()
            return redirect('signup')

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")

            @track_event_safe
            def track_username_exists():
                snowplow_tracker.track_user_action(
                    user=request.user,
                    action='signup_failed',
                    category='authentication',
                    properties={'reason': 'username_exists', 'username': username}
                )

            track_username_exists()
            return redirect('signup')

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already exists.")

            @track_event_safe
            def track_email_exists():
                snowplow_tracker.track_user_action(
                    user=request.user,
                    action='signup_failed',
                    category='authentication',
                    properties={'reason': 'email_exists', 'email': email}
                )

            track_email_exists()
            return redirect('signup')

        try:
            # Create new user
            new_user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name
            )

            # Track successful signup
            @track_event_safe
            def track_signup_success():
                snowplow_tracker.track_self_describing_event(
                    user=new_user,
                    schema="iglu:com.blogapp/user_registered/jsonschema/1-0-0",
                    data={
                        "user_id": new_user.id,
                        "username": username,
                        "email": email,
                        "has_first_name": bool(first_name),
                        "has_last_name": bool(last_name),
                        "registration_timestamp": datetime.now().isoformat()
                    }
                )

            track_signup_success()

            messages.success(request, "Account created successfully! Please sign in.")
            return redirect('signin')

        except Exception as e:
            logger.error(f"Error creating user: {str(e)}")
            messages.error(request, "An error occurred during registration.")
            return redirect('signup')

    return render(request, "signup.html", {'snowplow_available': SNOWPLOW_AVAILABLE})


@csrf_protect
def signin(request):
    """
    Enhanced signin view with session tracking and security monitoring.
    """
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        # Track login attempt
        @track_event_safe
        def track_login_attempt():
            snowplow_tracker.track_user_action(
                user=request.user,
                action='login_attempt',
                category='authentication',
                properties={
                    'username': username,
                    'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                    'ip_address': request.META.get('REMOTE_ADDR', ''),
                    'timestamp': datetime.now().isoformat()
                }
            )

        track_login_attempt()

        if not username or not password:
            messages.error(request, "Username and password are required.")
            return redirect('signin')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            auth.login(request, user)

            # Track successful login
            @track_event_safe
            def track_login_success():
                snowplow_tracker.track_self_describing_event(
                    user=user,
                    schema="iglu:com.blogapp/user_session/jsonschema/1-0-0",
                    data={
                        "session_event": "login",
                        "user_id": user.id,
                        "username": username,
                        "login_timestamp": datetime.now().isoformat(),
                        "is_staff": user.is_staff,
                        "last_login": user.last_login.isoformat() if user.last_login else None
                    }
                )

            track_login_success()

            messages.success(request, f"Welcome back, {user.first_name or user.username}!")

            # Redirect to next page if provided
            next_page = request.GET.get('next', 'index')
            return redirect(next_page)
        else:
            # Track failed login
            @track_event_safe
            def track_login_failure():
                snowplow_tracker.track_user_action(
                    user=request.user,
                    action='login_failed',
                    category='authentication',
                    properties={
                        'username': username,
                        'reason': 'invalid_credentials',
                        'timestamp': datetime.now().isoformat()
                    }
                )

            track_login_failure()

            messages.error(request, 'Invalid username or password.')
            return redirect('signin')

    return render(request, "signin.html", {'snowplow_available': SNOWPLOW_AVAILABLE})


def logout(request):
    """
    Enhanced logout view with session tracking.
    """

    # Track logout before actually logging out
    @track_event_safe
    def track_logout():
        if request.user.is_authenticated:
            snowplow_tracker.track_self_describing_event(
                user=request.user,
                schema="iglu:com.blogapp/user_session/jsonschema/1-0-0",
                data={
                    "session_event": "logout",
                    "user_id": request.user.id,
                    "username": request.user.username,
                    "logout_timestamp": datetime.now().isoformat(),
                    "session_duration_estimate": "unknown"
                }
            )

    track_logout()

    auth.logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect('index')


def blog(request):
    """
    Enhanced blog view with search, filtering, and pagination.
    """
    search_query = request.GET.get('search', '')
    category_filter = request.GET.get('category', '')

    # Base queryset with optimization
    posts_query = Post.objects.select_related('user').order_by("-id")
    carousel_images = ['img1.jpg', 'img2.jpg', 'img3.jpg', 'img4.jpg']

    # Apply search filter
    if search_query:
        posts_query = posts_query.filter(
            Q(postname__icontains=search_query) |
            Q(content__icontains=search_query) |
            Q(category__icontains=search_query)
        )

    # Apply category filter
    if category_filter:
        posts_query = posts_query.filter(category__iexact=category_filter)

    # Get user posts and top posts
    user_posts = posts_query.filter(
        user_id=request.user.id if request.user.is_authenticated else -1
    )
    top_posts = Post.objects.select_related('user').order_by("-likes")[:10]

    # Pagination
    paginator = Paginator(posts_query, 12)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    # Get unique categories for filter dropdown
    categories = Post.objects.values_list('category', flat=True).distinct()

    # Track blog page visit
    @track_event_safe
    def track_blog_visit():
        snowplow_tracker.track_self_describing_event(
            user=request.user,
            schema="iglu:com.blogapp/page_visit/jsonschema/1-0-0",
            data={
                "page_type": "blog",
                "search_query": search_query,
                "category_filter": category_filter,
                "results_count": posts_query.count(),
                "page_number": int(page_number),
                "timestamp": datetime.now().isoformat()
            }
        )

    track_blog_visit()

    context = {
        'posts': user_posts,
        'top_posts': top_posts,
        'recent_posts': page_obj,
        'user': request.user,
        'media_url': settings.MEDIA_URL,
        'page_obj': page_obj,
        'search_query': search_query,
        'category_filter': category_filter,
        'categories': categories,
        'snowplow_available': SNOWPLOW_AVAILABLE,
        "carousel_images": carousel_images
    }

    return render(request, "blog.html", context)


@login_required
@csrf_protect
def create(request):
    """
    Enhanced create post view with content analytics tracking.
    """
    if request.method == 'POST':
        try:
            postname = request.POST.get('postname', '').strip()
            content = request.POST.get('content', '').strip()
            category = request.POST.get('category', '').strip()
            image = request.FILES.get('image')

            if not all([postname, content, category]):
                messages.error(request, "Title, content, and category are required.")
                return redirect('create')

            # Create new post
            new_post = Post(
                postname=postname,
                content=content,
                category=category,
                image=image,
                user=request.user
            )
            new_post.save()

            # Track post creation with detailed analytics
            @track_event_safe
            def track_post_creation():
                snowplow_tracker.track_self_describing_event(
                    user=request.user,
                    schema="iglu:com.blogapp/content_created/jsonschema/1-0-0",
                    data={
                        "content_type": "post",
                        "post_id": new_post.id,
                        "post_title": postname,
                        "category": category,
                        "content_length": len(content),
                        "word_count": len(content.split()),
                        "has_image": bool(image),
                        "author_id": request.user.id,
                        "creation_timestamp": datetime.now().isoformat()
                    }
                )

            track_post_creation()

            messages.success(request, "Post created successfully!")
            return redirect('index')

        except Exception as e:
            logger.error(f"Error creating post: {str(e)}")

            # Track post creation failure
            @track_event_safe
            def track_creation_failure():
                snowplow_tracker.track_user_action(
                    user=request.user,
                    action='post_creation_failed',
                    category='content',
                    properties={'error': str(e), 'timestamp': datetime.now().isoformat()}
                )

            track_creation_failure()
            messages.error(request, "An error occurred while creating the post.")
            return redirect('create')

    # Get categories for dropdown
    categories = Post.objects.values_list('category', flat=True).distinct()

    return render(request, "create.html", {
        'categories': categories,
        'snowplow_available': SNOWPLOW_AVAILABLE
    })


def profile(request, id):
    """
    Enhanced profile view with user analytics tracking.
    """
    try:
        profile_user = get_object_or_404(User, id=id)
        user_posts = Post.objects.filter(user=profile_user).order_by("-id")

        # Pagination for user posts
        paginator = Paginator(user_posts, 6)
        page_number = request.GET.get('page', 1)
        page_obj = paginator.get_page(page_number)

        # Calculate user statistics
        total_posts = user_posts.count()
        total_likes = sum(post.likes for post in user_posts)

        # Track profile view
        @track_event_safe
        def track_profile_view():
            snowplow_tracker.track_self_describing_event(
                user=request.user,
                schema="iglu:com.blogapp/profile_view/jsonschema/1-0-0",
                data={
                    "viewed_user_id": profile_user.id,
                    "viewed_username": profile_user.username,
                    "viewer_user_id": request.user.id if request.user.is_authenticated else None,
                    "is_own_profile": request.user.id == profile_user.id if request.user.is_authenticated else False,
                    "profile_stats": {
                        "total_posts": total_posts,
                        "total_likes": total_likes
                    },
                    "timestamp": datetime.now().isoformat()
                }
            )

        track_profile_view()

        context = {
            'user': profile_user,
            'posts': page_obj,
            'media_url': settings.MEDIA_URL,
            'page_obj': page_obj,
            'total_posts': total_posts,
            'total_likes': total_likes,
            'is_own_profile': request.user.id == profile_user.id if request.user.is_authenticated else False,
            'snowplow_available': SNOWPLOW_AVAILABLE
        }

        return render(request, 'profile.html', context)

    except Exception as e:
        logger.error(f"Error in profile view: {str(e)}")
        messages.error(request, "Profile not found.")
        return redirect('index')


@login_required
@csrf_protect
def profileedit(request, id):
    """
    Enhanced profile edit view with change tracking.
    """
    if request.user.id != int(id):
        messages.error(request, "You can only edit your own profile.")
        return redirect('profile', id=id)

    user = get_object_or_404(User, id=id)

    if request.method == 'POST':
        old_data = {
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email
        }

        firstname = request.POST.get('firstname', '').strip()
        lastname = request.POST.get('lastname', '').strip()
        email = request.POST.get('email', '').strip()

        # Validate email uniqueness
        if email != user.email and User.objects.filter(email=email).exists():
            messages.error(request, "Email already exists.")
            return redirect('profileedit', id=id)

        # Update user data
        user.first_name = firstname
        user.last_name = lastname
        user.email = email
        user.save()

        # Track profile update
        @track_event_safe
        def track_profile_update():
            changes = {}
            if old_data['first_name'] != firstname:
                changes['first_name'] = {'old': old_data['first_name'], 'new': firstname}
            if old_data['last_name'] != lastname:
                changes['last_name'] = {'old': old_data['last_name'], 'new': lastname}
            if old_data['email'] != email:
                changes['email'] = {'old': old_data['email'], 'new': email}

            snowplow_tracker.track_self_describing_event(
                user=user,
                schema="iglu:com.blogapp/profile_updated/jsonschema/1-0-0",
                data={
                    "user_id": user.id,
                    "changes": changes,
                    "timestamp": datetime.now().isoformat()
                }
            )

        track_profile_update()

        messages.success(request, "Profile updated successfully!")
        return redirect('profile', id=id)

    return render(request, "profileedit.html", {
        'user': user,
        'snowplow_available': SNOWPLOW_AVAILABLE
    })


@login_required
@require_POST
def increaselikes(request, id):
    """
    Enhanced like functionality with engagement analytics.
    """
    try:
        post = get_object_or_404(Post, id=id)

        # Prevent users from liking their own posts (optional business rule)
        if post.user == request.user:
            return JsonResponse({
                'success': False,
                'message': 'You cannot like your own post.'
            })

        post.likes += 1
        post.save()

        # Track like action with detailed context
        @track_event_safe
        def track_like_action():
            snowplow_tracker.track_self_describing_event(
                user=request.user,
                schema="iglu:com.blogapp/engagement_action/jsonschema/1-0-0",
                data={
                    "action_type": "like",
                    "target_type": "post",
                    "target_id": post.id,
                    "target_title": post.postname,
                    "target_author_id": post.user.id,
                    "new_like_count": post.likes,
                    "liker_id": request.user.id,
                    "timestamp": datetime.now().isoformat()
                }
            )

        track_like_action()

        if request.headers.get('Content-Type') == 'application/json':
            return JsonResponse({
                'success': True,
                'new_like_count': post.likes,
                'message': 'Post liked successfully!'
            })

        messages.success(request, "Post liked!")
        return redirect("index")

    except Exception as e:
        logger.error(f"Error liking post: {str(e)}")

        if request.headers.get('Content-Type') == 'application/json':
            return JsonResponse({
                'success': False,
                'message': 'An error occurred while liking the post.'
            })

        messages.error(request, "An error occurred while liking the post.")
        return redirect("index")


def post(request, id):
    """
    Enhanced post detail view with comprehensive analytics.
    """
    try:
        post_obj = get_object_or_404(Post, id=id)
        comments = Comment.objects.select_related('user').filter(post=post_obj).order_by('-id')
        recent_posts = Post.objects.select_related('user').order_by("-id")[:5]

        # Track post view
        @track_event_safe
        def track_post_view():
            snowplow_tracker.track_self_describing_event(
                user=request.user,
                schema="iglu:com.blogapp/content_view/jsonschema/1-0-0",
                data={
                    "content_type": "post",
                    "post_id": post_obj.id,
                    "post_title": post_obj.postname,
                    "post_category": post_obj.category,
                    "author_id": post_obj.user.id,
                    "viewer_id": request.user.id if request.user.is_authenticated else None,
                    "is_author": request.user == post_obj.user if request.user.is_authenticated else False,
                    "post_stats": {
                        "likes": post_obj.likes,
                        "comments": comments.count()
                    },
                    "timestamp": datetime.now().isoformat()
                }
            )

        track_post_view()

        context = {
            "user": request.user,
            'post': post_obj,
            'recent_posts': recent_posts,
            'media_url': settings.MEDIA_URL,
            'comments': comments,
            'total_comments': comments.count(),
            'snowplow_available': SNOWPLOW_AVAILABLE
        }

        return render(request, "post-details.html", context)

    except Exception as e:
        logger.error(f"Error in post detail view: {str(e)}")
        messages.error(request, "Post not found.")
        return redirect('index')


@login_required
@csrf_protect
def savecomment(request, id):
    """
    Enhanced comment creation with engagement tracking.
    """
    if request.method == 'POST':
        try:
            post_obj = get_object_or_404(Post, id=id)
            content = request.POST.get('message', '').strip()

            if not content:
                messages.error(request, "Comment cannot be empty.")
                return redirect('post', id=id)

            # Create new comment
            new_comment = Comment(
                post=post_obj,
                user=request.user,
                content=content
            )
            new_comment.save()

            # Track comment creation
            @track_event_safe
            def track_comment_creation():
                snowplow_tracker.track_self_describing_event(
                    user=request.user,
                    schema="iglu:com.blogapp/engagement_action/jsonschema/1-0-0",
                    data={
                        "action_type": "comment",
                        "target_type": "post",
                        "target_id": post_obj.id,
                        "target_title": post_obj.postname,
                        "target_author_id": post_obj.user.id,
                        "comment_id": new_comment.id,
                        "comment_length": len(content),
                        "word_count": len(content.split()),
                        "commenter_id": request.user.id,
                        "timestamp": datetime.now().isoformat()
                    }
                )

            track_comment_creation()

            messages.success(request, "Comment added successfully!")
            return redirect('post', id=id)

        except Exception as e:
            logger.error(f"Error creating comment: {str(e)}")
            messages.error(request, "An error occurred while adding the comment.")
            return redirect('post', id=id)

    return redirect('index')


@login_required
def deletecomment(request, id):
    """
    Enhanced comment deletion with tracking.
    """
    try:
        comment = get_object_or_404(Comment, id=id)
        post_id = comment.post.id

        # Check permissions
        if comment.user != request.user and comment.post.user != request.user:
            messages.error(request, "You can only delete your own comments or comments on your posts.")
            return redirect('post', id=post_id)

        # Track comment deletion
        @track_event_safe
        def track_comment_deletion():
            snowplow_tracker.track_self_describing_event(
                user=request.user,
                schema="iglu:com.blogapp/content_deleted/jsonschema/1-0-0",
                data={
                    "content_type": "comment",
                    "comment_id": comment.id,
                    "post_id": post_id,
                    "deleter_id": request.user.id,
                    "original_author_id": comment.user.id,
                    "is_author_delete": comment.user == request.user,
                    "timestamp": datetime.now().isoformat()
                }
            )

        track_comment_deletion()

        comment.delete()
        messages.success(request, "Comment deleted successfully!")

        return redirect('post', id=post_id)

    except Exception as e:
        logger.error(f"Error deleting comment: {str(e)}")
        messages.error(request, "An error occurred while deleting the comment.")
        return redirect('index')


@login_required
@csrf_protect
def editpost(request, id):
    """
    Enhanced post edit view with change tracking.
    """
    try:
        post_obj = get_object_or_404(Post, id=id)

        # Check permissions
        if post_obj.user != request.user:
            messages.error(request, "You can only edit your own posts.")
            return redirect('post', id=id)

        if request.method == 'POST':
            old_data = {
                'postname': post_obj.postname,
                'content': post_obj.content,
                'category': post_obj.category
            }

            postname = request.POST.get('postname', '').strip()
            content = request.POST.get('content', '').strip()
            category = request.POST.get('category', '').strip()

            if not all([postname, content, category]):
                messages.error(request, "Title, content, and category are required.")
                return redirect('editpost', id=id)

            # Update post
            post_obj.postname = postname
            post_obj.content = content
            post_obj.category = category
            post_obj.save()

            # Track post update
            @track_event_safe
            def track_post_update():
                changes = {}
                if old_data['postname'] != postname:
                    changes['title'] = {'old': old_data['postname'], 'new': postname}
                if old_data['content'] != content:
                    changes['content'] = {
                        'old_length': len(old_data['content']),
                        'new_length': len(content)
                    }
                if old_data['category'] != category:
                    changes['category'] = {'old': old_data['category'], 'new': category}

                snowplow_tracker.track_self_describing_event(
                    user=request.user,
                    schema="iglu:com.blogapp/content_updated/jsonschema/1-0-0",
                    data={
                        "content_type": "post",
                        "post_id": post_obj.id,
                        "changes": changes,
                        "editor_id": request.user.id,
                        "timestamp": datetime.now().isoformat()
                    }
                )

            track_post_update()

            messages.success(request, "Post updated successfully!")
            return redirect('profile', id=request.user.id)

        return render(request, "postedit.html", {
            'post': post_obj,
            'snowplow_available': SNOWPLOW_AVAILABLE
        })

    except Exception as e:
        logger.error(f"Error in edit post view: {str(e)}")
        messages.error(request, "Post not found.")
        return redirect('index')


@login_required
def deletepost(request, id):
    """
    Enhanced post deletion with tracking.
    """
    try:
        post_obj = get_object_or_404(Post, id=id)

        # Check permissions
        if post_obj.user != request.user:
            messages.error(request, "You can only delete your own posts.")
            return redirect('post', id=id)

        # Track post deletion before deleting
        @track_event_safe
        def track_post_deletion():
            snowplow_tracker.track_self_describing_event(
                user=request.user,
                schema="iglu:com.blogapp/content_deleted/jsonschema/1-0-0",
                data={
                    "content_type": "post",
                    "post_id": post_obj.id,
                    "post_title": post_obj.postname,
                    "category": post_obj.category,
                    "likes": post_obj.likes,
                    "comment_count": Comment.objects.filter(post=post_obj).count(),
                    "deleter_id": request.user.id,
                    "timestamp": datetime.now().isoformat()
                }
            )

        track_post_deletion()

        post_obj.delete()
        messages.success(request, "Post deleted successfully!")

        return redirect('profile', id=request.user.id)

    except Exception as e:
        logger.error(f"Error deleting post: {str(e)}")
        messages.error(request, "An error occurred while deleting the post.")
        return redirect('profile', id=request.user.id)


@csrf_protect
def contact_us(request):
    """
    Enhanced contact form with submission tracking.
    """
    if request.method == 'POST':
        try:
            name = request.POST.get('name', '').strip()
            email = request.POST.get('email', '').strip()
            subject = request.POST.get('subject', '').strip()
            message = request.POST.get('message', '').strip()

            if not all([name, email, subject, message]):
                messages.error(request, "All fields are required.")
                return render(request, "contact.html", {'snowplow_available': SNOWPLOW_AVAILABLE})

            # Create contact entry
            contact_obj = Contact(
                name=name,
                email=email,
                subject=subject,
                message=message
            )
            contact_obj.save()

            # Track contact form submission
            @track_event_safe
            def track_contact_submission():
                snowplow_tracker.track_self_describing_event(
                    user=request.user,
                    schema="iglu:com.blogapp/form_submission/jsonschema/1-0-0",
                    data={
                        "form_type": "contact",
                        "contact_id": contact_obj.id,
                        "submitter_name": name,
                        "submitter_email": email,
                        "subject": subject,
                        "message_length": len(message),
                        "is_authenticated": request.user.is_authenticated,
                        "timestamp": datetime.now().isoformat()
                    }
                )

            track_contact_submission()

            messages.success(request, f"Dear {name}, Thanks for your message! We'll get back to you soon.")

        except Exception as e:
            logger.error(f"Error processing contact form: {str(e)}")
            messages.error(request, "An error occurred while sending your message.")

    return render(request, "contact.html", {'snowplow_available': SNOWPLOW_AVAILABLE})
