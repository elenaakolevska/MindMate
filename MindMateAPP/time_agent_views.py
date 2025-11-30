"""
Time Agent API Views

Provides REST API endpoints for task estimation functionality
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List

from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.db.models import Avg, Count, Q
from django.core.paginator import Paginator

from .models import (
    Student, TaskEstimationRequest, TaskEstimationFeedback,
    StudentPerformanceProfile, TaskCompletionLog, CalendarEvent
)
from .services.task_estimator import TaskEstimatorService, TaskEstimate
from .services.llama_estimator import LlamaTaskEstimator, AIEstimationContext

logger = logging.getLogger(__name__)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def estimate_task_time(request):
    """
    API endpoint to estimate task completion time
    
    POST /api/time-agent/estimate/
    Body: {
        "task_description": "study for math exam",
        "subject_area": "mathematics",  # optional
        "difficulty": "moderate",       # optional: easy|moderate|challenging|very_challenging  
        "deadline": "2023-12-15T10:00:00Z",  # optional ISO datetime
        "context": {                    # optional additional context
            "estimated_pages": 50,
            "task_type": "exam"
        }
    }
    """
    try:
        # Get student
        student = get_object_or_404(Student, user=request.user)
        
        # Parse request data
        data = json.loads(request.body)
        task_description = data.get('task_description', '').strip()
        
        if not task_description:
            return JsonResponse({
                'success': False,
                'error': 'Task description is required'
            }, status=400)
        
        # Extract optional parameters
        subject_area = data.get('subject_area', '').strip()
        difficulty = data.get('difficulty', 'moderate')
        deadline_str = data.get('deadline')
        context = data.get('context', {})
        
        # Parse deadline if provided
        deadline = None
        if deadline_str:
            try:
                deadline = datetime.fromisoformat(deadline_str.replace('Z', '+00:00'))
            except ValueError:
                logger.warning(f"Invalid deadline format: {deadline_str}")
        
        # Create estimation context
        estimation_context = {
            'subject': subject_area,
            'difficulty': difficulty,
            'deadline': deadline,
            **context
        }
        
        # Initialize task estimator service
        estimator = TaskEstimatorService(student)
        
        # Get time estimate
        estimate = estimator.estimate_task_time(task_description, estimation_context)
        
        # Enhance with AI estimation if available
        ai_enhancement = _get_ai_enhancement(student, task_description, estimate, estimation_context)
        
        # Store estimation request in database
        estimation_request = _store_estimation_request(
            student, task_description, estimate, ai_enhancement, estimation_context, deadline
        )
        
        # Suggest time slots
        suggested_start, suggested_end = estimator.suggest_time_slot(
            estimate, 
            preferred_time=context.get('preferred_time'),
            deadline=deadline
        )
        
        # Format time in Macedonian
        hours = estimate.estimated_hours
        if hours >= 1:
            if hours == 1:
                time_text = "1 час"
            elif hours < 2:
                time_text = f"{hours:.1f} часа" if hours != int(hours) else f"{int(hours)} часа"
            else:
                time_text = f"{hours:.1f} часа" if hours != int(hours) else f"{int(hours)} часа"
        else:
            minutes = int(hours * 60)
            time_text = f"{minutes} минути"
        
        # Clean reasoning text to be only in Macedonian
        reasoning = estimate.reasoning
        # Remove English phrases that might appear
        english_phrases = ['Based on', 'Estimated', 'hours', 'minutes', 'difficulty', 'complexity', 'task', 'study']
        for phrase in english_phrases:
            reasoning = reasoning.replace(phrase, '').replace(phrase.lower(), '')
        reasoning = reasoning.strip()
        
        # Clean reasoning from mixed language artifacts
        if 'час' not in reasoning and 'минути' not in reasoning and len(reasoning) > 10:
            # If reasoning doesn't contain Macedonian time words, provide default Macedonian reasoning
            reasoning = f"Проценката е направена врз основа на сложеноста на задачата и вашите претходни перформанси."
        
        # Ensure recommendation is in Macedonian
        recommendation = f"Препорачувам да издвоиш {time_text} за оваа задача."
        
        # Prepare response
        response_data = {
            'success': True,
            'estimation_id': estimation_request.id,
            'task_description': task_description,
            'estimated_hours': estimate.estimated_hours,
            'time_formatted': time_text,
            'confidence_level': estimate.confidence_level,
            'difficulty_assessment': ai_enhancement.get('difficulty_assessment', 'moderate'),
            'reasoning': reasoning,
            'recommendation': recommendation,
            'factors_considered': estimate.factors_considered,
            'time_breakdown': ai_enhancement.get('time_breakdown', {
                'preparation': 0.2 * estimate.estimated_hours,
                'main_work': 0.7 * estimate.estimated_hours, 
                'review': 0.1 * estimate.estimated_hours
            }),
            'recommended_approach': ai_enhancement.get('recommended_approach', 'Следи структуиран план за учење'),
            'potential_obstacles': ai_enhancement.get('potential_obstacles', ['Управување со време', 'Сложеност на задачата']),
            'success_tips': ai_enhancement.get('success_tips', [
                'Подели ја задачата на помали делови',
                'Прави редовни паузи', 
                'Следи го својот напредок'
            ]),
            'suggested_schedule': {
                'start_time': suggested_start.isoformat() if suggested_start else None,
                'end_time': suggested_end.isoformat() if suggested_end else None,
            } if suggested_start else None
        }
        
        return JsonResponse(response_data)
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        logger.error(f"Error in task estimation: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Internal server error'
        }, status=500)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def record_task_completion(request, estimation_id):
    """
    Record actual task completion time for learning
    
    POST /api/time-agent/estimate/{estimation_id}/complete/
    Body: {
        "actual_hours": 2.5,
        "completion_quality": 4,      # 1-5 rating
        "challenges_faced": ["time management", "difficult concepts"],
        "feedback": "The estimate was pretty accurate",
        "session_details": {          # optional detailed logging
            "actual_start_time": "2023-12-15T09:00:00Z",
            "actual_end_time": "2023-12-15T11:30:00Z", 
            "breaks_taken": 2,
            "focus_rating": 4
        }
    }
    """
    try:
        # Get student and estimation
        student = get_object_or_404(Student, user=request.user)
        estimation = get_object_or_404(
            TaskEstimationRequest, 
            id=estimation_id, 
            student=student
        )
        
        # Parse request data
        data = json.loads(request.body)
        actual_hours = data.get('actual_hours')
        
        if actual_hours is None or actual_hours < 0:
            return JsonResponse({
                'success': False,
                'error': 'Valid actual_hours is required'
            }, status=400)
        
        # Update estimation with completion data
        estimation.actual_hours_spent = actual_hours
        estimation.status = 'completed'
        estimation.completed_at = timezone.now()
        estimation.student_feedback = data.get('feedback', '')
        
        # Calculate accuracy
        estimation.calculate_accuracy()
        estimation.save()
        
        # Store detailed completion log if provided
        session_details = data.get('session_details', {})
        if session_details:
            _create_completion_log(estimation, session_details, data)
        
        # Create feedback entry
        completion_quality = data.get('completion_quality', 3)
        challenges_faced = data.get('challenges_faced', [])
        
        TaskEstimationFeedback.objects.create(
            estimation=estimation,
            feedback_type='accuracy',
            rating=completion_quality,
            comments=data.get('feedback', ''),
            unexpected_difficulties=challenges_faced,
            was_too_optimistic=actual_hours > (estimation.estimated_hours * 1.2),
            was_too_pessimistic=actual_hours < (estimation.estimated_hours * 0.8)
        )
        
        # Update student performance profile
        _update_performance_profile(student)
        
        # Calculate improvement insights
        insights = _calculate_learning_insights(estimation, student)
        
        response_data = {
            'success': True,
            'estimation_id': estimation.id,
            'accuracy_score': estimation.accuracy_score,
            'time_deviation_percentage': estimation.get_time_deviation_percentage(),
            'learning_insights': insights,
            'performance_update': 'Student performance profile updated successfully'
        }
        
        return JsonResponse(response_data)
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        logger.error(f"Error recording completion: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Internal server error'
        }, status=500)


@login_required
@require_http_methods(["GET"])
def get_estimation_history(request):
    """
    Get student's task estimation history
    
    GET /api/time-agent/history/?page=1&limit=10&status=completed&subject=math
    """
    try:
        student = get_object_or_404(Student, user=request.user)
        
        # Get query parameters
        page = int(request.GET.get('page', 1))
        limit = min(int(request.GET.get('limit', 10)), 50)  # Max 50 items per page
        status = request.GET.get('status')
        subject = request.GET.get('subject')
        
        # Build query
        estimations = TaskEstimationRequest.objects.filter(student=student)
        
        if status:
            estimations = estimations.filter(status=status)
        if subject:
            estimations = estimations.filter(subject_area__icontains=subject)
        
        estimations = estimations.order_by('-created_at')
        
        # Paginate
        paginator = Paginator(estimations, limit)
        page_obj = paginator.get_page(page)
        
        # Serialize data
        history_data = []
        for estimation in page_obj:
            history_data.append({
                'id': estimation.id,
                'task_description': estimation.task_description,
                'task_type': estimation.task_type,
                'subject_area': estimation.subject_area,
                'estimated_hours': estimation.estimated_hours,
                'actual_hours': estimation.actual_hours_spent,
                'accuracy_score': estimation.accuracy_score,
                'confidence_score': estimation.confidence_score,
                'difficulty_level': estimation.difficulty_level,
                'status': estimation.status,
                'created_at': estimation.created_at.isoformat(),
                'completed_at': estimation.completed_at.isoformat() if estimation.completed_at else None,
                'time_deviation_percentage': estimation.get_time_deviation_percentage()
            })
        
        response_data = {
            'success': True,
            'history': history_data,
            'pagination': {
                'current_page': page,
                'total_pages': paginator.num_pages,
                'total_items': paginator.count,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous()
            }
        }
        
        return JsonResponse(response_data)
        
    except Exception as e:
        logger.error(f"Error getting estimation history: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Internal server error'
        }, status=500)


@login_required
@require_http_methods(["GET"])
def get_performance_analytics(request):
    """
    Get student's performance analytics and insights
    
    GET /api/time-agent/analytics/
    """
    try:
        student = get_object_or_404(Student, user=request.user)
        
        # Get or create performance profile
        profile, created = StudentPerformanceProfile.objects.get_or_create(student=student)
        
        if not created:
            # Update metrics if profile exists
            profile.update_performance_metrics()
        
        # Get recent estimations for trends
        recent_estimations = TaskEstimationRequest.objects.filter(
            student=student,
            status='completed',
            completed_at__gte=timezone.now() - timedelta(days=30)
        ).order_by('completed_at')
        
        # Calculate trends
        accuracy_trend = []
        for estimation in recent_estimations[-10:]:  # Last 10 completed
            if estimation.accuracy_score is not None:
                accuracy_trend.append({
                    'date': estimation.completed_at.date().isoformat(),
                    'accuracy': estimation.accuracy_score,
                    'task_type': estimation.task_type
                })
        
        # Subject performance breakdown
        subject_stats = TaskEstimationRequest.objects.filter(
            student=student,
            status='completed',
            accuracy_score__isnull=False
        ).values('subject_area').annotate(
            count=Count('id'),
            avg_accuracy=Avg('accuracy_score'),
            avg_estimated_hours=Avg('estimated_hours'),
            avg_actual_hours=Avg('actual_hours_spent')
        ).order_by('-count')
        
        # Task type performance
        task_type_stats = TaskEstimationRequest.objects.filter(
            student=student,
            status='completed',
            accuracy_score__isnull=False
        ).values('task_type').annotate(
            count=Count('id'),
            avg_accuracy=Avg('accuracy_score'),
            avg_estimated_hours=Avg('estimated_hours'),
            avg_actual_hours=Avg('actual_hours_spent')
        ).order_by('-count')
        
        response_data = {
            'success': True,
            'performance_profile': {
                'total_estimations': profile.total_estimations,
                'average_accuracy': profile.average_accuracy_score,
                'recent_accuracy': profile.recent_accuracy_score,
                'improvement_trend': profile.estimation_improvement_trend,
                'consistency_score': profile.consistency_score,
                'recent_completion_rate': profile.recent_completion_rate
            },
            'accuracy_trend': accuracy_trend,
            'subject_performance': list(subject_stats),
            'task_type_performance': list(task_type_stats),
            'insights': _generate_performance_insights(profile, student),
            'recommendations': _generate_recommendations(profile, student)
        }
        
        return JsonResponse(response_data)
        
    except Exception as e:
        logger.error(f"Error getting performance analytics: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Internal server error'
        }, status=500)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def suggest_study_schedule(request):
    """
    Suggest optimal study schedule for multiple tasks
    
    POST /api/time-agent/schedule/
    Body: {
        "tasks": [
            {
                "description": "Study for math exam",
                "estimated_hours": 3.0,
                "deadline": "2023-12-20T10:00:00Z",
                "priority": "high"
            }
        ],
        "preferences": {
            "preferred_times": ["morning", "evening"],
            "max_session_length": 2.0,
            "break_frequency": 0.25
        }
    }
    """
    try:
        student = get_object_or_404(Student, user=request.user)
        data = json.loads(request.body)
        
        tasks = data.get('tasks', [])
        preferences = data.get('preferences', {})
        
        if not tasks:
            return JsonResponse({
                'success': False,
                'error': 'At least one task is required'
            }, status=400)
        
        # Get existing calendar events
        existing_events = CalendarEvent.objects.filter(
            student=student,
            date_time__gte=timezone.now(),
            date_time__lte=timezone.now() + timedelta(days=14)
        ).order_by('date_time')
        
        # Generate schedule suggestions
        schedule = _generate_study_schedule(tasks, preferences, existing_events)
        
        response_data = {
            'success': True,
            'suggested_schedule': schedule,
            'total_study_hours': sum(task.get('estimated_hours', 0) for task in tasks),
            'schedule_conflicts': schedule.get('conflicts', []),
            'optimization_notes': schedule.get('notes', [])
        }
        
        return JsonResponse(response_data)
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        logger.error(f"Error suggesting schedule: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Internal server error'
        }, status=500)


# Helper functions

def _get_ai_enhancement(student: Student, task_description: str, estimate: TaskEstimate, context: Dict) -> Dict:
    """Get AI-powered enhancement to the basic estimate"""
    try:
        # Create AI estimation context
        student_prefs = getattr(student, 'preferences', None)
        
        ai_context = AIEstimationContext(
            student_level=student.study_level,
            subject_area=context.get('subject', 'general'),
            task_complexity=context.get('difficulty', 'moderate'),
            historical_performance=_get_student_historical_data(student),
            learning_style=getattr(student_prefs, 'preferred_learning_style', 'reading_writing') if student_prefs else 'reading_writing'
        )
        
        # Try to get AI enhancement (fallback to rule-based if AI unavailable)
        llama_estimator = LlamaTaskEstimator()
        ai_result = llama_estimator.estimate_with_ai(task_description, ai_context, estimate.estimated_hours)
        
        return ai_result
        
    except Exception as e:
        logger.warning(f"AI enhancement failed, using fallback: {e}")
        return {
            'difficulty_assessment': 'moderate',
            'recommended_approach': 'Use a structured study plan with regular breaks',
            'potential_obstacles': ['Time management', 'Task complexity'],
            'success_tips': ['Break into smaller chunks', 'Track progress', 'Take breaks'],
            'time_breakdown': {
                'preparation': 0.2 * estimate.estimated_hours,
                'main_work': 0.7 * estimate.estimated_hours,
                'review': 0.1 * estimate.estimated_hours
            }
        }


def _store_estimation_request(
    student: Student, 
    task_description: str, 
    estimate: TaskEstimate, 
    ai_enhancement: Dict,
    context: Dict,
    deadline: datetime = None
) -> TaskEstimationRequest:
    """Store estimation request in database"""
    
    # Determine task type from description or context
    task_type = context.get('task_type', 'study')
    if not task_type or task_type not in [choice[0] for choice in TaskEstimationRequest.TASK_TYPE_CHOICES]:
        task_type = 'study'
    
    return TaskEstimationRequest.objects.create(
        student=student,
        task_description=task_description,
        task_type=task_type,
        subject_area=context.get('subject', ''),
        estimated_hours=estimate.estimated_hours,
        confidence_score=estimate.confidence_level,
        estimation_method='hybrid_ai',
        difficulty_level=ai_enhancement.get('difficulty_assessment', 'moderate'),
        urgency_level=context.get('urgency', 'normal'),
        deadline=deadline,
        reasoning=estimate.reasoning,
        factors_considered=estimate.factors_considered,
        recommended_approach=ai_enhancement.get('recommended_approach', ''),
        potential_obstacles=ai_enhancement.get('potential_obstacles', []),
        time_breakdown=ai_enhancement.get('time_breakdown', {})
    )


def _get_student_historical_data(student: Student) -> Dict:
    """Get student's historical performance data for AI context"""
    try:
        recent_estimations = TaskEstimationRequest.objects.filter(
            student=student,
            status='completed',
            accuracy_score__isnull=False
        ).order_by('-completed_at')[:10]
        
        if not recent_estimations.exists():
            return {}
        
        accuracies = [est.accuracy_score for est in recent_estimations]
        avg_accuracy = sum(accuracies) / len(accuracies) * 100  # Convert to percentage
        
        return {
            'accuracy_rate': avg_accuracy,
            'task_count': recent_estimations.count(),
            'completion_rate': 85.0,  # Default completion rate
            'avg_time_deviation': sum(abs(est.get_time_deviation_percentage() or 0) for est in recent_estimations) / len(recent_estimations)
        }
        
    except Exception as e:
        logger.warning(f"Error getting historical data: {e}")
        return {}


