
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_http_methods
from django.db.models import Count, Avg, Max
from dataset.models import Dataset, ImageFile
from .models import Annotation, AnnotationSession, MLModel, DetectionResult
from .forms import AnnotationForm, AnnotationSettingsForm
from django.contrib import messages
from django.db import models
from .yolo_utils import  YOLODetector
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .tasks import train_yolo_model
from celery.result import AsyncResult


@login_required
def annotation_start(request, dataset_pk):
    """Начало сессии разметки"""
    dataset = get_object_or_404(Dataset, pk=dataset_pk, user=request.user)

    # Получаем или создаем сессию разметки
    session, created = AnnotationSession.objects.get_or_create(
        dataset=dataset,
        user=request.user,
        defaults={'current_image': dataset.imagefile_set.first()}
    )

    return redirect('annotation_tool', dataset_pk=dataset_pk, image_pk=session.current_image.pk)


@login_required
def annotation_tool(request, dataset_pk, image_pk):
    """Интерфейс разметки изображений"""
    dataset = get_object_or_404(Dataset, pk=dataset_pk, user=request.user)
    image = get_object_or_404(ImageFile, pk=image_pk, dataset=dataset)

    # Обновляем текущее изображение в сессии
    session, created = AnnotationSession.objects.get_or_create(
        dataset=dataset,
        user=request.user
    )
    session.current_image = image
    session.save()

    # Получаем все изображения датасета с аннотациями
    images = dataset.imagefile_set.all().annotate(
        annotation_count=Count('annotation')
    ).order_by('uploaded_at')

    # Получаем аннотации для текущего изображения
    annotations = Annotation.objects.filter(image=image)

    # Формы
    annotation_form = AnnotationForm()
    settings_form = AnnotationSettingsForm()

    context = {
        'dataset': dataset,
        'images': images,
        'current_image': image,
        'annotations': annotations,
        'annotation_form': annotation_form,
        'settings_form': settings_form,
        'progress_percentage': int(
            (dataset.get_annotated_count() / dataset.get_image_count()) * 100) if dataset.get_image_count() > 0 else 0,
    }
    return render(request, 'detection/annotation_tool.html', context)


@login_required
@require_POST
def save_annotation(request, image_pk):
    """Сохранение аннотации через AJAX"""
    image = get_object_or_404(ImageFile, pk=image_pk, dataset__user=request.user)

    data = json.loads(request.body)

    # Создаем аннотацию без использования формы
    try:
        annotation = Annotation(
            image=image,
            label=data.get('label', ''),
            x=data.get('x', 0),
            y=data.get('y', 0),
            width=data.get('width', 0),
            height=data.get('height', 0),
            created_by=request.user
        )
        annotation.full_clean()  # Валидация
        annotation.save()

        # Обновляем статус изображения
        image.is_annotated = True
        image.save()

        return JsonResponse({
            'success': True,
            'annotation_id': annotation.id,
            'label': annotation.label,
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'errors': str(e)
        })


@login_required
@require_http_methods(['DELETE'])
def delete_annotation(request, annotation_pk):
    """Удаление аннотации"""
    annotation = get_object_or_404(Annotation, pk=annotation_pk, created_by=request.user)
    image_pk = annotation.image.pk
    annotation.delete()

    # Проверяем, остались ли аннотации у изображения
    if not annotation.image.annotation_set.exists():
        annotation.image.is_annotated = False
        annotation.image.save()

    return JsonResponse({'success': True})


@login_required
def get_annotations(request, image_pk):
    """Получение аннотаций для изображения"""
    image = get_object_or_404(ImageFile, pk=image_pk, dataset__user=request.user)
    annotations = Annotation.objects.filter(image=image)

    annotations_data = []
    for ann in annotations:
        annotations_data.append({
            'id': ann.id,
            'label': ann.label,
            'x': ann.x,
            'y': ann.y,
            'width': ann.width,
            'height': ann.height
        })

    return JsonResponse({'annotations': annotations_data})


