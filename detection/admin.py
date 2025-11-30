from django.contrib import admin
from .models import Annotation, AnnotationSession, MLModel, DetectionResult

@admin.register(Annotation)
class AnnotationAdmin(admin.ModelAdmin):
    list_display = ['label', 'image', 'created_by', 'created_at']
    list_filter = ['created_at', 'created_by', 'label']
    search_fields = ['label', 'image__original_filename']
    readonly_fields = ['created_at']

@admin.register(AnnotationSession)
class AnnotationSessionAdmin(admin.ModelAdmin):
    list_display = ['dataset', 'user', 'current_image', 'created_at']
    list_filter = ['created_at', 'user']
    search_fields = ['dataset__name', 'user__username']

@admin.register(MLModel)
class MLModelAdmin(admin.ModelAdmin):
    list_display = ['name', 'dataset', 'status', 'accuracy', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['name', 'dataset__name']
    readonly_fields = ['created_at']

@admin.register(DetectionResult)
class DetectionResultAdmin(admin.ModelAdmin):
    list_display = ['detected_label', 'confidence', 'image', 'ml_model', 'created_at']
    list_filter = ['created_at', 'detected_label']
    search_fields = ['detected_label', 'image__original_filename']
    readonly_fields = ['created_at']