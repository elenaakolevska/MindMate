"""
Study Agent Views - RAGRetriever Implementation
Handles study agent interface and interactions using RAGRetriever directly
"""

import logging
import json
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required

from MindMateAPP.models import Student
from MindMateAPP.services.study_agent.rag_retriever import RAGRetriever
from MindMateAPP.services.study_agent.quiz_generator import QuizGenerator

logger = logging.getLogger(__name__)

def get_rag_retriever(student_id: int) -> RAGRetriever:
    """Get RAG Retriever instance for student - create new instance each time to prevent memory leaks"""
    logger.info(f"Creating RAG Retriever instance for student {student_id}")
    return RAGRetriever(student_id=str(student_id))

def get_quiz_generator(student_id: int) -> QuizGenerator:
    """Get Quiz Generator instance for student - create new instance each time to prevent memory leaks"""
    from django.conf import settings
    logger.info(f"Creating Quiz Generator instance for student {student_id}")
    ollama_url = getattr(settings, 'OLLAMA_URL', 'http://host.docker.internal:11434')
    rag_retriever = get_rag_retriever(student_id)
    return QuizGenerator(ollama_url=ollama_url, rag_retriever=rag_retriever)


@login_required
def study_agent_view(request):
    """
    Render the Study Agent interface
    """
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        return redirect('mindmate:student_preferences')

    return render(request, 'study_agent/index.html', {
        'user': request.user,
        'student': student,
        'page_title': 'Study Agent - MindMate'
    })


@login_required
def study_agent_chat_view(request):
    """
    Render the Study Agent chat interface
    """
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        return redirect('mindmate:student_preferences')

    # Get current session ID to load previous messages
    rag_retriever = get_rag_retriever(student.id)
    current_session_id = rag_retriever.session_id

    return render(request, 'study_agent/chat.html', {
        'user': request.user,
        'student': student,
        'current_session_id': current_session_id,
        'page_title': 'Study Agent Chat - MindMate'
    })


@require_http_methods(["POST"])
def study_agent_api(request):
    """
    API endpoint for Study Agent interactions
    """
    try:
        message = request.POST.get('message', '').strip()
        uploaded_file = request.FILES.get('file')

        if not message and not uploaded_file:
            return JsonResponse({
                'error': 'Message or file is required'
            }, status=400)

        # Get student - handle case where student doesn't exist
        try:
            student = Student.objects.get(user=request.user)
        except Student.DoesNotExist:
            return JsonResponse({
                'error': 'Student profile not found. Please complete your student preferences first.',
                'redirect': '/preferences/'
            }, status=400)

        rag_retriever = get_rag_retriever(student.id)

        # Prepare message for agent
        agent_message = message
        if uploaded_file:
            agent_message = f"{message}\n\n[Uploaded file: {uploaded_file.name}]"

        # Determine intent and response type
        response_type = 'chat'
        intent = 'general_chat'

        # Simple intent classification based on keywords
        message_lower = message.lower()
        if any(word in message_lower for word in ['квиз', 'quiz', 'тест', 'test']):
            response_type = 'quiz'
            intent = 'quiz_generation'
        elif any(word in message_lower for word in ['време', 'time', 'проценка']):
            response_type = 'time_estimation'
            intent = 'time_estimation'
        elif any(word in message_lower for word in ['распоред', 'schedule', 'планирање']):
            response_type = 'schedule'
            intent = 'schedule_planning'

        # Generate response using RAG
        logger.info(f"Processing message from user {request.user.id}: {message[:50]}...")

        if response_type == 'quiz':
            # Generate quiz
            quiz_data = rag_retriever.generate_quiz_from_documents(
                question_count=10,  # Default
                material_ids=[]  # TODO: Get from request or detect from message
            )
            response_data = {
                'response': f"Generated quiz with {len(quiz_data.get('questions', []))} questions.",
                'intent': intent,
                'response_type': response_type,
                'quiz': quiz_data,
                'metadata': {
                    'processing_time': None,
                    'steps_taken': ['rag_retrieval', 'quiz_generation']
                }
            }
        else:
            # Regular chat response with RAG
            response_text = rag_retriever.generate_response(agent_message)
            response_data = {
                'response': response_text,
                'intent': intent,
                'response_type': response_type,
                'metadata': {
                    'processing_time': None,
                    'steps_taken': ['rag_retrieval', 'llm_generation']
                }
            }

        logger.info(f"✅ Response generated: {response_data['response'][:50]}...")

        return JsonResponse(response_data)

    except Exception as e:
        logger.error(f"❌ Error in study agent API: {e}", exc_info=True)
        return JsonResponse({
            'error': 'An error occurred. Please try again.',
            'details': str(e) if request.user.is_staff else None
        }, status=500)


@require_http_methods(["POST"])
def study_agent_chat_api(request):
    """
    API endpoint for Study Agent chat
    """
    try:
        # Handle both JSON and FormData requests
        if request.content_type == 'application/json':
            import json
            data = json.loads(request.body)
            message = data.get('message', '').strip()
        else:
            # FormData request
            message = request.POST.get('message', '').strip()

        if not message:
            return JsonResponse({
                'error': 'Message is required'
            }, status=400)

        # Get student - handle case where student doesn't exist
        try:
            student = Student.objects.get(user=request.user)
        except Student.DoesNotExist:
            return JsonResponse({
                'error': 'Student profile not found. Please complete your student preferences first.',
                'redirect': '/preferences/'
            }, status=400)

        # Get student and RAG retriever
        rag_retriever = get_rag_retriever(student.id)

        logger.info(f"Processing chat message from user {request.user.id}: {message[:50]}...")

        # Generate response using RAG
        response_text = rag_retriever.generate_response(message)

        response_data = {
            'response': response_text,
            'session_id': rag_retriever.session_id,  # Include session_id for frontend
            'intent': 'chat',
            'response_type': 'chat',
            'metadata': {
                'processing_time': None,
                'steps_taken': ['rag_retrieval', 'llm_generation']
            }
        }

        logger.info(f"✅ Chat response generated for session {rag_retriever.session_id}")

        return JsonResponse(response_data)

    except Exception as e:
        logger.error(f"❌ Error in chat API: {e}", exc_info=True)
        return JsonResponse({
            'error': 'An error occurred',
            'details': str(e) if request.user.is_staff else None
        }, status=500)


