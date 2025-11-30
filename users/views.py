from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import CustomUserCreationForm, ProfileUpdateForm
from .models import CustomUser


def home(request):
    """Главная страница с лендингом для всех пользователей"""
    # Если пользователь авторизован, показываем ему дашборд
    if request.user.is_authenticated:
        return redirect('dashboard')

    # Для неавторизованных показываем красивый лендинг
    return render(request, 'users/home.html')

def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Регистрация прошла успешно!')
            return redirect('dashboard')
    else:
        form = CustomUserCreationForm()

    return render(request, 'users/register.html', {'form': form})


@login_required
def profile(request):
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Профиль успешно обновлен!')
            return redirect('profile')
    else:
        form = ProfileUpdateForm(instance=request.user)

    # Получаем последние датасеты пользователя
    datasets = request.user.dataset_set.all().order_by('-created_at')[:6]

    context = {
        'form': form,
        'datasets': datasets,
        'user_datasets_count': request.user.dataset_set.count(),
    }
    return render(request, 'users/profile.html', context)


@login_required
def dashboard(request):
    """Панель управления для авторизованных пользователей"""
    user_datasets = request.user.dataset_set.all().order_by('-created_at')[:5]
    total_datasets = request.user.dataset_set.count()

    # Получаем статистику по изображениям
    total_images = 0
    annotated_images = 0

    for dataset in request.user.dataset_set.all():
        total_images += dataset.imagefile_set.count()
        annotated_images += dataset.imagefile_set.filter(is_annotated=True).count()

    context = {
        'recent_datasets': user_datasets,
        'total_datasets': total_datasets,
        'total_images': total_images,
        'annotated_images': annotated_images,
    }
    return render(request, 'users/dashboard.html', context)