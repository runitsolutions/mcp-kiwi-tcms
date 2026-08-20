from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.db import models
from django.utils import timezone

TOKEN_PREFIX = "kiwi_mcp_"
PREFIX_LENGTH = 16


class McpApiKey(models.Model):
    """Opaque API key bound to a Django user. The plaintext is shown only at creation."""

    name = models.CharField(max_length=128)
    prefix = models.CharField(max_length=PREFIX_LENGTH, unique=True, db_index=True)
    secret_hash = models.CharField(max_length=128)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="mcp_api_keys",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "MCP API key"
        verbose_name_plural = "MCP API keys"

    def __str__(self) -> str:
        status = "revoked" if self.revoked_at else "active"
        return f"{self.name} ({self.prefix}…, {status})"

    @property
    def is_active(self) -> bool:
        return self.revoked_at is None

    def matches(self, plaintext: str) -> bool:
        return check_password(plaintext, self.secret_hash)

    def mark_used(self) -> None:
        type(self).objects.filter(pk=self.pk).update(last_used_at=timezone.now())

    def revoke(self) -> None:
        self.revoked_at = timezone.now()
        self.save(update_fields=["revoked_at"])

    @classmethod
    def issue(cls, user, name: str, plaintext: str) -> "McpApiKey":
        return cls.objects.create(
            name=name,
            prefix=plaintext[:PREFIX_LENGTH],
            secret_hash=make_password(plaintext),
            user=user,
        )
