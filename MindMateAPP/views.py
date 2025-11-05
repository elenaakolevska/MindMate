from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from .forms import StudentRegistrationForm
from .preference_forms import StudentPreferencesForm
from .login_forms import StudentLoginForm
from .models import Student, StudentPreferences


def register(request):
    if request.method == 'POST':
        form = StudentRegistrationForm(request.POST)
        if form.is_valid():
            try:
                student = form.save()
                # Store student ID in session for preferences form
                request.session['student_id'] = student.id
                messages.success(request, 'Успешно се регистриравте! Сега персонализирајте го вашето искуство.')
                return redirect('mindmate:student_preferences')
            except Exception as e:
                messages.error(request, 'Се случи грешка при регистрацијата. Обидете се повторно.')
                return render(request, 'registration/register.html', {'form': form})
        else:
            # Form has errors - display them
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{error}')
            return render(request, 'registration/register.html', {'form': form})
    else:
        form = StudentRegistrationForm()
    
    return render(request, 'registration/register.html', {'form': form})


def registration_success(request):
    return render(request, 'registration/success.html')


def student_preferences(request):
    # Get student from session
    student_id = request.session.get('student_id')
    if not student_id:
        messages.error(request, 'Сесијата истече. Ве молиме регистрирајте се повторно.')
        return redirect('mindmate:register')
    
    student = get_object_or_404(Student, id=student_id)
    
    if request.method == 'POST':
        form = StudentPreferencesForm(request.POST)
        if form.is_valid():
            try:
                preferences = form.save(commit=False)
                preferences.student = student
                preferences.save()
                
                # Clear session
                if 'student_id' in request.session:
                    del request.session['student_id']
                
                messages.success(request, 'Вашите преференци се успешно зачувани!')
                return redirect('mindmate:home')
            except Exception as e:
                messages.error(request, 'Се случи грешка при зачувување на преференците.')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{error}')
    else:
        form = StudentPreferencesForm()
    
    return render(request, 'registration/preferences.html', {'form': form, 'student': student})


def home(request):
    return render(request, 'home.html')


def login(request):
    if request.method == 'POST':
        form = StudentLoginForm(request.POST)
        if form.is_valid():
            try:
                student = form.cleaned_data['student']
                # Store student info in session
                request.session['logged_in_student_id'] = student.id
                request.session['logged_in_student_name'] = student.full_name
                
                # Handle remember me
                if form.cleaned_data.get('remember_me'):
                    request.session.set_expiry(30 * 24 * 60 * 60)  # 30 days
                else:
                    request.session.set_expiry(0)  # Browser session
                
                messages.success(request, f'Добредојдовте, {student.full_name}!')
                return redirect('mindmate:home')
            except Exception as e:
                messages.error(request, 'Се случи грешка при најава. Обидете се повторно.')
        else:
            for error in form.non_field_errors():
                messages.error(request, error)
    else:
        form = StudentLoginForm()
    
    return render(request, 'auth/login.html', {'form': form})
