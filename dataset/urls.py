from django.urls import path
from . import views

urlpatterns = [
    path('', views.dataset_list, name='dataset_list'),
    path('create/', views.dataset_create, name='dataset_create'),
    path('<int:pk>/', views.dataset_detail, name='dataset_detail'),
    path('<int:pk>/upload/', views.dataset_upload, name='dataset_upload'),
    path('<int:pk>/delete/', views.dataset_delete, name='dataset_delete'),
    path('image/<int:pk>/delete/', views.delete_image, name='delete_image'),
    path('pdf/<int:pk>/delete/', views.delete_pdf, name='delete_pdf'),
]