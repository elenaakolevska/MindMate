from django import forms
from .models import Student


class StudentRegistrationForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Создајте силна лозинка'
        }),
        label='Лозинка'
    )
    password_confirm = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Потврдете ја лозинката'
        }),
        label='Потврди лозинка'
    )
    
    # Choices for education level in Macedonian
    EDUCATION_CHOICES = [
        ('', 'Изберете го вашето највисоко образование'),
        ('high_school', 'Средно образование'),
        ('college', 'Факултет'),
    ]
    
    # Study fields in Macedonian
    STUDY_FIELD_CHOICES = [
        ('', 'Изберете го вашето главно поле на студирање'),
        ('mathematics', 'Математика'),
        ('computer_science', 'Компјутерски науки'),
        ('engineering', 'Инженерство'),
        ('medicine', 'Медицина'),
        ('law', 'Право'),
        ('economics', 'Економија'),
        ('psychology', 'Психологија'),
        ('biology', 'Биологија'),
        ('chemistry', 'Хемија'),
        ('physics', 'Физика'),
        ('history', 'Историја'),
        ('literature', 'Литература'),
        ('philosophy', 'Филозофија'),
        ('art', 'Уметност'),
        ('music', 'Музика'),
        ('other', 'Друго'),
    ]
    
    # Interest choices in Macedonian
    INTEREST_CHOICES = [
        ('productivity', 'Продуктивност'),
        ('time_management', 'Управување со време'),
        ('mindfulness', 'Свесност'),
        ('coding', 'Програмирање'),
        ('reading', 'Читање'),
        ('writing', 'Пишување'),
        ('research', 'Истражување'),
        ('project_planning', 'Планирање проекти'),
        ('skill_development', 'Развој на вештини'),
        ('language_learning', 'Учење јазици'),
        ('exam_prep', 'Подготовка за испити'),
        ('note_taking', 'Водење белешки'),
    ]
    
    full_name = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Вашето полно име'
        }),
        label='Полно име',
        max_length=128
    )
    
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'your.email@example.com'
        }),
        label='Е-пошта'
    )
    
    study_level = forms.ChoiceField(
        choices=EDUCATION_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        label='Ниво на образование'
    )
    
    study_direction = forms.ChoiceField(
        choices=STUDY_FIELD_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        label='Поле на студирање'
    )
    
    interests = forms.MultipleChoiceField(
        choices=INTEREST_CHOICES,
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-check-input'
        }),
        label='Изберете ги вашите интереси (максимум 5)',
        required=False
    )
    
    terms_agreed = forms.BooleanField(
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label='Се согласувам со условите и правилата',
        required=True
    )

    class Meta:
        model = Student
        fields = ['full_name', 'email', 'study_level', 'study_direction', 'interests']

    def clean_password_confirm(self):
        password = self.cleaned_data.get('password')
        password_confirm = self.cleaned_data.get('password_confirm')
        
        if password and password_confirm and password != password_confirm:
            raise forms.ValidationError('Лозинките не се совпаѓаат.')
        
        return password_confirm

    def clean_interests(self):
        interests = self.cleaned_data.get('interests')
        if interests and len(interests) > 5:
            raise forms.ValidationError('Можете да изберете максимум 5 интереси.')
        return interests

    def save(self, commit=True):
        student = super().save(commit=False)
        # Convert interests list to string
        if self.cleaned_data.get('interests'):
            student.interests = ', '.join(self.cleaned_data.get('interests'))
        
        # Set password (in a real app, you'd want to hash this)
        student.password = self.cleaned_data.get('password')
        
        if commit:
            student.save()
        return student
