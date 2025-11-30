from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from .models import Dataset, ImageFile, PDFFile
from .forms import DatasetForm, ImageUploadForm, PDFUploadForm


@login_required
def dataset_list(request):
    """Список датасетов пользователя"""
    datasets = Dataset.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'dataset/dataset_list.html', {'datasets': datasets})


@login_required
def dataset_create(request):
    """Создание нового датасета"""
    if request.method == 'POST':
        form = DatasetForm(request.POST)
        if form.is_valid():
            dataset = form.save(commit=False)
            dataset.user = request.user
            dataset.save()
            messages.success(request, f'Датасет "{dataset.name}" успешно создан!')
            return redirect('dataset_upload', pk=dataset.pk)
    else:
        form = DatasetForm()

    return render(request, 'dataset/dataset_create.html', {'form': form})


@login_required
def dataset_detail(request, pk):
    """Детальная информация о датасете"""
    dataset = get_object_or_404(Dataset, pk=pk, user=request.user)
    images = dataset.imagefile_set.all()
    pdf_files = dataset.pdffile_set.all()

    context = {
        'dataset': dataset,
        'images': images,
        'pdf_files': pdf_files,
        'image_count': images.count(),
        'annotated_count': images.filter(is_annotated=True).count(),
    }
    return render(request, 'dataset/dataset_detail.html', context)


@login_required
def dataset_upload(request, pk):
    """Загрузка файлов в датасет"""
    dataset = get_object_or_404(Dataset, pk=pk, user=request.user)

    image_form = ImageUploadForm()
    pdf_form = PDFUploadForm()

    if request.method == 'POST':
        # Обработка загрузки изображений
        if 'images' in request.FILES:
            image_form = ImageUploadForm(request.POST, request.FILES)
            if image_form.is_valid():
                images = request.FILES.getlist('images')
                successful_uploads = 0

                for image in images:
                    try:
                        ImageFile.objects.create(
                            dataset=dataset,
                            image=image,
                            original_filename=image.name
                        )
                        successful_uploads += 1
                    except Exception as e:
                        messages.error(request, f'Ошибка при загрузке {image.name}: {str(e)}')

                if successful_uploads > 0:
                    messages.success(request, f'Успешно загружено {successful_uploads} изображений')
                    dataset.status = 'uploading'
                    dataset.save()

        # Обработка загрузки PDF
        if 'pdf_files' in request.FILES:
            pdf_form = PDFUploadForm(request.POST, request.FILES)
            if pdf_form.is_valid():
                pdf_files = request.FILES.getlist('pdf_files')
                successful_uploads = 0

                for pdf in pdf_files:
                    try:
                        PDFFile.objects.create(
                            dataset=dataset,
                            pdf=pdf,
                            original_filename=pdf.name
                        )
                        successful_uploads += 1
                    except Exception as e:
                        messages.error(request, f'Ошибка при загрузке {pdf.name}: {str(e)}')

                if successful_uploads > 0:
                    messages.success(request, f'Успешно загружено {successful_uploads} PDF файлов')
                    dataset.status = 'uploading'
                    dataset.save()

        return redirect('dataset_detail', pk=dataset.pk)

    context = {
        'dataset': dataset,
        'image_form': image_form,
        'pdf_form': pdf_form,
    }
    return render(request, 'dataset/dataset_upload.html', context)

@login_required
@require_POST
def dataset_delete(request, pk):
    """Удаление датасета"""
    dataset = get_object_or_404(Dataset, pk=pk, user=request.user)
    dataset_name = dataset.name
    dataset.delete()
    messages.success(request, f'Датасет "{dataset_name}" успешно удален')
    return redirect('dataset_list')


@login_required
@require_POST
def delete_image(request, pk):
    """Удаление изображения"""
    image = get_object_or_404(ImageFile, pk=pk, dataset__user=request.user)
    dataset_pk = image.dataset.pk
    image.delete()
    messages.success(request, 'Изображение удалено')
    return redirect('dataset_detail', pk=dataset_pk)


@login_required
@require_POST
def delete_pdf(request, pk):
    """Удаление PDF файла"""
    pdf = get_object_or_404(PDFFile, pk=pk, dataset__user=request.user)
    dataset_pk = pdf.dataset.pk
    pdf.delete()
    messages.success(request, 'PDF файл удален')
    return redirect('dataset_detail', pk=dataset_pk)