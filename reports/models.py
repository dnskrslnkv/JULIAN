from django.db import models
from users.models import CustomUser
from dataset.models import Dataset
from detection.models import MLModel
from django.core.files.storage import default_storage


class Report(models.Model):
    FORMAT_CHOICES = [
        ('pdf', 'PDF'),
        ('csv', 'CSV'),
        ('json', 'JSON'),
        ('html', 'HTML'),
    ]

    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE, verbose_name='Датасет')
    ml_model = models.ForeignKey(MLModel, on_delete=models.CASCADE, verbose_name='ML Модель')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, verbose_name='Пользователь')
    title = models.CharField(max_length=255, verbose_name='Название отчета')
    format = models.CharField(max_length=10, choices=FORMAT_CHOICES, default='pdf', verbose_name='Формат')

    # Статистика
    total_images = models.IntegerField(verbose_name='Всего изображений')
    annotated_images = models.IntegerField(verbose_name='Размеченных изображений')
    total_annotations = models.IntegerField(verbose_name='Всего аннотаций')
    total_detections = models.IntegerField(verbose_name='Всего обнаружений')
    high_confidence_detections = models.IntegerField(default=0, verbose_name='Обнаружений с уверенностью >75%')

    # Метрики качества
    accuracy = models.FloatField(verbose_name='Точность')
    precision = models.FloatField(null=True, blank=True, verbose_name='Точность (Precision)')
    recall = models.FloatField(null=True, blank=True, verbose_name='Полнота (Recall)')
    f1_score = models.FloatField(null=True, blank=True, verbose_name='F1-мера')

    # Параметры обучения
    training_epochs = models.IntegerField(default=0, verbose_name='Количество эпох')
    training_batch_size = models.IntegerField(default=0, verbose_name='Размер батча')
    training_img_size = models.IntegerField(default=640, verbose_name='Размер изображения при обучении')

    # Файлы отчета
    report_file = models.FileField(upload_to='reports/', verbose_name='Файл отчета')
    images_archive = models.FileField(upload_to='reports/archives/', null=True, blank=True,
                                      verbose_name='Архив с изображениями')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')

    class Meta:
        verbose_name = 'Отчет'
        verbose_name_plural = 'Отчеты'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.dataset.name}"

    def delete(self, *args, **kwargs):
        """Удаление файлов при удалении отчета"""
        if self.report_file:
            if default_storage.exists(self.report_file.name):
                default_storage.delete(self.report_file.name)
        if self.images_archive:
            if default_storage.exists(self.images_archive.name):
                default_storage.delete(self.images_archive.name)
        super().delete(*args, **kwargs)


class ReportImage(models.Model):
    """Изображения с высокой уверенностью для отчета"""
    report = models.ForeignKey(Report, on_delete=models.CASCADE, verbose_name='Отчет')
    image = models.ForeignKey('dataset.ImageFile', on_delete=models.CASCADE, verbose_name='Изображение')
    detection = models.ForeignKey('detection.DetectionResult', on_delete=models.CASCADE, verbose_name='Обнаружение')
    confidence = models.FloatField(verbose_name='Уверенность')
    label = models.CharField(max_length=255, verbose_name='Метка')

    class Meta:
        verbose_name = 'Изображение отчета'
        verbose_name_plural = 'Изображения отчетов'

    def __str__(self):
        return f"{self.label} ({self.confidence:.1%}) - {self.report.title}"