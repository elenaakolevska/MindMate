# MindMateAPP/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from datetime import datetime, timedelta
import json
import logging

logger = logging.getLogger(__name__)
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from datetime import datetime, timedelta
import json
from .forms import StudentRegistrationForm
from .preference_forms import StudentPreferencesForm
from .login_forms import StudentLoginForm
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import os
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

            # Validate file size (50MB limit)
            if uploaded_file.size > 50 * 1024 * 1024:
                return JsonResponse({
                    'success': False,
                    'message': 'File size exceeds 50MB limit'
                }, status=400)

            # Determine file type
            file_extension = uploaded_file.name.split('.')[-1].lower()
            file_type_map = {
                'pdf': 'pdf',
                'doc': 'word',
                'docx': 'word',
                'txt': 'text',
                'jpg': 'image',
                'jpeg': 'image',
                'png': 'image',
                'ppt': 'presentation',
                'pptx': 'presentation'
            }
            file_type = file_type_map.get(file_extension, 'text')

            # Create uploads directory if it doesn't exist
            import os
            from django.conf import settings
            upload_dir = os.path.join(settings.MEDIA_ROOT, 'uploads', str(student.id))
            os.makedirs(upload_dir, exist_ok=True)

            # Save file to disk
            file_path = os.path.join(upload_dir, uploaded_file.name)
            with open(file_path, 'wb+') as destination:
                for chunk in uploaded_file.chunks():
                    destination.write(chunk)

            # Create study material
            material = StudyMaterial.objects.create(
                student=student,
                type=file_type,
                title=uploaded_file.name.rsplit('.', 1)[0],  # Remove extension from title
                original_filename=uploaded_file.name,
                file_path=f'uploads/{student.id}/{uploaded_file.name}',
                content='',  # TODO: Extract text content using OCR
                subject='',  # TODO: Classify subject using AI
                processing_status='pending'
            )

            # TODO: Queue OCR processing task here
            # process_document_async.delay(material.id)

            return JsonResponse({
                'success': True,
                'message': 'Document uploaded successfully',
                'material_id': material.id,
                'file_name': uploaded_file.name,
                'file_size': uploaded_file.size,
                'file_type': file_type
            })
        except Exception as e:
            import traceback
            logger.error(f"Document upload error: {e}")
            logger.error(traceback.format_exc())
            return JsonResponse({
                'success': False,
                'message': f'Upload failed: {str(e)}'
            }, status=500)

    return JsonResponse({'success': False, 'message': 'Invalid request'}, status=400)


@login_required
def calendar_view(request):
    """Display the calendar page"""
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        messages.error(request, 'Student profile not found.')
        return redirect('mindmate:register')

    context = {
        'student': student,
    }
    
    return render(request, 'calendar/index.html', context)


