from django.apps import AppConfig


class RelayConfig(AppConfig):
    name = 'relay'

    def ready(self):
        import os
        import sys
        from . import scheduler
        
        # Detect if running under Gunicorn (Production)
        is_gunicorn = "gunicorn" in sys.argv[0]
        
        # Detect if running under Runserver (Dev) - check RUN_MAIN to avoid double start
        is_runserver = "runserver" in sys.argv and (os.environ.get('RUN_MAIN') or os.environ.get('WERKZEUG_RUN_MAIN'))
        
        if is_gunicorn or is_runserver:
             scheduler.start()
