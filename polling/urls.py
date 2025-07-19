from django.urls import path
from . import views, admin_views, auth_views, notification_views, payment_views, admin_payment_views

urlpatterns = [
    # Core game routes
    path("", views.index, name="index"),
    path("join/", views.join_room, name="join_room"),
    path("room/<str:room_name>/", views.room, name="room"),

    # Public game information
    path("game-history/", views.game_history, name="game_history"),
    path("api/player/<str:username>/", views.player_stats, name="player_stats"),

    # User Authentication routes
    path("register/", auth_views.register_view, name="register"),
    path("login/", auth_views.login_view, name="login"),
    path("logout/", auth_views.logout_view, name="logout"),
    path("verify-otp/", auth_views.verify_otp_view, name="verify_otp"),
    path("resend-otp/", auth_views.resend_otp_view, name="resend_otp"),
    path("welcome/", auth_views.welcome_view, name="welcome"),

    # User Profile routes
    path("profile/", auth_views.user_profile, name="user_profile"),
    path("profile/edit/", auth_views.edit_profile, name="edit_profile"),
    path("profile/change-password/", auth_views.change_password, name="change_password"),
    path("profile/upload-avatar/", auth_views.upload_avatar, name="upload_avatar"),
    path("profile/resend-verification/", auth_views.resend_verification_email, name="resend_verification_email"),  # Use views.upload_avatar

    # User History and Wallet routes
    path("history/", auth_views.user_history, name="user_history"),
    path("recent-matches/", auth_views.recent_matches, name="recent_matches"),
    path("wallet/", auth_views.wallet_management, name="wallet_management"),
    path("wallet/add-money/", auth_views.add_money, name="add_money"),
    path("transactions/", auth_views.transaction_history, name="transaction_history"),

    # Responsible Gambling routes
    path("api/responsible-gambling/status/", views.responsible_gambling_status, name="responsible_gambling_status"),
    path("api/responsible-gambling/set-limits/", views.set_gambling_limits, name="set_gambling_limits"),
    path("api/responsible-gambling/cooling-off/", views.trigger_cooling_off, name="trigger_cooling_off"),

    # System Monitoring routes
    path("api/monitoring/dashboard/", views.system_monitoring_dashboard, name="monitoring_dashboard"),
    path("api/monitoring/resolve-alert/", views.resolve_alert, name="resolve_alert"),

    # Notification routes
    path("notifications/settings/", notification_views.notification_settings, name="notification_settings"),
    path("notifications/history/", notification_views.notification_history, name="notification_history"),

    # Notification API routes
    path("api/notifications/", notification_views.get_notifications, name="api_notifications"),
    path("api/notifications/<int:notification_id>/read/", notification_views.mark_notification_read, name="api_mark_notification_read"),
    path("api/notifications/mark-all-read/", notification_views.mark_all_notifications_read, name="api_mark_all_notifications_read"),
    path("api/notifications/<int:notification_id>/delete/", notification_views.delete_notification, name="api_delete_notification"),
    path("api/notifications/stats/", notification_views.get_notification_stats, name="api_notification_stats"),

    # Payment System Routes
    path("payment/dashboard/", payment_views.payment_dashboard, name="payment_dashboard"),
    path("payment/history/", payment_views.payment_history, name="payment_history"),
    path("payment/test-razorpay/", payment_views.test_razorpay, name="test_razorpay"),
    path("test-razorpay-simple/", views.test_razorpay_simple, name="test_razorpay_simple"),
    path("api/payment/create-deposit-order/", payment_views.create_deposit_order, name="create_deposit_order"),
    path("api/payment/verify-payment/", payment_views.verify_payment, name="verify_payment"),
    path("api/payment/request-withdrawal/", payment_views.request_withdrawal, name="request_withdrawal"),
    path("api/payment/status/<int:payment_id>/", payment_views.payment_status, name="payment_status"),
    path("webhooks/razorpay/", payment_views.razorpay_webhook, name="razorpay_webhook"),

    # API routes (keep player history for potential future use)
    path("api/player/<str:username>/history/", views.player_bet_history, name="player_bet_history"),

    # Legacy admin redirect
    path("admin/", views.admin_redirect, name="admin_redirect"),

    # Debug endpoint (only available in DEBUG mode)
    path("debug/session/", views.debug_session, name="debug_session"),
    path("test-chrome/", views.test_chrome, name="test_chrome"),
    path("minimal-login/", views.minimal_login, name="minimal_login"),

    # Admin Panel - Authentication
    path("control-panel/", admin_views.admin_login, name="admin_login"),
    path("control-panel/logout/", admin_views.admin_logout, name="admin_logout"),

    # Admin Panel - Main Pages
    path("control-panel/dashboard/", admin_views.admin_dashboard, name="admin_dashboard"),
    path("control-panel/game-control/", admin_views.game_control, name="admin_game_control"),
    path("control-panel/game-control-live/", admin_views.admin_game_control_live, name="admin_game_control_live"),
    path("control-panel/users/", admin_views.user_management, name="admin_user_management"),
    path("control-panel/users/<int:player_id>/", admin_views.player_detail, name="admin_player_detail"),
    path("control-panel/financial/", admin_views.financial_management, name="admin_financial"),
    path("control-panel/master-wallet/", admin_views.master_wallet_dashboard, name="admin_master_wallet"),
    path("control-panel/master-wallet/transactions/", admin_views.master_wallet_transactions, name="admin_master_wallet_transactions"),
    path("control-panel/payments/", admin_payment_views.payment_admin_dashboard, name="admin_payment_dashboard"),
    path("control-panel/payments/transactions/", admin_payment_views.payment_transactions_list, name="admin_payment_transactions"),
    path("control-panel/payments/approve/<int:transaction_id>/", admin_payment_views.approve_withdrawal, name="approve_withdrawal"),
    path("control-panel/payments/reject/<int:transaction_id>/", admin_payment_views.reject_withdrawal, name="reject_withdrawal"),
    path("control-panel/payments/statistics/", admin_payment_views.payment_statistics, name="payment_statistics"),
    path("control-panel/payments/player/<int:player_id>/", admin_payment_views.player_payment_history, name="player_payment_history"),

    # Withdrawal Management
    path("control-panel/withdrawals/", admin_payment_views.withdrawal_management, name="admin_withdrawal_management"),
    path("control-panel/withdrawals/detail/<str:withdrawal_id>/", admin_payment_views.withdrawal_detail, name="admin_withdrawal_detail"),
    path("control-panel/withdrawals/approve/<str:withdrawal_id>/", admin_payment_views.approve_withdrawal, name="admin_approve_withdrawal"),
    path("control-panel/withdrawals/reject/<str:withdrawal_id>/", admin_payment_views.reject_withdrawal, name="admin_reject_withdrawal"),
    path("control-panel/withdrawals/complete/<str:withdrawal_id>/", admin_payment_views.complete_withdrawal, name="admin_complete_withdrawal"),
    path("control-panel/razorpay-test/", admin_payment_views.razorpay_test_dashboard, name="admin_razorpay_test"),
    path("control-panel/reports/", admin_views.game_reports, name="admin_reports"),
    path("control-panel/logs/", admin_views.admin_logs, name="admin_logs"),

    # Admin Panel - API Endpoints
    path("control-panel/api/select-color/", admin_views.admin_select_color, name="admin_select_color"),
    path("control-panel/api/game-status/", admin_views.admin_game_status, name="admin_game_status"),
    path("control-panel/api/live-betting-stats/", admin_views.live_betting_stats, name="admin_live_betting_stats"),
    path("control-panel/api/live-game-control-stats/", admin_views.live_game_control_stats, name="admin_live_game_control_stats"),
    path("control-panel/api/submit-result/", admin_views.submit_game_result, name="admin_submit_result"),
    path("control-panel/api/timer-info/", admin_views.get_game_timer_info, name="admin_timer_info"),
    path("control-panel/api/delete-user/<int:user_id>/", admin_views.delete_user, name="admin_delete_user"),
    path("control-panel/api/test-razorpay-connection/", admin_payment_views.test_razorpay_connection, name="admin_test_razorpay"),

    # Test Data Management
    path("control-panel/test-data/", admin_views.test_data_management, name="test_data_management"),

    # Email Service Status
    path("control-panel/email-status/", admin_views.email_service_status, name="email_service_status"),
]