@login_required
def annotation_progress(request, dataset_pk):
    """Прогресс разметки датасета"""
    dataset = get_object_or_404(Dataset, pk=dataset_pk, user=request.user)

    total_images = dataset.get_image_count()
    annotated_images = dataset.get_annotated_count()
    progress = int((annotated_images / total_images) * 100) if total_images > 0 else 0

    return JsonResponse({
        'total_images': total_images,
        'annotated_images': annotated_images,
        'progress': progress
    })


@login_required
@require_POST
def train_model(request, dataset_pk, model_pk):
    """Запуск обучения существующей ML модели через Celery"""
    dataset = get_object_or_404(Dataset, pk=dataset_pk, user=request.user)
    model = get_object_or_404(MLModel, pk=model_pk, dataset=dataset)

    # Проверяем, есть ли достаточно размеченных данных
    annotated_count = dataset.get_annotated_count()
    if annotated_count < 3:
        messages.error(request, f'Недостаточно размеченных изображений. Требуется минимум 3, размечено: {annotated_count}')
        return redirect('model_detail', dataset_pk=dataset.pk, model_pk=model.pk)

    # Обновляем параметры модели если переданы
    epochs = request.POST.get('epochs')
    batch_size = request.POST.get('batch_size')
    img_size = request.POST.get('img_size')

    if epochs:
        model.epochs = int(epochs)
    if batch_size:
        model.batch_size = int(batch_size)
    if img_size:
        model.img_size = int(img_size)

    model.status = 'training'
    model.save()

    # Запускаем обучение через Celery
    task = train_yolo_model.delay(model.id)


    model.save()

    messages.success(request, f'Обучение модели "{model.name}" запущено! Это может занять несколько минут.')
    return redirect('model_list', dataset_pk=dataset.pk)

def train_model_async(ml_model_id):
    """Асинхронное обучение модели"""
    try:
        from django.utils import timezone
        ml_model = MLModel.objects.get(id=ml_model_id)
        ml_model.status = 'training'
        ml_model.save()

        # Импортируем здесь чтобы избежать циклических импортов
        from .yolo_utils import YOLOTrainer

        trainer = YOLOTrainer(ml_model)
        success = trainer.train_model()

        if success:
            ml_model = MLModel.objects.get(id=ml_model_id)
            ml_model.status = 'trained'
            ml_model.trained_at = timezone.now()
            ml_model.save()
        else:
            ml_model = MLModel.objects.get(id=ml_model_id)
            ml_model.status = 'error'
            ml_model.save()

    except Exception as e:
        import traceback
        print(f"Ошибка обучения модели: {e}")
        print(traceback.format_exc())

        # Обновляем статус модели в случае ошибки
        try:
            ml_model = MLModel.objects.get(id=ml_model_id)
            ml_model.status = 'error'
            ml_model.save()
        except:
            pass


@login_required
@require_POST
def train_model_from_list(request, dataset_pk):
    """Создание и обучение новой модели из списка моделей через Celery"""
    dataset = get_object_or_404(Dataset, pk=dataset_pk, user=request.user)

    # Проверяем, есть ли достаточно размеченных данных
    annotated_count = dataset.get_annotated_count()
    if annotated_count < 3:
        messages.error(request, f'Недостаточно размеченных изображений. Требуется минимум 3, размечено: {annotated_count}')
        return redirect('model_list', dataset_pk=dataset.pk)

    # Создаем модель
    name = request.POST.get('name', f'Модель для {dataset.name}')
    description = request.POST.get('description', '')
    model_type = request.POST.get('model_type', 'yolo')
    epochs = int(request.POST.get('epochs', 50))
    batch_size = int(request.POST.get('batch_size', 16))
    img_size = int(request.POST.get('img_size', 640))

    model = MLModel.objects.create(
        dataset=dataset,
        name=name,
        description=description,
        model_type=model_type,
        epochs=epochs,
        batch_size=batch_size,
        img_size=img_size,
        status='training'
    )

    # Запускаем обучение через Celery
    task = train_yolo_model.delay(model.id)
    model.task_id = task.id
    model.save()

    messages.success(request, f'Модель "{model.name}" создана и обучение запущено! Это может занять несколько минут.')
    return redirect('model_list', dataset_pk=dataset.pk)


