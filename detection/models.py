from django.db import models
from users.models import CustomUser
from dataset.models import Dataset, ImageFile
import os

class Annotation(models.Model):
    image = models.ForeignKey(ImageFile, on_delete=models.CASCADE, verbose_name='Изображение')
    label = models.CharField(max_length=100, verbose_name='Метка')
    x = models.FloatField(verbose_name='X координата')
    y = models.FloatField(verbose_name='Y координата')
    width = models.FloatField(verbose_name='Ширина')
    height = models.FloatField(verbose_name='Высота')
    created_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, verbose_name='Создано')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')

    class Meta:
        verbose_name = 'Аннотация'
        verbose_name_plural = 'Аннотации'
        ordering = ['created_at']

    def __str__(self):
        return f"{self.label} ({self.image.original_filename})"


class AnnotationSession(models.Model):
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE, verbose_name='Датасет')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, verbose_name='Пользователь')
    current_image = models.ForeignKey(ImageFile, on_delete=models.SET_NULL, null=True, blank=True,
                                      verbose_name='Текущее изображение')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')

    class Meta:
        verbose_name = 'Сессия разметки'
        verbose_name_plural = 'Сессии разметки'

    def __str__(self):
        return f"Сессия {self.user.username} - {self.dataset.name}"


class MLModel(models.Model):
    MODEL_TYPE_CHOICES = [
        ('yolo', 'YOLO'),
        ('custom', 'Custom'),
    ]

    STATUS_CHOICES = [
        ('not_trained', 'Не обучена'),
        ('training', 'Обучается'),
        ('trained', 'Обучена'),
        ('error', 'Ошибка'),
    ]

    name = models.CharField(max_length=255, verbose_name='Название модели')
    description = models.TextField(blank=True, verbose_name='Описание')
    dataset = models.ForeignKey('dataset.Dataset', on_delete=models.CASCADE, verbose_name='Датасет')
    model_type = models.CharField(max_length=20, choices=MODEL_TYPE_CHOICES, default='yolo', verbose_name='Тип модели')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='not_trained', verbose_name='Статус')
    accuracy = models.FloatField(null=True, blank=True, verbose_name='Точность')
    precision = models.FloatField(null=True, blank=True, verbose_name='Precision')
    recall = models.FloatField(null=True, blank=True, verbose_name='Recall')
    f1_score = models.FloatField(null=True, blank=True, verbose_name='F1 Score')

    # Поля для YOLO модели
    epochs = models.IntegerField(default=50, verbose_name='Количество эпох')
    batch_size = models.IntegerField(default=16, verbose_name='Размер батча')
    img_size = models.IntegerField(default=640, verbose_name='Размер изображения')

    # Файлы модели
    model_file = models.FileField(upload_to='models/', null=True, blank=True, verbose_name='Файл модели')
    results_file = models.FileField(upload_to='model_results/', null=True, blank=True, verbose_name='Файл результатов')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    trained_at = models.DateTimeField(null=True, blank=True, verbose_name='Дата обучения')
    task_id = models.CharField(max_length=255, blank=True, null=True, verbose_name='ID задачи Celery')
    training_log = models.TextField(blank=True, null=True, verbose_name='Лог обучения')

    class Meta:
        verbose_name = 'ML Модель'
        verbose_name_plural = 'ML Модели'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.dataset.name})"

    def get_model_path(self):
        """Получить путь к файлу модели"""
        if self.model_file:
            return self.model_file.path
        return None

    def delete(self, *args, **kwargs):
        """Удаление связанных файлов при удалении модели"""
        if self.model_file:
            if os.path.isfile(self.model_file.path):
                os.remove(self.model_file.path)
        if self.results_file:
            if os.path.isfile(self.results_file.path):
                os.remove(self.results_file.path)
        super().delete(*args, **kwargs)


class DetectionResult(models.Model):
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE, verbose_name='Датасет')
    image = models.ForeignKey(ImageFile, on_delete=models.CASCADE, verbose_name='Изображение')
    ml_model = models.ForeignKey('MLModel', on_delete=models.CASCADE, verbose_name='ML Модель')
    detected_label = models.CharField(max_length=100, verbose_name='Обнаруженная метка')
    confidence = models.FloatField(verbose_name='Уверенность')
    x = models.FloatField(verbose_name='X координата')
    y = models.FloatField(verbose_name='Y координата')
    width = models.FloatField(verbose_name='Ширина')
    height = models.FloatField(verbose_name='Высота')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата обнаружения')

    class Meta:
        verbose_name = 'Результат детекции'
        verbose_name_plural = 'Результаты детекции'
        ordering = ['-confidence']

    def __str__(self):
        return f"{self.detected_label} ({self.confidence:.2f}) - {self.image.original_filename}"