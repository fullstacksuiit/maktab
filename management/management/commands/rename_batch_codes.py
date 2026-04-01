from django.core.management.base import BaseCommand
from django.db import transaction

from management.models import Batch, Organization


class Command(BaseCommand):
    help = "Rename all batch codes to B1, B2, ... B(n) per organization, ordered by creation date."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview changes without saving.",
        )
        parser.add_argument(
            "--org-id",
            type=int,
            help="Only rename batches for a specific organization ID.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        org_id = options.get("org_id")

        orgs = Organization.objects.all()
        if org_id:
            orgs = orgs.filter(id=org_id)

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no changes will be saved.\n"))

        with transaction.atomic():
            for org in orgs:
                batches = Batch.objects.filter(organization=org).order_by("created_at", "id")
                self.stdout.write(f"\nOrganization: {org.org_name} ({batches.count()} batches)")

                for i, batch in enumerate(batches, start=1):
                    new_code = f"B{i}"
                    if batch.batch_code != new_code:
                        self.stdout.write(f"  {batch.batch_code} -> {new_code}  ({batch.batch_name})")
                        if not dry_run:
                            batch.batch_code = new_code
                            batch.save(update_fields=["batch_code"])
                    else:
                        self.stdout.write(f"  {batch.batch_code} (unchanged)")

            if dry_run:
                transaction.set_rollback(True)

        self.stdout.write(self.style.SUCCESS("\nDone." if not dry_run else "\nDry run complete. No changes made."))
