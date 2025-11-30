from django import forms
from .models import Report


class ReportForm(forms.ModelForm):
    include_images = forms.BooleanField(
        required=False,
        initial=True,
        label='Включить изображения с высокой уверенностью (>75%)',
        help_text='Будет создан дополнительный архив с изображениями высокой уверенности'
    )

    class Meta:
        model = Report
        fields = ['title', 'format']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Введите название отчета'}),
            'format': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'title': 'Название отчета',
            'format': 'Формат отчета',
        }
        help_texts = {
            'title': 'Укажите понятное название отчета',
            'format': 'Выберите формат файла отчета',
        }