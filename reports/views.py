import os
import json
import zipfile
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.http import HttpResponse
from django.core.files.base import ContentFile
from io import BytesIO
from dataset.models import Dataset
from detection.models import MLModel, DetectionResult, Annotation
from .models import Report, ReportImage
from .utils import generate_report_file
from django.core.files.temp import NamedTemporaryFile
from django.core.files.base import ContentFile
import io


@login_required
def create_report(request, dataset_pk, model_pk):
    """Создание нового отчета с улучшенной статистикой"""
    dataset = get_object_or_404(Dataset, pk=dataset_pk, user=request.user)
    ml_model = get_object_or_404(MLModel, pk=model_pk, dataset=dataset)

    if request.method == 'POST':
        title = request.POST.get('title', f'Отчет по {dataset.name}')
        format_type = request.POST.get('format', 'pdf')
        include_images = request.POST.get('include_images', False)

        # Собираем расширенную статистику
        total_images = dataset.imagefile_set.count()
        annotated_images = dataset.get_annotated_images_count()
        total_annotations = Annotation.objects.filter(image__dataset=dataset).count()
        total_detections = DetectionResult.objects.filter(dataset=dataset, ml_model=ml_model).count()

        # Детекции с высокой уверенностью
        high_confidence_detections = DetectionResult.objects.filter(
            dataset=dataset,
            ml_model=ml_model,
            confidence__gte=0.75
        )
        high_confidence_count = high_confidence_detections.count()

        # Создаем отчет
        report = Report.objects.create(
            dataset=dataset,
            ml_model=ml_model,
            user=request.user,
            title=title,
            format=format_type,
            total_images=total_images,
            annotated_images=annotated_images,
            total_annotations=total_annotations,
            total_detections=total_detections,
            high_confidence_detections=high_confidence_count,
            accuracy=ml_model.accuracy or 0.0,
            precision=ml_model.precision,
            recall=ml_model.recall,
            f1_score=ml_model.f1_score,
            training_epochs=ml_model.epochs,
            training_batch_size=ml_model.batch_size,
            training_img_size=ml_model.img_size,
            report_file=None
        )

        # Сохраняем изображения с высокой уверенностью
        if include_images and high_confidence_detections.exists():
            for detection in high_confidence_detections[:50]:
                ReportImage.objects.create(
                    report=report,
                    image=detection.image,
                    detection=detection,
                    confidence=detection.confidence,
                    label=detection.detected_label
                )

        # Генерируем файлы отчета
        try:
            # Основной отчет
            buffer, filename, content_type = generate_report_file(report, format_type)
            report.report_file.save(filename, buffer)

            # Архив с изображениями (если нужно)
            if include_images and report.reportimage_set.exists():
                archive_buffer = generate_images_archive(report)
                archive_filename = f"high_confidence_images_{report.id}.zip"
                report.images_archive.save(archive_filename, archive_buffer)

            report.save()
            messages.success(request, f'Отчет "{report.title}" успешно создан!')

        except Exception as e:
            messages.error(request, f'Ошибка при создании файла отчета: {str(e)}')
            report.delete()
            return redirect('model_detail', dataset_pk=dataset.pk, model_pk=ml_model.pk)

        return redirect('reports:report_detail', report_pk=report.pk)

    # Для GET запроса - собираем статистику для отображения
    total_images = dataset.imagefile_set.count()
    annotated_images = dataset.get_annotated_images_count()  # Используем новый метод
    total_annotations = Annotation.objects.filter(image__dataset=dataset).count()
    total_detections = DetectionResult.objects.filter(dataset=dataset, ml_model=ml_model).count()
    high_confidence_count = DetectionResult.objects.filter(
        dataset=dataset,
        ml_model=ml_model,
        confidence__gte=0.75
    ).count()

    context = {
        'dataset': dataset,
        'ml_model': ml_model,
        'total_images': total_images,
        'annotated_images': annotated_images,
        'total_annotations': total_annotations,
        'total_detections': total_detections,
        'high_confidence_count': high_confidence_count,
    }
    return render(request, 'reports/create_report.html', context)





def generate_images_archive(report):
    """Создание архива с изображениями высокой уверенности"""
    buffer = BytesIO()

    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for report_image in report.reportimage_set.all():
            try:
                image_path = report_image.image.image.path
                if os.path.exists(image_path):
                    # Добавляем изображение в архив
                    arcname = f"high_confidence/{report_image.label}_{report_image.confidence:.2f}_{os.path.basename(image_path)}"
                    zip_file.write(image_path, arcname)

                    # Создаем файл с метаданными
                    metadata = {
                        'image': report_image.image.original_filename,
                        'label': report_image.label,
                        'confidence': report_image.confidence,
                        'coordinates': {
                            'x': report_image.detection.x,
                            'y': report_image.detection.y,
                            'width': report_image.detection.width,
                            'height': report_image.detection.height
                        }
                    }

                    metadata_filename = f"metadata/{report_image.label}_{report_image.confidence:.2f}_{report_image.image.id}.json"
                    zip_file.writestr(metadata_filename, json.dumps(metadata, indent=2, ensure_ascii=False))

            except Exception as e:
                print(f"Ошибка обработки изображения {report_image.image.id}: {e}")
                continue

    buffer.seek(0)
    return ContentFile(buffer.getvalue())