def _create_completion_log(estimation: TaskEstimationRequest, session_details: Dict, completion_data: Dict):
    """Create detailed completion log"""
    try:
        # Parse session times
        start_time = None
        end_time = None
        
        if session_details.get('actual_start_time'):
            start_time = datetime.fromisoformat(session_details['actual_start_time'].replace('Z', '+00:00'))
        if session_details.get('actual_end_time'):
            end_time = datetime.fromisoformat(session_details['actual_end_time'].replace('Z', '+00:00'))
        
        TaskCompletionLog.objects.create(
            estimation=estimation,
            actual_start_time=start_time,
            actual_end_time=end_time,
            total_breaks_taken=session_details.get('breaks_taken', 0),
            focus_quality_rating=session_details.get('focus_rating', 3),
            satisfaction_rating=completion_data.get('completion_quality', 3),
            distractions_encountered=completion_data.get('challenges_faced', []),
            student_notes=completion_data.get('feedback', '')
        )
        
    except Exception as e:
        logger.error(f"Error creating completion log: {e}")


def _update_performance_profile(student: Student):
    """Update student's performance profile"""
    try:
        profile, created = StudentPerformanceProfile.objects.get_or_create(student=student)
        profile.update_performance_metrics()
    except Exception as e:
        logger.error(f"Error updating performance profile: {e}")


