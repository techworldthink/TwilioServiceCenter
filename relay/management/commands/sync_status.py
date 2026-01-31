from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from relay.models import CommunicationLog
from relay.services import LogService

class Command(BaseCommand):
    help = 'Syncs the status of pending communications from Twilio'

    def handle(self, *args, **options):
        # Look for logs created in the last 7 days that are not final
        time_threshold = timezone.now() - timedelta(days=7)
        non_final_statuses = ['pending', 'queued', 'sending', 'sent', 'initiated', 'ringing']
        
        logs_to_sync = CommunicationLog.objects.filter(
            created_at__gte=time_threshold,
            status__in=non_final_statuses
        ).exclude(twilio_sid='').select_related('account')
        
        count = logs_to_sync.count()
        self.stdout.write(f"Found {count} logs to sync...")
        
        synced_count = 0
        for log in logs_to_sync:
            try:
                if LogService.sync_status_from_twilio(log):
                    synced_count += 1
                    self.stdout.write(f"Synced {log.twilio_sid}: {log.status}")
                else:
                    self.stdout.write(self.style.WARNING(f"Failed to sync {log.twilio_sid}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error syncing {log.twilio_sid}: {e}"))
                
        self.stdout.write(self.style.SUCCESS(f"Successfully synced {synced_count}/{count} logs"))