@login_required
def api_events(request):
    """
    API endpoint for calendar events
    GET: Fetch events for date range
    POST: Create new event
    """
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Student not found'}, status=404)

    if request.method == 'GET':
        # Get query parameters for date filtering
        start_date = request.GET.get('start')
        end_date = request.GET.get('end')
        
        # Base query for student's events
        events = CalendarEvent.objects.filter(student=student)
        
        # Apply date filtering if provided
        if start_date:
            try:
                start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                events = events.filter(date_time__gte=start_dt)
            except ValueError:
                pass
        
        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                events = events.filter(date_time__lte=end_dt)
            except ValueError:
                pass
        
        # Convert events to FullCalendar format
        event_list = []
        for event in events:
            event_data = {
                'id': event.id,
                'title': event.title,
                'start': event.date_time.strftime('%Y-%m-%dT%H:%M:%S'),
                'allDay': False,  # Explicitly set to false for timed events
                'description': event.description,
                'backgroundColor': event.color,
                'borderColor': event.color,
                'textColor': '#ffffff',  # White text for better contrast
                'display': 'block',  # Ensure full block display
                'extendedProps': {
                    'event_type': event.event_type,
                    'description': event.description
                }
            }
            
            # Add end time if available (for multi-hour events)
            if event.end_time:
                event_data['end'] = event.end_time.strftime('%Y-%m-%dT%H:%M:%S')
            # If no end time is set, don't add an end property (FullCalendar will handle it as all-day or timed event)
                
            event_list.append(event_data)
        
        return JsonResponse(event_list, safe=False)
    
    elif request.method == 'POST':
        try:
            # Parse JSON data
            data = json.loads(request.body)
            
            # Validate required fields
            title = data.get('title', '').strip()
            start = data.get('start')
            end = data.get('end')

            if not title:
                return JsonResponse({'success': False, 'message': 'Title is required'}, status=400)
            
            if not start:
                return JsonResponse({'success': False, 'message': 'Start date is required'}, status=400)
            
            # Parse start datetime
            try:
                # Handle both datetime-local format and ISO format
                if 'T' in start and len(start) == 16:  # datetime-local format YYYY-MM-DDTHH:MM
                    start_dt = datetime.strptime(start, '%Y-%m-%dT%H:%M')
                else:
                    start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
            except Exception:
                return JsonResponse({'success': False, 'message': 'Invalid start date format'}, status=400)
            
            end_dt = None
            if end:
                try:
                    if 'T' in end and len(end) == 16:
                        end_dt = datetime.strptime(end, '%Y-%m-%dT%H:%M')
                    else:
                        end_dt = datetime.fromisoformat(end.replace('Z', '+00:00'))
                except Exception:
                    return JsonResponse({'success': False, 'message': 'Invalid end date format'}, status=400)

            # If no end time, treat as 1 hour event for overlap check
            if not end_dt:
                end_dt = start_dt + timedelta(hours=1)

            # Overlap validation: check if any event for this student overlaps with the new event
            overlap_qs = CalendarEvent.objects.filter(
                student=student,
                date_time__lt=end_dt,
                end_time__gt=start_dt
            )
            if overlap_qs.exists():
                return JsonResponse({'success': False, 'message': 'Веќе постои настан закажан во истото време.'}, status=400)

            # Create the event
            event = CalendarEvent.objects.create(
                student=student,
                title=title,
                date_time=start_dt,
                end_time=end_dt,
                event_type=data.get('event_type', 'personal'),
                description=data.get('description', ''),
                notes=data.get('notes', '')
            )
            
            return JsonResponse({
                'success': True,
                'message': 'Event created successfully',
                'event': {
                    'id': event.id,
                    'title': event.title,
                    'start': event.date_time.isoformat(),
                    'description': event.description,
                }
            })
            
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'message': 'Invalid JSON data'}, status=400)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)