@login_required
def download_images_archive(request, report_pk):
    """Скачивание архива с изображениями"""
    report = get_object_or_404(Report, pk=report_pk, user=request.user)

    if report.images_archive:
        file_path = report.images_archive.path
        if os.path.exists(file_path):
            with open(file_path, 'rb') as f:
                response = HttpResponse(f.read(), content_type='application/zip')
                response['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}"'
                return response

    messages.error(request, 'Архив с изображениями не найден.')
    return redirect('reports:report_detail', report_pk=report_pk)


@login_required
def report_list(request, dataset_pk):
    """Список отчетов для датасета"""
    dataset = get_object_or_404(Dataset, pk=dataset_pk, user=request.user)
    reports = Report.objects.filter(dataset=dataset).select_related('ml_model').order_by('-created_at')

    context = {
        'dataset': dataset,
        'reports': reports,
    }
    return render(request, 'reports/report_list.html', context)


@login_required
def report_detail(request, report_pk):
    """Детальная информация об отчете"""
    report = get_object_or_404(Report, pk=report_pk, user=request.user)

    # Получаем изображения с bounding boxes
    high_confidence_images = []
    for report_image in report.reportimage_set.all()[:6]:  # Ограничиваем 6 изображениями
        try:
            # Создаем временный URL для изображения с bbox
            from django.core.files.base import ContentFile
            from django.core.files.storage import default_storage

            bbox_image = create_image_with_bbox(report_image.image, report_image.detection)
            if bbox_image:
                filename = f"bbox_{report_image.image.id}_{report_pk}.jpg"
                file_path = default_storage.save(f'temp/{filename}', bbox_image)
                image_url = default_storage.url(file_path)

                high_confidence_images.append({
                    'url': image_url,
                    'label': report_image.label,
                    'confidence': report_image.confidence,
                    'filename': report_image.image.original_filename
                })
        except Exception as e:
            print(f"Ошибка обработки изображения: {e}")
            continue

    context = {
        'report': report,
        'high_confidence_images': high_confidence_images,
    }
    return render(request, 'reports/report_detail.html', context)

@login_required
@require_POST
def delete_report(request, report_pk):
    """Удаление отчета"""
    report = get_object_or_404(Report, pk=report_pk, user=request.user)
    dataset_pk = report.dataset.pk

    # Удаляем связанные изображения
    ReportImage.objects.filter(report=report).delete()

    report.delete()
    messages.success(request, 'Отчет успешно удален')
    return redirect('reports:report_list', dataset_pk=dataset_pk)


@login_required
def download_report(request, report_pk):
    """Скачивание файла отчета"""
    report = get_object_or_404(Report, pk=report_pk, user=request.user)

    if report.report_file:
        file_path = report.report_file.path
        if os.path.exists(file_path):
            with open(file_path, 'rb') as f:
                response = HttpResponse(f.read(), content_type='application/octet-stream')
                response['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}"'
                return response

    messages.error(request, 'Файл отчета не найден.')
    return redirect('reports:report_detail', report_pk=report_pk)



def create_image_with_bbox(image_file, detection):
    """Создает изображение с bounding box для отображения в HTML"""
    try:
        from PIL import Image, ImageDraw
        import os
        import io
        from django.core.files.base import ContentFile

        # Открываем оригинальное изображение
        img_path = image_file.image.path
        original_img = Image.open(img_path)

        # Создаем копию для рисования
        img_with_bbox = original_img.copy()
        draw = ImageDraw.Draw(img_with_bbox)

        # Получаем размеры изображения
        img_width, img_height = original_img.size

        # Получаем координаты bounding box в пикселях
        # Предполагаем, что координаты в detection нормализованы (0-1)
        x1 = int(detection.x * img_width)
        y1 = int(detection.y * img_height)
        x2 = int((detection.x + detection.width) * img_width)
        y2 = int((detection.y + detection.height) * img_height)

        # Ограничиваем координаты размерами изображения
        x1 = max(0, min(x1, img_width - 1))
        y1 = max(0, min(y1, img_height - 1))
        x2 = max(0, min(x2, img_width))
        y2 = max(0, min(y2, img_height))

        # Рисуем bounding box
        draw.rectangle([x1, y1, x2, y2], outline='red', width=3)

        # Создаем текст для подписи (без кириллицы для избежания ошибок кодировки)
        label_text = f"{detection.detected_label[:10]} {detection.confidence:.1%}"

        # Рисуем фон для подписи
        text_width = len(label_text) * 8  # Примерная ширина текста
        text_height = 20
        text_x = x1
        text_y = max(y1 - text_height - 5, 0)

        draw.rectangle([text_x, text_y, text_x + text_width, text_y + text_height], fill='red')

        # Рисуем текст (используем только ASCII символы для избежания ошибок)
        try:
            # Пытаемся использовать простой текст
            draw.text((text_x + 2, text_y + 2), label_text, fill='white')
        except Exception as text_error:
            print(f"Ошибка рисования текста: {text_error}")
            # Если не получается, рисуем без текста
            pass

        # Сохраняем в буфер
        buffer = io.BytesIO()
        img_with_bbox.save(buffer, format='JPEG', quality=85)
        buffer.seek(0)

        return ContentFile(buffer.getvalue())

    except Exception as e:
        print(f"Ошибка создания изображения с bbox: {e}")
        import traceback
        print(f"Подробности: {traceback.format_exc()}")
        return None


