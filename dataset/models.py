from django.db import models
from django.urls import reverse
from users.models import CustomUser
import os
from uuid import uuid4


def rename_uploaded_file(instance, filename):
    """Переименовывает загружаемый файл в формат UUID"""
    ext = filename.split('.')[-1]
    filename = f"{uuid4().hex}.{ext}"
    return os.path.join('uploads/images/', filename)


def rename_uploaded_pdf(instance, filename):
    """Переименовывает загружаемый PDF файл"""
    ext = filename.split('.')[-1]
    filename = f"{uuid4().hex}.{ext}"
    return os.path.join('uploads/pdf/', filename)


class Dataset(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Черновик'),
        ('uploading', 'Загрузка файлов'),
        ('annotating', 'Разметка'),
        ('processing', 'Обработка'),
        ('completed', 'Завершен'),
        ('error', 'Ошибка'),
    ]

    name = models.CharField(max_length=255, verbose_name='Название датасета')
    description = models.TextField(blank=True, verbose_name='Описание')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, verbose_name='Пользователь')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', verbose_name='Статус')
    is_processed = models.BooleanField(default=False, verbose_name='Обработан')

    class Meta:
        verbose_name = 'Датасет'
        verbose_name_plural = 'Датасеты'
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('dataset_detail', kwargs={'pk': self.pk})

    def get_image_count(self):
        return self.imagefile_set.count()


    def get_annotated_count(self):
        """Количество размеченных изображений """
        return self.imagefile_set.filter(is_annotated=True).count()

    def get_annotated_images_count(self):
        """Количество изображений с аннотациями """
        return self.imagefile_set.filter(annotation__isnull=False).distinct().count()

    def get_unique_classes_count(self):
        """Количество уникальных классов в аннотациях"""
        from detection.models import Annotation
        return Annotation.objects.filter(image__dataset=self).values_list('label', flat=True).distinct().count()




class ImageFile(models.Model):
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE, verbose_name='Датасет')
    image = models.ImageField(
        upload_to=rename_uploaded_file,
        verbose_name='Изображение',
        help_text='Поддерживаемые форматы: JPG, PNG, JPEG'
    )
    original_filename = models.CharField(max_length=255, verbose_name='Исходное имя файла')
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата загрузки')
    is_annotated = models.BooleanField(default=False, verbose_name='Размечено')

    class Meta:
        verbose_name = 'Изображение'
        verbose_name_plural = 'Изображения'
        ordering = ['uploaded_at']

    def __str__(self):
        return f"{self.original_filename} ({self.dataset.name})"


class PDFFile(models.Model):
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE, verbose_name='Датасет')
    pdf = models.FileField(
        upload_to=rename_uploaded_pdf,
        verbose_name='PDF файл'
    )
    original_filename = models.CharField(max_length=255, verbose_name='Исходное имя файла')
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата загрузки')
    images_extracted = models.BooleanField(default=False, verbose_name='Изображения извлечены')
    page_count = models.IntegerField(default=0, verbose_name='Количество страниц')

    class Meta:
        verbose_name = 'PDF файл'
        verbose_name_plural = 'PDF файлы'

    def __str__(self):
        return f"{self.original_filename} ({self.dataset.name})"