@login_required
def api_event_detail(request, event_id):
    """
    API endpoint for individual event operations
    PUT: Update event
    DELETE: Delete event
    """
    try:
        student = Student.objects.get(user=request.user)
        event = get_object_or_404(CalendarEvent, id=event_id, student=student)
    except Student.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Student not found'}, status=404)

    if request.method == 'PUT':
        try:
            # Parse JSON data
            data = json.loads(request.body)
            
            # Update event fields if provided
            if 'title' in data:
                title = data['title'].strip()
                if title:
                    event.title = title
                else:
                    return JsonResponse({'success': False, 'message': 'Title cannot be empty'}, status=400)
            
            if 'start' in data:
                try:
                    start = data['start']
                    # Handle both datetime-local format and ISO format
                    if 'T' in start and len(start) == 16:  # datetime-local format YYYY-MM-DDTHH:MM
                        start_dt = datetime.strptime(start, '%Y-%m-%dT%H:%M')
                    else:
                        start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                    
                    # Make timezone aware
                    if timezone.is_naive(start_dt):
                        start_dt = timezone.make_aware(start_dt)
                        
                    event.date_time = start_dt
                except ValueError:
                    return JsonResponse({'success': False, 'message': 'Invalid start date format'}, status=400)
            
            if 'end' in data:
                end = data['end']
                if end:
                    try:
                        # Handle both datetime-local format and ISO format
                        if 'T' in end and len(end) == 16:  # datetime-local format YYYY-MM-DDTHH:MM
                            end_dt = datetime.strptime(end, '%Y-%m-%dT%H:%M')
                        else:
                            end_dt = datetime.fromisoformat(end.replace('Z', '+00:00'))
                        
                        # Make timezone aware
                        if timezone.is_naive(end_dt):
                            end_dt = timezone.make_aware(end_dt)
                            
                        event.end_time = end_dt
                    except ValueError:
                        pass  # If end date is invalid, just ignore it
                else:
                    event.end_time = None
            
            if 'description' in data:
                event.description = data['description']
            
            if 'notes' in data:
                event.notes = data['notes']
                
            if 'event_type' in data:
                event.event_type = data['event_type']
            
            # Save changes
            event.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Event updated successfully',
                'event': {
                    'id': event.id,
                    'title': event.title,
                    'start': event.date_time.isoformat(),
                    'description': event.description,
                }
            })
            
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'message': 'Invalid JSON data'}, status=400)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)
    
    elif request.method == 'DELETE':
        try:
            event.delete()
            return JsonResponse({'success': True, 'message': 'Event deleted successfully'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)


@login_required
def study_agent_view(request):
    """Display the Study Agent interface"""
    try:
        student = Student.objects.get(user=request.user)
        
        # Get student's recent documents
        recent_documents = StudyMaterial.objects.filter(
            student=student
        ).order_by('-upload_date')[:10]
        
        context = {
            'student': student,
            'recent_documents': recent_documents,
        }
        
        return render(request, 'study_agent/index.html', context)
        
    except Student.DoesNotExist:
        # Redirect to preferences if student profile not found
        return redirect('mindmate:student_preferences')


@login_required
def get_recent_documents(request):
    """Get recent documents for Study Agent interface"""
    try:
        student = Student.objects.get(user=request.user)
        
        # Get recent documents
        documents = StudyMaterial.objects.filter(
            student=student
        ).order_by('-upload_date')[:20]
        
        documents_data = []
        for doc in documents:
            documents_data.append({
                'id': doc.id,
                'name': doc.original_filename or doc.title,
                'title': doc.title,
                'subject': doc.subject or 'Uncategorized',
                'type': doc.type,
                'upload_date': doc.upload_date.isoformat(),
                'processing_status': doc.processing_status,
                'file_size': getattr(doc, 'file_size', 0)
            })
        
        return JsonResponse({
            'success': True,
            'documents': documents_data
        })
        
    except Student.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Student not found'
        }, status=404)
    except Exception as e:
        logger.error(f"Error getting recent documents: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Internal server error'
        }, status=500)


@login_required 
@require_http_methods(["GET"])
def get_recent_documents(request):
    """API endpoint to get recent documents for the Study Agent"""
    try:
        student = Student.objects.get(user=request.user)
        
        documents = StudyMaterial.objects.filter(
            student=student
        ).order_by('-upload_date')[:20]
        
        document_list = []
        for doc in documents:
            # Calculate time ago
            now = timezone.now()
            time_diff = now - doc.upload_date
            
            if time_diff.days > 0:
                time_ago = f"{time_diff.days} day{'s' if time_diff.days > 1 else ''} ago"
            elif time_diff.seconds > 3600:
                hours = time_diff.seconds // 3600
                time_ago = f"{hours} hour{'s' if hours > 1 else ''} ago"
            else:
                minutes = time_diff.seconds // 60
                time_ago = f"{minutes} minute{'s' if minutes > 1 else ''} ago"
            
            document_list.append({
                'id': doc.id,
                'name': doc.original_filename,
                'title': doc.title or doc.original_filename,
                'type': doc.type,
                'subject': doc.subject or 'General',
                'upload_date': doc.upload_date.isoformat(),
                'time_ago': time_ago,
                'processing_status': doc.processing_status,
                'file_size': None  # We don't store file size currently
            })
        
        return JsonResponse({
            'success': True,
            'documents': document_list,
            'total_count': documents.count()
        })
        
    except Student.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Student not found'
        }, status=404)
    except Exception as e:
        logger.error(f"Error getting recent documents: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Internal server error'
        }, status=500)