def _calculate_learning_insights(estimation: TaskEstimationRequest, student: Student) -> Dict:
    """Calculate learning insights from completed estimation"""
    insights = []
    
    if estimation.accuracy_score is not None:
        if estimation.accuracy_score > 0.8:
            insights.append("Great job! Your time estimation was very accurate.")
        elif estimation.accuracy_score > 0.6:
            insights.append("Good estimation. Minor adjustments could improve accuracy.")
        else:
            insights.append("Consider breaking down complex tasks for better estimation.")
    
    deviation = estimation.get_time_deviation_percentage()
    if deviation is not None:
        if deviation > 50:
            insights.append("Task took much longer than expected. Consider similar tasks need more time.")
        elif deviation < -30:
            insights.append("Task completed faster than expected. You might be underestimating your abilities.")
    
    return {
        'insights': insights,
        'accuracy_category': 'excellent' if estimation.accuracy_score and estimation.accuracy_score > 0.8 else 'good' if estimation.accuracy_score and estimation.accuracy_score > 0.6 else 'needs_improvement'
    }


def _generate_performance_insights(profile: StudentPerformanceProfile, student: Student) -> List[str]:
    """Generate performance insights for the student"""
    insights = []
    
    if profile.average_accuracy_score > 0.8:
        insights.append("You're excellent at estimating task duration! Keep up the great work.")
    elif profile.average_accuracy_score > 0.6:
        insights.append("Your estimation skills are developing well. Focus on identifying task complexity patterns.")
    else:
        insights.append("Consider breaking larger tasks into smaller, more manageable pieces for better estimation.")
    
    if profile.recent_accuracy_score > profile.average_accuracy_score:
        insights.append("Your estimation accuracy is improving over time - great progress!")
    
    if profile.recent_completion_rate < 0.7:
        insights.append("Consider setting more realistic deadlines to improve task completion rates.")
    
    return insights


