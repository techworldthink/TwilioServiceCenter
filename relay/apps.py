from django.apps import AppConfig


class RelayConfig(AppConfig):
    name = 'relay'

    def ready(self):
        import os
        from . import scheduler
        
        # Only start scheduler if we are running the server
        # This is a common hack to prevent scheduler from running on migrate, etc.
        if os.environ.get('RUN_MAIN') or os.environ.get('WERKZEUG_RUN_MAIN'):
             scheduler.start()
