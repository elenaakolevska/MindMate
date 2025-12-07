"""
Quiz Generation Views

API endpoints for generating and managing AI-powered quizzes
from student study materials using RAG and Llama3.
"""

from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
import json
import logging

from .models import Quiz, QuizQuestion, QuizResult, StudyMaterial, Student
from .services.quiz_generator import get_quiz_generator, QuizGenerationOptions

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["POST"])
def generate_quiz(request):
    """
    Generate a new quiz from study materials
    
    POST /api/quiz/generate/
    Body: {
        "student_id": int,
        "questions_count": int (optional, default 10),
        "quiz_type": str (optional, "multiple_choice"|"true_false"|"mixed", default "mixed"),
        "difficulty": str (optional, "easy"|"medium"|"hard", default from preferences),
        "subject_filter": str (optional),
        "material_ids": [int] (optional, specific materials to use)
    }
    """
    try:
        data = json.loads(request.body)
        student_id = data.get('student_id')
        
        if not student_id:
            return JsonResponse({'error': 'student_id is required'}, status=400)
        
        # Validate student exists
        try:
            student = Student.objects.get(id=student_id)
        except Student.DoesNotExist:
            return JsonResponse({'error': f'Student with id {student_id} not found'}, status=404)
        
        # Prepare generation options
        options = QuizGenerationOptions(
            questions_count=data.get('questions_count', 10),
            quiz_type=data.get('quiz_type', 'mixed'),
            difficulty=data.get('difficulty', 'medium'),
            subject_filter=data.get('subject_filter'),
            material_ids=data.get('material_ids')
        )
        
        # Validate generation requirements
        quiz_generator = get_quiz_generator()
        validation = quiz_generator.validate_quiz_generation_requirements(student_id)
        
        if not validation['can_generate_quiz']:
            return JsonResponse({
                'error': 'Cannot generate quiz',
                'details': 'No processed study materials available',
                'validation': validation
            }, status=400)
        
        # Generate quiz
        logger.info(f"Generating quiz for student {student_id}")
        quiz, quiz_questions = quiz_generator.generate_quiz(student_id, options)
        
        # Format response
        response_data = {
            'quiz': {
                'id': quiz.id,
                'quiz_type': quiz.quiz_type,
                'subject': quiz.subject,
                'difficulty': quiz.difficulty,
                'questions_count': quiz.questions_count,
                'created_at': quiz.created_at.isoformat() if hasattr(quiz, 'created_at') else None,
                'generated_from_material': quiz.generated_from_material.title if quiz.generated_from_material else None
            },
            'questions': [
                {
                    'id': q.id,
                    'question_text': q.question_text,
                    'question_type': q.question_type,
                    'options': q.options,
                    'correct_answer': q.correct_answer,
                    'explanation': q.explanation
                }
                for q in quiz_questions
            ],
            'generation_info': {
                'student_id': student_id,
                'options': {
                    'questions_count': options.questions_count,
                    'quiz_type': options.quiz_type,
                    'difficulty': options.difficulty,
                    'subject_filter': options.subject_filter,
                    'material_ids': options.material_ids
                }
            }
        }
        
        logger.info(f"Successfully generated quiz {quiz.id} with {len(quiz_questions)} questions")
        return JsonResponse(response_data, status=201)
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON in request body'}, status=400)
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        logger.error(f"Error generating quiz: {e}")
        return JsonResponse({'error': f'Quiz generation failed: {str(e)}'}, status=500)


