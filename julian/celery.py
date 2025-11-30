import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'julian.settings')

app = Celery('julian')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
app.conf.beat_django_auto_import = False

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')