from django import forms
from .models import Student


class StudentLoginForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Внесете ја вашата е-пошта'
        }),
        label='Е-пошта'
    )
    
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Внесете ја вашата лозинка'
        }),
        label='Лозинка'
    )
    
    remember_me = forms.BooleanField(
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label='Запомни ме 30 дена',
        required=False
    )

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        password = cleaned_data.get('password')
        
        if email and password:
            try:
                student = Student.objects.get(email=email)
                if student.password != password:  # In real app, use hashed passwords
                    raise forms.ValidationError('Неточна лозинка.')
                cleaned_data['student'] = student
            except Student.DoesNotExist:
                raise forms.ValidationError('Не постои корисник со таа е-пошта.')
        
        return cleaned_data