@require_http_methods(["GET"])
def get_quiz(request, quiz_id):
    """
    Get quiz details and questions
    
    GET /api/quiz/<quiz_id>/
    """
    try:
        quiz = get_object_or_404(Quiz, id=quiz_id)
        questions = QuizQuestion.objects.filter(quiz=quiz).order_by('id')
        
        response_data = {
            'quiz': {
                'id': quiz.id,
                'quiz_type': quiz.quiz_type,
                'subject': quiz.subject,
                'difficulty': quiz.difficulty,
                'questions_count': quiz.questions_count,
                'created_at': quiz.created_at.isoformat() if hasattr(quiz, 'created_at') else None,
                'generated_from_material': quiz.generated_from_material.title if quiz.generated_from_material else None
            },
            'questions': [
                {
                    'id': q.id,
                    'question_text': q.question_text,
                    'question_type': q.question_type,
                    'options': q.options,
                    # Don't include correct_answer or explanation for active quiz
                }
                for q in questions
            ]
        }
        
        return JsonResponse(response_data)
        
    except Exception as e:
        logger.error(f"Error retrieving quiz {quiz_id}: {e}")
        return JsonResponse({'error': f'Failed to retrieve quiz: {str(e)}'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def submit_quiz(request, quiz_id):
    """
    Submit quiz answers and get results
    
    POST /api/quiz/<quiz_id>/submit/
    Body: {
        "student_id": int,
        "answers": {
            "question_id": "selected_answer",
            ...
        }
    }
    """
    try:
        data = json.loads(request.body)
        student_id = data.get('student_id')
        answers = data.get('answers', {})
        
        if not student_id:
            return JsonResponse({'error': 'student_id is required'}, status=400)
        
        if not answers:
            return JsonResponse({'error': 'answers are required'}, status=400)
        
        # Get quiz and questions
        quiz = get_object_or_404(Quiz, id=quiz_id)
        questions = QuizQuestion.objects.filter(quiz=quiz)
        
        # Validate student
        try:
            student = Student.objects.get(id=student_id)
        except Student.DoesNotExist:
            return JsonResponse({'error': f'Student with id {student_id} not found'}, status=404)
        
        # Calculate results
        total_questions = questions.count()
        correct_answers = 0
        question_results = []
        
        for question in questions:
            user_answer = answers.get(str(question.id), '').strip().upper()
            correct_answer = question.correct_answer.strip().upper()
            is_correct = user_answer == correct_answer
            
            if is_correct:
                correct_answers += 1
            
            question_results.append({
                'question_id': question.id,
                'question_text': question.question_text,
                'user_answer': user_answer,
                'correct_answer': question.correct_answer,
                'is_correct': is_correct,
                'explanation': question.explanation
            })
        
        # Calculate score
        score_percentage = (correct_answers / total_questions * 100) if total_questions > 0 else 0
        
        # Save quiz result
        quiz_result = QuizResult.objects.create(
            student=student,
            quiz=quiz,
            score=correct_answers,  # Points earned
            max_score=total_questions,  # Total possible points  
            accuracy_percentage=score_percentage  # Percentage score
        )
        
        # Format response
        response_data = {
            'quiz_result': {
                'id': quiz_result.id,
                'score': quiz_result.score,
                'max_score': quiz_result.max_score,
                'accuracy_percentage': quiz_result.accuracy_percentage,
                'completion_time': quiz_result.taken_at.isoformat()
            },
            'quiz_info': {
                'id': quiz.id,
                'subject': quiz.subject,
                'difficulty': quiz.difficulty,
                'quiz_type': quiz.quiz_type
            },
            'detailed_results': question_results,
            'performance_summary': {
                'grade': _calculate_grade(quiz_result.accuracy_percentage),
                'passed': quiz_result.accuracy_percentage >= 70,  # 70% passing threshold
                'areas_for_improvement': _identify_improvement_areas(question_results, quiz)
            }
        }
        
        logger.info(f"Quiz {quiz_id} submitted by student {student_id}: {score_percentage:.1f}% ({correct_answers}/{total_questions})")
        return JsonResponse(response_data, status=201)
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON in request body'}, status=400)
    except Exception as e:
        logger.error(f"Error submitting quiz {quiz_id}: {e}")
        return JsonResponse({'error': f'Quiz submission failed: {str(e)}'}, status=500)


@require_http_methods(["GET"])
def get_quiz_results(request, quiz_result_id):
    """
    Get detailed quiz results
    
    GET /api/quiz/results/<quiz_result_id>/
    """
    try:
        quiz_result = get_object_or_404(QuizResult, id=quiz_result_id)
        quiz = quiz_result.quiz
        questions = QuizQuestion.objects.filter(quiz=quiz)
        
        # Reconstruct detailed results
        question_results = []
        for question in questions:
            user_answer = quiz_result.answers_data.get(str(question.id), '')
            is_correct = user_answer.strip().upper() == question.correct_answer.strip().upper()
            
            question_results.append({
                'question_id': question.id,
                'question_text': question.question_text,
                'user_answer': user_answer,
                'correct_answer': question.correct_answer,
                'is_correct': is_correct,
                'explanation': question.explanation
            })
        
        response_data = {
            'quiz_result': {
                'id': quiz_result.id,
                'score': quiz_result.score,
                'max_score': quiz_result.max_score,
                'accuracy_percentage': quiz_result.accuracy_percentage,
                'completion_time': quiz_result.taken_at.isoformat()
            },
            'quiz_info': {
                'id': quiz.id,
                'subject': quiz.subject,
                'difficulty': quiz.difficulty,
                'quiz_type': quiz.quiz_type
            },
            'student_info': {
                'id': quiz_result.student.id,
                'username': quiz_result.student.user.username if quiz_result.student.user else quiz_result.student.full_name
            },
            'detailed_results': question_results,
            'performance_summary': {
                'grade': _calculate_grade(quiz_result.accuracy_percentage),
                'passed': quiz_result.accuracy_percentage >= 70,
                'areas_for_improvement': _identify_improvement_areas(question_results, quiz)
            }
        }
        
        return JsonResponse(response_data)
        
    except Exception as e:
        logger.error(f"Error retrieving quiz results {quiz_result_id}: {e}")
        return JsonResponse({'error': f'Failed to retrieve quiz results: {str(e)}'}, status=500)


@require_http_methods(["GET"])
def list_student_quizzes(request):
    """
    List all quizzes for a student
    
    GET /api/quiz/student/<student_id>/
    """
    try:
        student_id = request.GET.get('student_id')
        if not student_id:
            return JsonResponse({'error': 'student_id parameter is required'}, status=400)
        
        try:
            student = Student.objects.get(id=student_id)
        except Student.DoesNotExist:
            return JsonResponse({'error': f'Student with id {student_id} not found'}, status=404)
        
        # Get quiz results for student
        quiz_results = QuizResult.objects.filter(student=student).select_related('quiz').order_by('-taken_at')

        quizzes_data = []
        for result in quiz_results:
            quiz = result.quiz
            quizzes_data.append({
                'quiz': {
                    'id': quiz.id,
                    'subject': quiz.subject,
                    'difficulty': quiz.difficulty,
                    'quiz_type': quiz.quiz_type,
                    'questions_count': quiz.questions_count
                },
                'result': {
                    'id': result.id,
                    'score': result.score,
                    'max_score': result.max_score,
                    'accuracy_percentage': result.accuracy_percentage,
                    'completion_time': result.taken_at.isoformat()
                }
            })        # Also get available materials for quiz generation
        quiz_generator = get_quiz_generator()
        validation = quiz_generator.validate_quiz_generation_requirements(student_id)
        
        response_data = {
            'student_id': student_id,
            'quiz_history': quizzes_data,
            'quiz_generation_status': validation,
            'available_subjects': _get_available_subjects_for_student(student_id)
        }
        
        return JsonResponse(response_data)
        
    except Exception as e:
        logger.error(f"Error listing quizzes for student {student_id}: {e}")
        return JsonResponse({'error': f'Failed to retrieve quiz list: {str(e)}'}, status=500)


@require_http_methods(["GET"])
def quiz_generation_status(request):
    """
    Check if student can generate quizzes
    
    GET /api/quiz/generation-status/?student_id=<id>
    """
    try:
        student_id = request.GET.get('student_id')
        if not student_id:
            return JsonResponse({'error': 'student_id parameter is required'}, status=400)
        
        quiz_generator = get_quiz_generator()
        validation = quiz_generator.validate_quiz_generation_requirements(int(student_id))
        
        response_data = {
            'student_id': int(student_id),
            'can_generate_quiz': validation['can_generate_quiz'],
            'has_materials': validation['has_materials'],
            'has_vector_data': validation['has_vector_data'],
            'material_count': validation['material_count'],
            'available_subjects': _get_available_subjects_for_student(student_id),
            'recommended_settings': {
                'difficulty': quiz_generator.get_student_difficulty_preference(int(student_id)),
                'questions_count': 10,
                'quiz_type': 'mixed'
            }
        }
        
        return JsonResponse(response_data)
        
    except Exception as e:
        logger.error(f"Error checking quiz generation status: {e}")
        return JsonResponse({'error': f'Failed to check generation status: {str(e)}'}, status=500)


def _calculate_grade(score_percentage: float) -> str:
    """Calculate letter grade from score percentage"""
    if score_percentage >= 90:
        return 'A'
    elif score_percentage >= 80:
        return 'B'
    elif score_percentage >= 70:
        return 'C'
    elif score_percentage >= 60:
        return 'D'
    else:
        return 'F'


def _identify_improvement_areas(question_results: list, quiz: Quiz) -> list:
    """Identify areas where student needs improvement"""
    improvement_areas = []
    
    # Count incorrect answers by type
    incorrect_questions = [q for q in question_results if not q['is_correct']]
    
    if len(incorrect_questions) > 0:
        incorrect_count = len(incorrect_questions)
        total_count = len(question_results)
        
        if incorrect_count / total_count > 0.5:
            improvement_areas.append(f"Review {quiz.subject} fundamentals")
        
        if incorrect_count / total_count > 0.3:
            improvement_areas.append("Practice more quiz questions")
        
        # Check if specific question types are problematic
        mc_incorrect = sum(1 for q in incorrect_questions if 'multiple_choice' in str(q))
        tf_incorrect = sum(1 for q in incorrect_questions if 'true_false' in str(q))
        
        if mc_incorrect > tf_incorrect and mc_incorrect > 2:
            improvement_areas.append("Focus on multiple choice strategies")
        elif tf_incorrect > mc_incorrect and tf_incorrect > 2:
            improvement_areas.append("Review true/false question analysis")
    
    return improvement_areas if improvement_areas else ["Continue practicing to maintain performance"]


def _get_available_subjects_for_student(student_id: int) -> list:
    """Get list of subjects available for quiz generation"""
    try:
        materials = StudyMaterial.objects.filter(
            student_id=student_id,
            processing_status='completed'
        ).values_list('subject', flat=True).distinct()
        
        return [subject for subject in materials if subject]
        
    except Exception as e:
        logger.error(f"Error getting available subjects: {e}")
        return []


# Template views for quiz interface
@login_required
def quiz_dashboard(request):
    """Dashboard for quiz management and generation"""
    try:
        # Get student for current user
        student = get_object_or_404(Student, user=request.user)
        
        # Get quiz generation status
        quiz_generator = get_quiz_generator()
        generation_status = quiz_generator.validate_quiz_generation_requirements(student.id)
        
        # Get recent quiz results
        recent_results = QuizResult.objects.filter(student=student).select_related('quiz').order_by('-taken_at')[:5]
        
        context = {
            'student': student,
            'generation_status': generation_status,
            'recent_results': recent_results,
            'available_subjects': _get_available_subjects_for_student(student.id)
        }
        
        return render(request, 'quiz/dashboard.html', context)
        
    except Exception as e:
        logger.error(f"Error loading quiz dashboard: {e}")
        return render(request, 'quiz/error.html', {'error': str(e)})


@login_required
def quiz_interface(request, quiz_id):
    """Interface for taking a quiz"""
    try:
        quiz = get_object_or_404(Quiz, id=quiz_id)
        questions = QuizQuestion.objects.filter(quiz=quiz).order_by('id')
        student = get_object_or_404(Student, user=request.user)
        
        context = {
            'quiz': quiz,
            'questions': questions,
            'student': student
        }
        
        return render(request, 'quiz/take_quiz.html', context)
        
    except Exception as e:
        logger.error(f"Error loading quiz interface: {e}")
        return render(request, 'quiz/error.html', {'error': str(e)})


@login_required
def quiz_results_view(request, quiz_result_id):
    """View quiz results"""
    try:
        quiz_result = get_object_or_404(QuizResult, id=quiz_result_id)
        
        # Ensure user can view this result
        if hasattr(request.user, 'student'):
            if quiz_result.student != request.user.student:
                return render(request, 'quiz/error.html', {'error': 'Access denied'})
        
        quiz = quiz_result.quiz
        questions = QuizQuestion.objects.filter(quiz=quiz)
        
        # Reconstruct detailed results
        question_results = []
        for question in questions:
            user_answer = quiz_result.answers_data.get(str(question.id), '')
            is_correct = user_answer.strip().upper() == question.correct_answer.strip().upper()
            
            question_results.append({
                'question': question,
                'user_answer': user_answer,
                'is_correct': is_correct
            })
        
        context = {
            'quiz_result': quiz_result,
            'quiz': quiz,
            'question_results': question_results,
            'grade': _calculate_grade(quiz_result.accuracy_percentage),
            'passed': quiz_result.accuracy_percentage >= 70
        }
        
        return render(request, 'quiz/results.html', context)
        
    except Exception as e:
        logger.error(f"Error loading quiz results: {e}")
        return render(request, 'quiz/error.html', {'error': str(e)})