@login_required
@csrf_exempt  
@require_http_methods(["DELETE"])
def delete_document(request, document_id):
    """Delete a document"""
    try:
        student = Student.objects.get(user=request.user)
        
        try:
            document = StudyMaterial.objects.get(id=document_id, student=student)
        except StudyMaterial.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Document not found'
            }, status=404)
        
        if document.file_path:
            import os
            from django.conf import settings
            full_path = os.path.join(settings.MEDIA_ROOT, document.file_path)
            if os.path.exists(full_path):
                try:
                    os.remove(full_path)
                except Exception as e:
                    logger.warning(f"Could not delete file {full_path}: {e}")
        
        document_name = document.original_filename or document.title
        document.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'Document "{document_name}" deleted successfully'
        })
        
    except Student.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Student not found'
        }, status=404)
    except Exception as e:
        logger.error(f"Error deleting document: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Internal server error'
        }, status=500)


@login_required
def profile_view(request):
    """Display user profile"""
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        messages.error(request, 'Студентскиот профил не е пронајден.')
        return redirect('mindmate:register')

    # Get or create student preferences
    preferences, created = StudentPreferences.objects.get_or_create(student=student)

    # Get progress data
    try:
        progress = Progress.objects.get(student=student)
        streak = Streak.objects.get(progress=progress)
        streak_days = streak.days_count
    except (Progress.DoesNotExist, Streak.DoesNotExist):
        streak_days = 0

    # Get quiz statistics
    quiz_results = QuizResult.objects.filter(student=student)
    completed_quizzes = quiz_results.count()

    if quiz_results.exists():
        total_accuracy = sum([result.accuracy_percentage for result in quiz_results])
        accuracy_percentage = round(total_accuracy / len(quiz_results), 1)
    else:
        accuracy_percentage = 0.0

    # Get badges
    badges = Badge.objects.filter(student=student).order_by('-received_at')

    context = {
        'student': student,
        'preferences': preferences,
        'streak_days': streak_days,
        'completed_quizzes': completed_quizzes,
        'accuracy_percentage': accuracy_percentage,
        'badges': badges,
        'interests': student.interests.split(', ') if student.interests else [],
    }

    return render(request, 'profile/profile.html', context)



@login_required
@csrf_exempt
@require_http_methods(["POST"])
def update_profile(request):
    """Update user profile information"""
    try:
        student = Student.objects.get(user=request.user)
        data = json.loads(request.body)

        # Update student fields
        if 'full_name' in data:
            student.full_name = data['full_name']
            # Update User model too
            name_parts = data['full_name'].split()
            if name_parts:
                request.user.first_name = name_parts[0]
                if len(name_parts) > 1:
                    request.user.last_name = ' '.join(name_parts[1:])
                request.user.save()

        if 'email' in data:
            # Check if email is already taken by another user
            if User.objects.filter(email=data['email']).exclude(id=request.user.id).exists():
                return JsonResponse({
                    'success': False,
                    'error': 'Оваа е-пошта веќе се користи'
                }, status=400)

            student.email = data['email']
            request.user.email = data['email']
            request.user.username = data['email']
            request.user.save()

        if 'study_direction' in data:
            student.study_direction = data['study_direction']

        student.save()

        # Update preferences
        preferences, created = StudentPreferences.objects.get_or_create(student=student)

        if 'major_field_of_study' in data:
            preferences.major_field_of_study = data['major_field_of_study']

        if 'learning_goals' in data:
            preferences.learning_goals = data['learning_goals']

        preferences.save()

        return JsonResponse({
            'success': True,
            'message': 'Профилот е успешно ажуриран'
        })

    except Student.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Студентскиот профил не е пронајден'
        }, status=404)
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Невалидни податоци'
        }, status=400)
    except Exception as e:
        logger.error(f"Profile update error: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Грешка при ажурирање на профилот'
        }, status=500)