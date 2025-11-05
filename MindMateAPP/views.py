from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .forms import StudentRegistrationForm
from .preference_forms import StudentPreferencesForm
from .login_forms import StudentLoginForm
from .models import Student, StudentPreferences


def register(request):
    # Clear any existing messages when showing the registration form (both authenticated and non-authenticated)
    if request.method == 'GET':
        storage = messages.get_messages(request)
        for message in storage:
            pass  # This consumes/clears the messages
    
    # Check if user is already authenticated
    if request.user.is_authenticated:
        return render(request, 'registration/register.html')  # Show template with auth check
    
    if request.method == 'POST':
        form = StudentRegistrationForm(request.POST)
        if form.is_valid():
            try:
                # Create Django User
                user = User.objects.create_user(
                    username=form.cleaned_data['email'],
                    email=form.cleaned_data['email'],
                    password=form.cleaned_data['password'],
                    first_name=form.cleaned_data['full_name'].split()[0] if form.cleaned_data['full_name'] else '',
                    last_name=' '.join(form.cleaned_data['full_name'].split()[1:]) if len(form.cleaned_data['full_name'].split()) > 1 else ''
                )
                
                # Create Student profile
                student = form.save(commit=False)
                student.user = user  # Link to Django User
                student.save()
                
                # Log the user in
                auth_login(request, user)
                
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


@login_required
def student_preferences(request):
    # Get student from logged-in user
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        messages.error(request, 'Студентскиот профил не е пронајден. Ве молиме регистрирајте се повторно.')
        return redirect('mindmate:register')
    
    if request.method == 'POST':
        form = StudentPreferencesForm(request.POST)
        if form.is_valid():
            try:
                preferences = form.save(commit=False)
                preferences.student = student
                preferences.save()
                
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

def login(request):
    if request.user.is_authenticated:
        return redirect('mindmate:home')
    
    # Clear any existing messages when showing the login form
    if request.method == 'GET':
        storage = messages.get_messages(request)
        for message in storage:
            pass  # This consumes/clears the messages
    
    if request.method == 'POST':
        form = StudentLoginForm(request.POST)
        if form.is_valid():
            try:
                # Authenticate using Django's auth system
                user = authenticate(
                    request, 
                    username=form.cleaned_data['email'], 
                    password=form.cleaned_data['password']
                )
                
                if user is not None:
                    auth_login(request, user)
                    
                    # Get student name for welcome message
                    try:
                        student = Student.objects.get(user=user)
                        student_name = student.full_name
                    except Student.DoesNotExist:
                        student_name = user.first_name or user.username
                    
                    messages.success(request, f'Добредојдовте, {student_name}!')
                    return redirect('mindmate:home')
                else:
                    messages.error(request, 'Неточна е-пошта или лозинка.')
            except Exception as e:
                messages.error(request, 'Се случи грешка при најава. Обидете се повторно.')
        else:
            for error in form.non_field_errors():
                messages.error(request, error)
    else:
        form = StudentLoginForm()
    
    return render(request, 'auth/login.html', {'form': form})

def home(request):
    # Clear any existing messages when showing the home page
    if request.method == 'GET':
        storage = messages.get_messages(request)
        for message in storage:
            pass  # This consumes/clears the messages
    # Don't redirect authenticated users - let them see the home page
    return render(request, 'home.html')

def logout(request):
    auth_logout(request)
    # Don't add success message to avoid it showing on other pages
    return redirect('mindmate:home')
