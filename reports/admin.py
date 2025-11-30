from django.contrib import admin
from .models import Report
@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ['title', 'dataset', 'ml_model', 'format', 'accuracy', 'created_at']
    list_filter = ['format', 'created_at']
    search_fields = ['title', 'dataset__name']
    readonly_fields = ['created_at']



