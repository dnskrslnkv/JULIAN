from django import forms
from .models import Annotation


class AnnotationForm(forms.ModelForm):
    class Meta:
        model = Annotation
        fields = ['label', 'x', 'y', 'width', 'height']
        widgets = {
            'x': forms.HiddenInput(attrs={'id': 'annotation-x'}),
            'y': forms.HiddenInput(attrs={'id': 'annotation-y'}),
            'width': forms.HiddenInput(attrs={'id': 'annotation-width'}),
            'height': forms.HiddenInput(attrs={'id': 'annotation-height'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'label' in self.fields:
            del self.fields['label']


class AnnotationSettingsForm(forms.Form):
    LABEL_CHOICES = [
        ('object', 'Объект'),
        ('defect', 'Дефект'),
        ('animal', 'Животное'),
        ('person', 'Человек'),
        ('vehicle', 'Транспорт'),
        ('other', 'Другое'),
    ]

    default_label = forms.ChoiceField(
        choices=LABEL_CHOICES,
        label='Метка по умолчанию',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    show_grid = forms.BooleanField(
        required=False,
        initial=True,
        label='Показывать сетку',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    auto_save = forms.BooleanField(
        required=False,
        initial=True,
        label='Автосохранение',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )