from celery import shared_task
from django.core.files import File
from .models import Report
from .utils import generate_report_file


@shared_task
def generate_report_task(report_id):
    """Задача Celery для генерации отчета"""
    try:
        report = Report.objects.get(id=report_id)

        # Генерируем файл отчета
        buffer, filename, content_type = generate_report_file(report, report.format)
        report.report_file.save(filename, buffer)
        report.save()

        return {
            'status': 'Отчет сгенерирован!',
            'report_id': report.id
        }

    except Exception as e:
        raise e