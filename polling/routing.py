from django.urls import re_path

from . import consumers, admin_consumers

websocket_urlpatterns = [
    re_path(r"ws/game/(?P<room_name>\w+)/$", consumers.GameConsumer.as_asgi()),
    re_path(r"ws/control-panel/game-control/$", admin_consumers.AdminGameConsumer.as_asgi()),
    re_path(r"ws/control-panel/dashboard/$", admin_consumers.AdminDashboardConsumer.as_asgi()),
    re_path(r"ws/control-panel/users/$", admin_consumers.AdminUserManagementConsumer.as_asgi()),
    re_path(r"ws/control-panel/financial/$", admin_consumers.AdminFinancialConsumer.as_asgi()),
]