def _generate_recommendations(profile: StudentPerformanceProfile, student: Student) -> List[str]:
    """Generate personalized recommendations"""
    recommendations = []
    
    if profile.average_accuracy_score < 0.6:
        recommendations.append("Start with smaller, well-defined tasks to build estimation skills")
        recommendations.append("Track your actual time spent on different types of tasks")
    
    if profile.consistency_score < 0.5:
        recommendations.append("Try to study at consistent times of day for better time prediction")
        recommendations.append("Use a timer to become more aware of actual time spent")
    
    recommendations.append("Review your estimation accuracy regularly to identify patterns")
    
    return recommendations


def _generate_study_schedule(tasks: List[Dict], preferences: Dict, existing_events) -> Dict:
    """Generate optimized study schedule"""
    # This is a simplified scheduling algorithm
    # In production, you might use more sophisticated optimization
    
    schedule = {
        'sessions': [],
        'conflicts': [],
        'notes': []
    }
    
    max_session_length = preferences.get('max_session_length', 2.0)
    preferred_times = preferences.get('preferred_times', ['morning', 'afternoon'])
    
    # Sort tasks by deadline and priority
    sorted_tasks = sorted(tasks, key=lambda x: (
        datetime.fromisoformat(x.get('deadline', '2099-12-31T23:59:59Z').replace('Z', '+00:00')),
        {'high': 1, 'medium': 2, 'low': 3}.get(x.get('priority', 'medium'), 2)
    ))
    
    current_time = timezone.now().replace(hour=9, minute=0, second=0, microsecond=0)
    if current_time < timezone.now():
        current_time += timedelta(days=1)
    
    for task in sorted_tasks:
        remaining_hours = task.get('estimated_hours', 2.0)
        task_deadline = datetime.fromisoformat(task.get('deadline', '2099-12-31T23:59:59Z').replace('Z', '+00:00'))
        
        while remaining_hours > 0:
            session_length = min(remaining_hours, max_session_length)
            
            # Find next available slot
            session_start = current_time
            session_end = session_start + timedelta(hours=session_length)
            
            # Check for conflicts with existing events
            conflicts = [event for event in existing_events 
                        if event.date_time < session_end and 
                        (event.end_time or event.date_time + timedelta(hours=1)) > session_start]
            
            if conflicts:
                # Move to after the conflicting event
                latest_conflict_end = max(
                    event.end_time or event.date_time + timedelta(hours=1) 
                    for event in conflicts
                )
                current_time = latest_conflict_end + timedelta(minutes=30)  # 30-min buffer
                continue
            
            # Check if session would exceed deadline
            if session_end > task_deadline:
                schedule['conflicts'].append({
                    'task': task['description'],
                    'issue': 'Not enough time before deadline',
                    'deadline': task_deadline.isoformat()
                })
                break
            
            # Add session to schedule
            schedule['sessions'].append({
                'task_description': task['description'],
                'start_time': session_start.isoformat(),
                'end_time': session_end.isoformat(),
                'duration_hours': session_length,
                'task_priority': task.get('priority', 'medium')
            })
            
            remaining_hours -= session_length
            current_time = session_end + timedelta(minutes=15)  # Short break between sessions
    
    # Add optimization notes
    if len(schedule['sessions']) > 0:
        schedule['notes'].append(f"Scheduled {len(schedule['sessions'])} study sessions")
    if len(schedule['conflicts']) > 0:
        schedule['notes'].append(f"Found {len(schedule['conflicts'])} scheduling conflicts")
    
    return schedule