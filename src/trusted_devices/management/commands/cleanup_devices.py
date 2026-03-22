from django.core.management.base import BaseCommand
from django.utils import timezone
from rest_framework_simplejwt.settings import api_settings

from trusted_devices.models import TrustedDevice


class Command(BaseCommand):
    help = (
        "Remove stale trusted devices that haven't been seen "
        "within the refresh token lifetime."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=None,
            help=(
                "Override: remove devices not seen in this many days. "
                "Defaults to SIMPLE_JWT REFRESH_TOKEN_LIFETIME."
            ),
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show how many devices would be deleted without deleting them.",
        )

    def handle(self, *args, **options):
        if options["days"] is not None:
            from datetime import timedelta

            cutoff_delta = timedelta(days=options["days"])
        else:
            cutoff_delta = api_settings.REFRESH_TOKEN_LIFETIME

        cutoff = timezone.now() - cutoff_delta
        stale_devices = TrustedDevice.objects.filter(last_seen__lt=cutoff)
        count = stale_devices.count()

        if options["dry_run"]:
            self.stdout.write(
                self.style.WARNING(
                    f"[DRY RUN] Would delete {count} stale device(s) "
                    f"(last seen before {cutoff.isoformat()})."
                )
            )
            return

        deleted, _ = stale_devices.delete()
        self.stdout.write(
            self.style.SUCCESS(
                f"Deleted {deleted} stale device(s) "
                f"(last seen before {cutoff.isoformat()})."
            )
        )