@login_required
@require_POST
def run_detection(request, dataset_pk, model_pk):
    """Запуск детекции объектов через Celery"""
    dataset = get_object_or_404(Dataset, pk=dataset_pk, user=request.user)
    model = get_object_or_404(MLModel, pk=model_pk, dataset=dataset)

    if model.status != 'trained':
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'Модель не обучена. Сначала обучите модель.'})
        messages.error(request, 'Модель не обучена. Сначала обучите модель.')
        return redirect('model_detail', dataset_pk=dataset.pk, model_pk=model.pk)

    try:
        confidence = float(request.POST.get('confidence', 0.25))

        # Запускаем асинхронную задачу с правильным именем
        from .tasks import run_detection_task
        task = run_detection_task.delay(model.id, confidence)

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': 'Детекция запущена. Это может занять несколько минут.'
            })
        else:
            messages.info(request, 'Детекция запущена. Это может занять несколько минут.')
            return redirect('model_detail', dataset_pk=dataset.pk, model_pk=model.pk)

    except Exception as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': f'Ошибка при запуске детекции: {str(e)}'})
        messages.error(request, f'Ошибка при запуске детекции: {str(e)}')
        return redirect('model_detail', dataset_pk=dataset.pk, model_pk=model.pk)


@login_required
def detection_results(request, dataset_pk, model_pk):
    """Результаты детекции для датасета и модели"""
    dataset = get_object_or_404(Dataset, pk=dataset_pk, user=request.user)
    ml_model = get_object_or_404(MLModel, pk=model_pk, dataset=dataset)

    results = DetectionResult.objects.filter(
        dataset=dataset,
        ml_model=ml_model
    ).select_related('image').order_by('-confidence')

    # Статистика для шаблона
    total_detections = results.count()
    if total_detections > 0:
        avg_confidence = results.aggregate(Avg('confidence'))['confidence__avg'] * 100
        max_confidence = results.aggregate(Max('confidence'))['confidence__max'] * 100
    else:
        avg_confidence = 0
        max_confidence = 0

    # Уникальные метки
    unique_labels = results.values_list('detected_label', flat=True).distinct()

    # Распределение по классам
    class_distribution = results.values('detected_label').annotate(
        count=Count('id')
    ).order_by('-count')

    class_distribution_data = {
        'labels': [item['detected_label'] for item in class_distribution],
        'counts': [item['count'] for item in class_distribution]
    }

    # Пагинация
    page = request.GET.get('page', 1)
    paginator = Paginator(results, 20)  # 20 результатов на страницу
    try:
        detections_page = paginator.page(page)
    except PageNotAnInteger:
        detections_page = paginator.page(1)
    except EmptyPage:
        detections_page = paginator.page(paginator.num_pages)

    context = {
        'dataset': dataset,
        'model': ml_model,
        'detections': detections_page,
        'total_detections': total_detections,
        'detection_stats': {
            'avg_confidence': avg_confidence,
            'max_confidence': max_confidence,
        },
        'unique_labels': unique_labels,
        'class_distribution': json.dumps(class_distribution_data),
    }

    return render(request, 'detection/detection_results.html', context)


