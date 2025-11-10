# MindMateAPP/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from datetime import datetime, timedelta
from .forms import StudentRegistrationForm
from .preference_forms import StudentPreferencesForm
from .login_forms import StudentLoginForm
from .models import (
    Student, StudentPreferences, CalendarEvent, Progress, Streak,
    Accuracy, Badge, Quiz, QuizResult, StudyMaterial, ChatbotInteraction,
    Notification
)


def register(request):
    if request.method == 'GET':
        storage = messages.get_messages(request)
        for message in storage:
            pass

    if request.user.is_authenticated:
        return render(request, 'registration/register.html')

    if request.method == 'POST':
        form = StudentRegistrationForm(request.POST)
        if form.is_valid():
            try:
                user = User.objects.create_user(
                    username=form.cleaned_data['email'],
                    email=form.cleaned_data['email'],
                    password=form.cleaned_data['password'],
                    first_name=form.cleaned_data['full_name'].split()[0] if form.cleaned_data['full_name'] else '',
                    last_name=' '.join(form.cleaned_data['full_name'].split()[1:]) if len(
                        form.cleaned_data['full_name'].split()) > 1 else ''
                )

                student = form.save(commit=False)
                student.user = user
                student.save()

                auth_login(request, user)

                messages.success(request, 'Успешно се регистриравте! Сега персонализирајте го вашето искуство.')
                return redirect('mindmate:student_preferences')
            except Exception as e:
                messages.error(request, 'Се случи грешка при регистрацијата. Обидете се повторно.')
                return render(request, 'registration/register.html', {'form': form})
        else:
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
                return redirect('mindmate:dashboard')
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
        return redirect('mindmate:dashboard')

    if request.method == 'GET':
        storage = messages.get_messages(request)
        for message in storage:
            pass

    if request.method == 'POST':
        form = StudentLoginForm(request.POST)
        if form.is_valid():
            try:
                user = authenticate(
                    request,
                    username=form.cleaned_data['email'],
                    password=form.cleaned_data['password']
                )

                if user is not None:
                    auth_login(request, user)

                    try:
                        student = Student.objects.get(user=user)
                        student_name = student.full_name
                    except Student.DoesNotExist:
                        student_name = user.first_name or user.username

                    messages.success(request, f'Добредојдовте, {student_name}!')
                    return redirect('mindmate:dashboard')
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
    if request.method == 'GET':
        storage = messages.get_messages(request)
        for message in storage:
            pass
    return render(request, 'home.html')


def logout(request):
    auth_logout(request)
    return redirect('mindmate:home')


@login_required
def dashboard(request):
    """Main dashboard view with all user data"""
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        messages.error(request, 'Студентскиот профил не е пронајден.')
        return redirect('mindmate:register')

    # Get or create student preferences
    preferences, created = StudentPreferences.objects.get_or_create(student=student)

    # Get or create progress
    progress, created = Progress.objects.get_or_create(
        student=student,
        defaults={'progress_bar': 0.0, 'completed_tasks': 0}
    )

    # Get or create streak
    streak, created = Streak.objects.get_or_create(
        progress=progress,
        defaults={'days_count': 0, 'last_day': timezone.now().date()}
    )

    # Calculate current streak
    today = timezone.now().date()
    if streak.last_day < today - timedelta(days=1):
        # Streak broken
        streak.days_count = 0
        streak.save()

    # Get accuracy
    try:
        accuracy = Accuracy.objects.filter(progress=progress).latest('id')
        accuracy_percentage = accuracy.percentage
    except Accuracy.DoesNotExist:
        accuracy_percentage = 0.0

    # Get quiz results
    quiz_results = QuizResult.objects.filter(student=student).order_by('-taken_at')[:5]
    completed_quizzes = QuizResult.objects.filter(student=student).count()

    # Calculate average accuracy from quiz results
    if quiz_results.exists():
        total_accuracy = sum([result.accuracy_percentage for result in quiz_results])
        accuracy_percentage = total_accuracy / len(quiz_results)

    # Get badges
    badges = Badge.objects.filter(student=student).order_by('-received_at')[:5]

    # Get recent activity (last 10 items)
    recent_activities = []

    # Add quiz completions
    for result in quiz_results[:3]:
        recent_activities.append({
            'icon': 'fa-check-circle',
            'text': f'Completed Quiz: {result.quiz.subject}',
            'time': result.taken_at,
            'type': 'quiz'
        })

    # Add uploaded materials
    materials = StudyMaterial.objects.filter(student=student).order_by('-upload_date')[:3]
    for material in materials:
        recent_activities.append({
            'icon': 'fa-file-alt',
            'text': f'Uploaded Document: {material.title or material.original_filename}',
            'time': material.upload_date,
            'type': 'upload'
        })

    # Add calendar events
    events = CalendarEvent.objects.filter(student=student).order_by('-date_time')[:2]
    for event in events:
        recent_activities.append({
            'icon': 'fa-calendar-alt',
            'text': f'Scheduled: {event.title}',
            'time': event.date_time,
            'type': 'event'
        })

    # Add chatbot interactions
    interactions = ChatbotInteraction.objects.filter(student=student).order_by('-action_time')[:2]
    for interaction in interactions:
        recent_activities.append({
            'icon': 'fa-question',
            'text': f'Asked: {interaction.event_action}',
            'time': interaction.action_time,
            'type': 'chat'
        })

    # Sort activities by time
    recent_activities.sort(key=lambda x: x['time'], reverse=True)
    recent_activities = recent_activities[:10]

    # Get upcoming events
    upcoming_events = CalendarEvent.objects.filter(
        student=student,
        date_time__gte=timezone.now()
    ).order_by('date_time')[:5]

    # Get student interests
    interests = student.interests.split(', ') if student.interests else []

    context = {
        'student': student,
        'preferences': preferences,
        'streak_days': streak.days_count,
        'accuracy_percentage': round(accuracy_percentage, 1),
        'completed_quizzes': completed_quizzes,
        'badges': badges,
        'recent_activities': recent_activities,
        'upcoming_events': upcoming_events,
        'interests': interests[:3],  # Show first 3 interests
        'progress': progress,
    }

    return render(request, 'dashboard/dashboard.html', context)


@login_required
def upload_document(request):
    """Handle document upload via AJAX"""
    if request.method == 'POST' and request.FILES:
        try:
            student = Student.objects.get(user=request.user)
            uploaded_file = request.FILES['file']

            # Determine file type
            file_extension = uploaded_file.name.split('.')[-1].lower()
            file_type_map = {
                'pdf': 'pdf',
                'doc': 'word',
                'docx': 'word',
                'txt': 'text',
                'jpg': 'image',
                'jpeg': 'image',
                'png': 'image'
            }
            file_type = file_type_map.get(file_extension, 'text')

            # Create study material
            material = StudyMaterial.objects.create(
                student=student,
                type=file_type,
                title=uploaded_file.name,
                original_filename=uploaded_file.name,
                file_path=f'uploads/{uploaded_file.name}',
                content='',  # TODO: Extract text content using OCR
                subject=''  # TODO: Classify subject using AI
            )

            return JsonResponse({
                'success': True,
                'message': 'Document uploaded successfully',
                'material_id': material.id
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=400)

    return JsonResponse({'success': False, 'message': 'Invalid request'}, status=400)