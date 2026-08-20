import secrets

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from mcp_kiwi_tcms.models import TOKEN_PREFIX, McpApiKey


class Command(BaseCommand):
    help = "Create a Kiwi MCP API key for a Django user. Prints the plaintext once."

    def add_arguments(self, parser):
        parser.add_argument("--username", required=True, help="Django username to bind the key to")
        parser.add_argument("--name", default="mcp", help="Human label for this key")

    def handle(self, *args, **options):
        user_model = get_user_model()
        username = options["username"]
        try:
            user = user_model.objects.get(**{user_model.USERNAME_FIELD: username})
        except user_model.DoesNotExist as exc:
            raise CommandError(f"User {username!r} does not exist") from exc
        if not user.is_active:
            raise CommandError(f"User {username!r} is inactive")

        plaintext = TOKEN_PREFIX + secrets.token_urlsafe(32)
        key = McpApiKey.issue(user, options["name"], plaintext)
        self.stdout.write(self.style.WARNING("Store this token now; it will not be shown again."))
        self.stdout.write(f"id={key.pk} prefix={key.prefix}")
        self.stdout.write(plaintext)
