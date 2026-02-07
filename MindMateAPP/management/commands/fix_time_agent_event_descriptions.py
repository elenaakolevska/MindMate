from django.core.management.base import BaseCommand

from MindMateAPP.models import CalendarEvent


class Command(BaseCommand):
    help = "Normalize descriptions for calendar events created by the Time Agent."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Only show how many events would be updated without saving changes.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        # Heuristic: limit to events whose description starts with or contains the Time Agent prefix
        qs = CalendarEvent.objects.filter(description__icontains="Time Agent")

        updated_count = 0

        for event in qs.iterator():
            original = event.description or ""
            new_text = original

            # Replace literal "\\n" (backslash + n) with real newlines
            new_text = new_text.replace("\\n", "\n")

            # Replace "undefined" with a Macedonian placeholder
            new_text = new_text.replace("undefined", "Недефинирано")

            if new_text != original:
                updated_count += 1
                if not dry_run:
                    event.description = new_text
                    event.save(update_fields=["description"])

        if dry_run:
            self.stdout.write(self.style.WARNING(f"[DRY RUN] Would update {updated_count} Time Agent-related events."))
        else:
            self.stdout.write(self.style.SUCCESS(f"Updated {updated_count} Time Agent-related events."))
