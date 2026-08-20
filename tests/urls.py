from django.urls import include, path

urlpatterns = [
    path("mcp/", include("mcp_kiwi_tcms.urls")),
]
