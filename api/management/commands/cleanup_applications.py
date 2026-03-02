from django.core.management.base import BaseCommand
from api.supabase_models import Application, ApplicationStatus, ApplicationNote, ApplicationCoverLetter

class Command(BaseCommand):
    help = "Deletes all applications except the most recent 2 to improve performance."

    def handle(self, *args, **options):
        # Get all applications ordered by matched_at descending (newest first)
        apps = Application.objects.all().order_by('-matched_at')
        count = apps.count()
        
        if count <= 2:
            self.stdout.write(self.style.SUCCESS(f"Only {count} applications found. No cleanup needed."))
            return

        # Keep the first 2 IDs
        keep_ids = list(apps.values_list('id', flat=True)[:2])
        
        # Get IDs to delete
        delete_ids = list(apps.exclude(id__in=keep_ids).values_list('id', flat=True))
        
        if not delete_ids:
            return

        self.stdout.write(f"Deleting {len(delete_ids)} applications...")

        # Delete related records first to avoid FK violations
        ApplicationStatus.objects.filter(application_id__in=delete_ids).delete()
        ApplicationNote.objects.filter(application_id__in=delete_ids).delete()
        ApplicationCoverLetter.objects.filter(application_id__in=delete_ids).delete()
        
        # Delete the applications
        deleted_count, _ = Application.objects.filter(id__in=delete_ids).delete()
        
        self.stdout.write(self.style.SUCCESS(f"Successfully deleted {deleted_count} applications. Kept 2."))
