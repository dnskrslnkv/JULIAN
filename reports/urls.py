from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('dataset/<int:dataset_pk>/reports/', views.report_list, name='report_list'),
    path('dataset/<int:dataset_pk>/model/<int:model_pk>/create-report/', views.create_report, name='create_report'),
    path('report/<int:report_pk>/', views.report_detail, name='report_detail'),
    path('report/<int:report_pk>/delete/', views.delete_report, name='delete_report'),
    path('report/<int:report_pk>/download/', views.download_report, name='download_report'),
    path('report/<int:report_pk>/download-images/', views.download_images_archive, name='download_images_archive'),
]