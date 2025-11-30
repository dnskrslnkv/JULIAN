from django.contrib import admin
from .models import Dataset, ImageFile, PDFFile


@admin.register(Dataset)
class DatasetAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'status', 'created_at', 'get_image_count']
    list_filter = ['status', 'created_at', 'user']
    search_fields = ['name', 'description']

    def get_image_count(self, obj):
        return obj.get_image_count()

    get_image_count.short_description = 'Изображений'


@admin.register(ImageFile)
class ImageFileAdmin(admin.ModelAdmin):
    list_display = ['original_filename', 'dataset', 'uploaded_at', 'is_annotated']
    list_filter = ['is_annotated', 'uploaded_at', 'dataset']
    search_fields = ['original_filename', 'dataset__name']


@admin.register(PDFFile)
class PDFFileAdmin(admin.ModelAdmin):
    list_display = ['original_filename', 'dataset', 'uploaded_at', 'images_extracted']
    list_filter = ['images_extracted', 'uploaded_at', 'dataset']
    search_fields = ['original_filename', 'dataset__name']