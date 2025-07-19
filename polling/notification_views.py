"""
Views for handling notification-related API endpoints
"""

import logging
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q

from .models import (
    Player, Notification, NotificationType, 
    UserNotificationPreference
)
from .decorators import secure_api_endpoint
from .auth_views import get_current_user, auth_required

logger = logging.getLogger(__name__)


@secure_api_endpoint(
    authentication_required=True,
    allowed_methods=['GET'],
    rate_limit_per_minute=30,
    rate_limit_per_hour=300
)
def get_notifications(request):
    """
    Get user's notifications with pagination
    """
    try:
        user = request.player
        page = int(request.GET.get('page', 1))
        limit = min(int(request.GET.get('limit', 20)), 50)  # Max 50 per page
        
        # Get notifications
        notifications = Notification.objects.filter(
            user=user
        ).select_related('notification_type').order_by('-created_at')
        
        # Filter by status if specified
        status = request.GET.get('status')
        if status in ['read', 'unread']:
            if status == 'read':
                notifications = notifications.filter(read_at__isnull=False)
            else:
                notifications = notifications.filter(read_at__isnull=True)
        
        # Filter by category if specified
        category = request.GET.get('category')
        if category:
            notifications = notifications.filter(notification_type__category=category)
        
        # Paginate
        paginator = Paginator(notifications, limit)
        page_obj = paginator.get_page(page)
        
        # Get unread count
        unread_count = Notification.objects.filter(
            user=user,
            read_at__isnull=True
        ).count()
        
        # Serialize notifications
        notifications_data = []
        for notification in page_obj:
            notifications_data.append({
                'id': notification.id,
                'title': notification.title,
                'message': notification.message,
                'priority': notification.priority,
                'status': notification.status,
                'read_at': notification.read_at.isoformat() if notification.read_at else None,
                'created_at': notification.created_at.isoformat(),
                'notification_type': {
                    'name': notification.notification_type.name,
                    'category': notification.notification_type.category,
                },
                'extra_data': notification.extra_data,
            })
        
        return JsonResponse({
            'success': True,
            'notifications': notifications_data,
            'unread_count': unread_count,
            'pagination': {
                'current_page': page_obj.number,
                'total_pages': paginator.num_pages,
                'total_count': paginator.count,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting notifications for user {request.player.username}: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Failed to load notifications'
        }, status=500)


@secure_api_endpoint(
    authentication_required=True,
    allowed_methods=['POST'],
    rate_limit_per_minute=60,
    rate_limit_per_hour=600
)
def mark_notification_read(request, notification_id):
    """
    Mark a specific notification as read
    """
    try:
        user = request.player
        
        notification = get_object_or_404(
            Notification,
            id=notification_id,
            user=user
        )
        
        if not notification.read_at:
            notification.mark_as_read()
            
        return JsonResponse({
            'success': True,
            'message': 'Notification marked as read'
        })
        
    except Exception as e:
        logger.error(f"Error marking notification {notification_id} as read: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Failed to mark notification as read'
        }, status=500)


@secure_api_endpoint(
    authentication_required=True,
    allowed_methods=['POST'],
    rate_limit_per_minute=10,
    rate_limit_per_hour=100
)
def mark_all_notifications_read(request):
    """
    Mark all user's notifications as read
    """
    try:
        user = request.player
        
        # Update all unread notifications
        updated_count = Notification.objects.filter(
            user=user,
            read_at__isnull=True
        ).update(
            read_at=timezone.now(),
            status='read'
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Marked {updated_count} notifications as read'
        })
        
    except Exception as e:
        logger.error(f"Error marking all notifications as read for user {request.player.username}: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Failed to mark notifications as read'
        }, status=500)