@require_http_methods(["POST"])
def study_agent_stream_api(request):
    """
    Streaming API endpoint for Study Agent
    """
    try:
        # Handle both JSON and FormData requests
        if request.content_type == 'application/json':
            import json
            data = json.loads(request.body)
            message = data.get('message', '').strip()
        else:
            # FormData request
            message = request.POST.get('message', '').strip()

        if not message:
            return JsonResponse({'error': 'Message is required'}, status=400)

        # Get student - handle case where student doesn't exist
        try:
            student = Student.objects.get(user=request.user)
        except Student.DoesNotExist:
            return JsonResponse({
                'error': 'Student profile not found. Please complete your student preferences first.',
                'redirect': '/preferences/'
            }, status=400)

        # Get student and RAG retriever
        rag_retriever = get_rag_retriever(student.id)

        # For now, return regular response (streaming can be added later)
        response_text = rag_retriever.generate_response(message)

        return JsonResponse({
            'response': response_text,
            'intent': 'chat',
            'steps': ['rag_retrieval', 'llm_generation']
        })

    except Exception as e:
        logger.error(f"Error in streaming API: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def chat_history_api(request):
    """
    Get chat history for current user
    """
    try:
        # Get student - handle case where student doesn't exist
        try:
            student = Student.objects.get(user=request.user)
        except Student.DoesNotExist:
            return JsonResponse({
                'error': 'Student profile not found. Please complete your student preferences first.',
                'redirect': '/preferences/'
            }, status=400)

        rag_retriever = get_rag_retriever(student.id)

        # Check if specific session_id is requested
        requested_session_id = request.GET.get('session_id')
        if requested_session_id:
            # Get history for specific session
            history = rag_retriever.get_session_history(requested_session_id, limit=50)
        else:
            # Get general chat history (all sessions)
            history = rag_retriever.get_chat_history(limit=50)

        # Format for frontend - match expected format
        formatted_history = []
        for entry in history:
            formatted_history.append({
                'id': entry.get('id'),
                'content': entry.get('message', ''),  # Frontend expects 'content'
                'is_user_message': entry.get('message_type', 'user') == 'user',  # Frontend expects 'is_user_message'
                'timestamp': entry.get('timestamp'),
                'session_id': entry.get('session_id')
            })

        # Also return available sessions for sidebar
        sessions = rag_retriever.get_sessions()
        formatted_sessions = []
        for session in sessions:
            # Get last message time from session
            session_history = rag_retriever.get_session_history(session.get('session_id'), limit=1)
            last_message_time = session_history[0].get('timestamp') if session_history else session.get('created_at')
            
            formatted_sessions.append({
                'id': session.get('session_id'),
                'title': session.get('title', 'New Chat'),
                'created_at': session.get('created_at'),
                'updated_at': last_message_time
            })

        return JsonResponse({
            'history': formatted_history,
            'sessions': formatted_sessions,
            'current_session_id': rag_retriever.session_id
        })

    except Exception as e:
        logger.error(f"Error fetching chat history: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["POST"])
def clear_chat_history_api(request):
    """
    Clear chat history for current session
    """
    try:
        # Note: RAGRetriever doesn't have a clear method yet
        # This would need to be implemented in the RAGRetriever class
        return JsonResponse({'success': True})

    except Exception as e:
        logger.error(f"Error clearing chat history: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["DELETE"])
def delete_session_api(request, session_id):
    """
    Delete a specific chat session and all its messages
    """
    try:
        student = Student.objects.get(user=request.user)
        rag_retriever = get_rag_retriever(student.id)
        
        # Delete the session using the chat history manager
        success = rag_retriever.chat_manager.delete_session(student.id, session_id)
        
        if success:
            logger.info(f"Deleted session {session_id} for student {student.id}")
            return JsonResponse({'success': True, 'message': 'Session deleted successfully'})
        else:
            return JsonResponse({'success': False, 'error': 'Failed to delete session'}, status=400)

    except Student.DoesNotExist:
        return JsonResponse({'error': 'Student profile not found'}, status=404)
    except Exception as e:
        logger.error(f"Error deleting session: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)

@require_http_methods(["POST"])
def create_new_session_api(request):
    """
    Create a new chat session for the current user
    """
    try:
        student = Student.objects.get(user=request.user)
        rag_retriever = get_rag_retriever(student.id)
        
        # Create a new session
        new_session_id = rag_retriever.open_new_session()
        
        logger.info(f"Created new session {new_session_id} for student {student.id}")
        
        return JsonResponse({
            'success': True,
            'session_id': new_session_id,
            'message': 'New session created successfully'
        })
    
    except Student.DoesNotExist:
        return JsonResponse({
            'error': 'Student profile not found. Please complete your student preferences first.',
            'redirect': '/preferences/'
        }, status=400)
    except Exception as e:
        logger.error(f"Error creating new session: {e}", exc_info=True)
        return JsonResponse({
            'error': 'An error occurred while creating a new session',
            'details': str(e) if request.user.is_staff else None
        }, status=500)
