from django import forms
from .models import StudentPreferences


class StudentPreferencesForm(forms.ModelForm):
    # Academic Information
    major_field_of_study = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'пр., Компјутерски науки'
        }),
        label='Главно поле на студирање',
        max_length=256,
        required=False
    )
    
    current_courses = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'пр., Структури на податоци, Калкулус 2'
        }),
        label='Тековни курсеви',
        required=False
    )
    
    # Study Preferences
    LEARNING_STYLE_CHOICES = [
        ('visual', 'Визуелно (учење преку гледање)'),
        ('auditory', 'Аудитивно (учење преку слушање)'),
        ('kinesthetic', 'Кинестетичко (учење преку правење)'),
        ('reading_writing', 'Читање/Пишување (учење преку текст)'),
    ]
    
    preferred_learning_style = forms.ChoiceField(
        choices=LEARNING_STYLE_CHOICES,
        widget=forms.RadioSelect(attrs={
            'class': 'form-check-input'
        }),
        label='Преферирани стил на учење',
        required=False
    )
    
    daily_study_hours = forms.FloatField(
        widget=forms.NumberInput(attrs={
            'class': 'form-range',
            'type': 'range',
            'min': '1',
            'max': '12',
            'step': '0.5',
            'value': '4'
        }),
        label='Дневни часови на учење: 4 часа',
        initial=4.0,
        required=False
    )
    
    # Learning Goals
    learning_goals = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'placeholder': 'пр., Подобрување на оценките за 10%, учење нов програмски јазик',
            'rows': 3
        }),
        label='Цели за учење',
        required=False
    )

    class Meta:
        model = StudentPreferences
        fields = [
            'major_field_of_study', 
            'current_courses', 
            'preferred_learning_style',
            'daily_study_hours',
            'learning_goals'
        ]
