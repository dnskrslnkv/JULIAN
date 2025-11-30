from django.urls import path
from . import views

urlpatterns = [
    # Аннотации
    path('dataset/<int:dataset_pk>/annotate/', views.annotation_start, name='annotation_start'),
    path('dataset/<int:dataset_pk>/annotate/<int:image_pk>/', views.annotation_tool, name='annotation_tool'),

    # API для аннотаций
    path('api/annotation/<int:image_pk>/save/', views.save_annotation, name='save_annotation'),
    path('api/annotation/<int:annotation_pk>/delete/', views.delete_annotation, name='delete_annotation'),
    path('api/annotations/<int:image_pk>/', views.get_annotations, name='get_annotations'),
    path('api/progress/<int:dataset_pk>/', views.annotation_progress, name='annotation_progress'),

    # ML модели
    path('dataset/<int:dataset_pk>/models/', views.model_list, name='model_list'),
    path('dataset/<int:dataset_pk>/models/create/', views.create_model, name='create_model'),
    path('dataset/<int:dataset_pk>/models/<int:model_pk>/', views.model_detail, name='model_detail'),
    path('dataset/<int:dataset_pk>/models/<int:model_pk>/delete/', views.delete_model, name='delete_model'),

    # ML операции
    path('dataset/<int:dataset_pk>/train/', views.train_model_from_list, name='train_model_from_list'),
    path('dataset/<int:dataset_pk>/models/<int:model_pk>/train/', views.train_model, name='train_model'),
    path('dataset/<int:dataset_pk>/models/<int:model_pk>/detect/', views.run_detection, name='run_detection'),


    path('dataset/<int:dataset_pk>/models/<int:model_pk>/results/', views.detection_results, name='detection_results'),


]