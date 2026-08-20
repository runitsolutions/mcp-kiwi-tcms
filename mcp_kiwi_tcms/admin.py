from django.contrib import admin
from django.utils import timezone

from mcp_kiwi_tcms.models import McpApiKey


@admin.register(McpApiKey)
class McpApiKeyAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "prefix", "created_at", "last_used_at", "revoked_at")
    list_filter = ("revoked_at",)
    search_fields = ("name", "prefix", "user__username")
    readonly_fields = (
        "prefix",
        "secret_hash",
        "created_at",
        "last_used_at",
        "revoked_at",
        "user",
    )
    actions = ("revoke_keys",)

    @admin.action(description="Revoke selected API keys")
    def revoke_keys(self, request, queryset):
        queryset.filter(revoked_at__isnull=True).update(revoked_at=timezone.now())
