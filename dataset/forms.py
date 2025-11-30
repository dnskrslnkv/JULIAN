from django import forms
from .models import Dataset, ImageFile, PDFFile
from django.core.validators import FileExtensionValidator

class DatasetForm(forms.ModelForm):
    class Meta:
        model = Dataset
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Введите название датасета'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Опишите ваш датасет (необязательно)'
            }),
        }
        labels = {
            'name': 'Название датасета',
            'description': 'Описание',
        }

class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = single_file_clean(data, initial)
        return result

class ImageUploadForm(forms.Form):
    images = MultipleFileField(
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'bmp', 'gif'])],
        label='Выберите изображения',
        help_text='Можно выбрать несколько файлов. Поддерживаемые форматы: JPG, PNG, JPEG, BMP, GIF'
    )

class PDFUploadForm(forms.Form):
    pdf_files = MultipleFileField(
        validators=[FileExtensionValidator(allowed_extensions=['pdf'])],
        label='Выберите PDF файлы',
        help_text='Можно выбрать несколько PDF файлов'
    )