@login_required
def model_list(request, dataset_pk):
    """Список ML моделей для датасета"""
    dataset = get_object_or_404(Dataset, pk=dataset_pk, user=request.user)

    # Проверяем, есть ли размеченные данные
    annotated_count = dataset.get_annotated_count()
    can_train = annotated_count >= 3

    ml_models = MLModel.objects.filter(dataset=dataset).order_by('-created_at')

    # Добавляем цвет статуса для отображения в шаблоне
    status_colors = {
        'not_trained': 'secondary',
        'training': 'warning',
        'trained': 'success',
        'error': 'danger'
    }

    for model in ml_models:
        model.status_color = status_colors.get(model.status, 'secondary')

    context = {
        'dataset': dataset,
        'ml_models': ml_models,
        'can_train': can_train,
        'annotated_count': annotated_count,
    }
    return render(request, 'detection/model_list.html', context)


@login_required
@require_POST
def create_model(request, dataset_pk):
    """Создание новой ML модели без немедленного обучения"""
    dataset = get_object_or_404(Dataset, pk=dataset_pk, user=request.user)

    name = request.POST.get('name', f'Модель для {dataset.name}')
    description = request.POST.get('description', '')
    model_type = request.POST.get('model_type', 'yolo')
    epochs = int(request.POST.get('epochs', 50))
    batch_size = int(request.POST.get('batch_size', 16))
    img_size = int(request.POST.get('img_size', 640))

    if not name:
        messages.error(request, 'Название модели обязательно')
        return redirect('detection:model_list', dataset_pk=dataset.pk)

    model = MLModel.objects.create(
        dataset=dataset,
        name=name,
        description=description,
        model_type=model_type,
        epochs=epochs,
        batch_size=batch_size,
        img_size=img_size,
        status='not_trained'
    )

    messages.success(request, f'Модель "{model.name}" успешно создана! Теперь вы можете обучить её.')
    return redirect('model_list', dataset_pk=dataset.pk)


@login_required
@require_POST
def delete_model(request, dataset_pk, model_pk):
    """Удаление ML модели"""
    dataset = get_object_or_404(Dataset, pk=dataset_pk, user=request.user)
    model = get_object_or_404(MLModel, pk=model_pk, dataset=dataset)

    # Удаляем связанные результаты детекции
    DetectionResult.objects.filter(ml_model=model).delete()

    model_name = model.name
    model.delete()

    messages.success(request, f'Модель "{model_name}" успешно удалена!')
    return redirect('model_list', dataset_pk=dataset.pk)


@login_required
def model_detail(request, dataset_pk, model_pk):
    """Детальная информация о ML модели"""
    dataset = get_object_or_404(Dataset, pk=dataset_pk, user=request.user)
    model = get_object_or_404(MLModel, pk=model_pk, dataset=dataset)

    # Статистика детекции
    detection_stats = DetectionResult.objects.filter(
        ml_model=model
    ).aggregate(
        total_detections=models.Count('id'),
        avg_confidence=models.Avg('confidence')
    )

    # Детекции по классам
    detections_by_class = DetectionResult.objects.filter(
        ml_model=model
    ).values('detected_label').annotate(
        count=models.Count('id'),
        avg_confidence=models.Avg('confidence')
    ).order_by('-count')

    # Последние детекции
    recent_detections = DetectionResult.objects.filter(
        ml_model=model
    ).select_related('image').order_by('-created_at')[:10]

    # Проверяем, есть ли активные задачи детекции для этой модели
    # (это упрощенная версия - в реальном приложении нужно хранить task_id в модели)
    detection_in_progress = False
    detection_completed = False
    detection_count = 0

    # Простая проверка: если есть детекции и модель обучена, считаем что детекция была
    if model.status == 'trained' and detection_stats['total_detections'] > 0:
        detection_completed = True
        detection_count = detection_stats['total_detections']

    context = {
        'dataset': dataset,
        'model': model,
        'detection_stats': detection_stats,
        'detections_by_class': detections_by_class,
        'recent_detections': recent_detections,
        'detection_in_progress': detection_in_progress,
        'detection_completed': detection_completed,
        'detection_count': detection_count,
    }
    return render(request, 'detection/model_detail.html', context)