@auth_required
def notification_settings(request):
    """
    View and manage notification preferences
    """
    user = get_current_user(request)
    if not user:
        return redirect('login')
    
    if request.method == 'POST':
        try:
            # Update notification preferences
            for key, value in request.POST.items():
                if key.startswith('notification_'):
                    # Extract notification type ID
                    notification_type_id = key.replace('notification_', '')
                    
                    try:
                        notification_type = NotificationType.objects.get(id=notification_type_id)
                        preference, created = UserNotificationPreference.objects.get_or_create(
                            user=user,
                            notification_type=notification_type,
                            defaults={'delivery_method': value, 'is_enabled': value != 'none'}
                        )
                        
                        if not created:
                            preference.delivery_method = value
                            preference.is_enabled = value != 'none'
                            preference.save()
                            
                    except NotificationType.DoesNotExist:
                        continue
            
            messages.success(request, 'Notification preferences updated successfully!')
            return redirect('notification_settings')
            
        except Exception as e:
            logger.error(f"Error updating notification preferences for user {user.username}: {e}")
            messages.error(request, 'Failed to update notification preferences.')
    
    # Get notification types and user preferences
    notification_types = NotificationType.objects.filter(is_active=True).order_by('category', 'name')
    user_preferences = {
        pref.notification_type_id: pref
        for pref in UserNotificationPreference.objects.filter(user=user)
    }
    
    # Group by category
    categories = {}
    for nt in notification_types:
        if nt.category not in categories:
            categories[nt.category] = []
        
        preference = user_preferences.get(nt.id)
        categories[nt.category].append({
            'notification_type': nt,
            'preference': preference,
            'current_setting': preference.delivery_method if preference else ('both' if nt.default_enabled else 'none')
        })
    
    context = {
        'user': user,
        'categories': categories,
        'title': 'Notification Settings'
    }
    
    return render(request, 'notifications/settings.html', context)


@auth_required
def notification_history(request):
    """
    View notification history
    """
    user = get_current_user(request)
    if not user:
        return redirect('login')
    
    # Get filter parameters
    category = request.GET.get('category', 'all')
    status = request.GET.get('status', 'all')
    
    # Build query
    notifications = Notification.objects.filter(user=user).select_related('notification_type')
    
    if category != 'all':
        notifications = notifications.filter(notification_type__category=category)
    
    if status == 'read':
        notifications = notifications.filter(read_at__isnull=False)
    elif status == 'unread':
        notifications = notifications.filter(read_at__isnull=True)
    
    notifications = notifications.order_by('-created_at')
    
    # Paginate
    paginator = Paginator(notifications, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get statistics
    stats = {
        'total': Notification.objects.filter(user=user).count(),
        'unread': Notification.objects.filter(user=user, read_at__isnull=True).count(),
        'today': Notification.objects.filter(
            user=user,
            created_at__date=timezone.now().date()
        ).count(),
    }
    
    # Get available categories
    available_categories = NotificationType.objects.filter(
        is_active=True
    ).values_list('category', flat=True).distinct()
    
    context = {
        'user': user,
        'notifications': page_obj,
        'stats': stats,
        'current_category': category,
        'current_status': status,
        'available_categories': available_categories,
        'title': 'Notification History'
    }
    
    return render(request, 'notifications/history.html', context)


@secure_api_endpoint(
    authentication_required=True,
    allowed_methods=['DELETE'],
    rate_limit_per_minute=30,
    rate_limit_per_hour=300
)
def delete_notification(request, notification_id):
    """
    Delete a specific notification
    """
    try:
        user = request.player
        
        notification = get_object_or_404(
            Notification,
            id=notification_id,
            user=user
        )
        
        notification.delete()
        
        return JsonResponse({
            'success': True,
            'message': 'Notification deleted successfully'
        })
        
    except Exception as e:
        logger.error(f"Error deleting notification {notification_id}: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Failed to delete notification'
        }, status=500)


@secure_api_endpoint(
    authentication_required=True,
    allowed_methods=['GET'],
    rate_limit_per_minute=20,
    rate_limit_per_hour=200
)
def get_notification_stats(request):
    """
    Get notification statistics for the user
    """
    try:
        user = request.player
        
        stats = {
            'total': Notification.objects.filter(user=user).count(),
            'unread': Notification.objects.filter(user=user, read_at__isnull=True).count(),
            'today': Notification.objects.filter(
                user=user,
                created_at__date=timezone.now().date()
            ).count(),
            'this_week': Notification.objects.filter(
                user=user,
                created_at__gte=timezone.now() - timezone.timedelta(days=7)
            ).count(),
        }
        
        # Category breakdown
        category_stats = {}
        for category, label in NotificationType.CATEGORY_CHOICES:
            category_stats[category] = {
                'label': label,
                'total': Notification.objects.filter(
                    user=user,
                    notification_type__category=category
                ).count(),
                'unread': Notification.objects.filter(
                    user=user,
                    notification_type__category=category,
                    read_at__isnull=True
                ).count(),
            }
        
        return JsonResponse({
            'success': True,
            'stats': stats,
            'category_stats': category_stats
        })
        
    except Exception as e:
        logger.error(f"Error getting notification stats for user {request.player.username}: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Failed to load notification statistics'
        }, status=500)
