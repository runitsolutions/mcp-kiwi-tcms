from django.urls import path

from mcp_kiwi_tcms.views import mcp_view

urlpatterns = [
    path("", mcp_view, name="mcp-kiwi-endpoint"),
]
