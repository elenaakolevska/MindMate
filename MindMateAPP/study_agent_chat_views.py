"""
Study Agent Chat Views
Handles chat interface and agent interactions
"""

import logging
import json
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import os

from MindMateAPP.agents import build_study_agent_graph

logger = logging.getLogger(__name__)

# Initialize Study Agent (singleton pattern)
_study_agent = None

def get_study_agent():
    """Get or create Study Agent instance"""
    global _study_agent
    if _study_agent is None:
        logger.info("Initializing Study Agent...")
        _study_agent = build_study_agent_graph()
        logger.info("✅ Study Agent initialized")
    return _study_agent


@login_required
def study_agent_chat_view(request):
    """
    Render the Study Agent chat interface
    """
    return render(request, 'chat/study_agent.html', {
        'user': request.user,
        'page_title': 'Study Agent - MindMate'
    })


@require_http_methods(["POST"])
def study_agent_chat_api(request):
    """
    API endpoint for Study Agent chat
    Handles message sending and file uploads
    """
    try:
        # Get message from request
        message = request.POST.get('message', '').strip()
        uploaded_file = request.FILES.get('file')

        if not message and not uploaded_file:
            return JsonResponse({
                'error': 'Пораката или датотеката е задолжителна'
            }, status=400)

        # Handle file upload if present
        extracted_text = None
        if uploaded_file:
            try:
                # Save file temporarily
                file_path = default_storage.save(
                    f'temp/{uploaded_file.name}',
                    ContentFile(uploaded_file.read())
                )

                logger.info(f"File uploaded: {uploaded_file.name} ({uploaded_file.size} bytes)")

                # TODO: Extract text from file (PDF, DOCX, etc.)
                # For now, just acknowledge the upload
                extracted_text = f"Датотеката {uploaded_file.name} е успешно прикачена."

                # Clean up temp file
                default_storage.delete(file_path)

            except Exception as e:
                logger.error(f"Error processing file: {e}")
                return JsonResponse({
                    'error': 'Грешка при обработка на датотеката'
                }, status=500)

        # Prepare message for agent
        agent_message = message
        if extracted_text:
            agent_message = f"{message}\n\n[Прикачена датотека: {uploaded_file.name}]"

        # Get user context
        user_id = request.user.id if request.user.is_authenticated else None
        session_id = request.session.session_key

        # Invoke Study Agent
        logger.info(f"Processing message from user {user_id}: {message[:50]}...")

        agent = get_study_agent()
        result = agent.invoke(
            user_message=agent_message,
            user_id=user_id,
            session_id=session_id
        )

        # Prepare response
        response_data = {
            'response': result.get('response', 'Жалам, не можев да генерирам одговор.'),
            'intent': result.get('intent'),
            'response_type': result.get('response_type'),
            'metadata': {
                'processing_time': result.get('processing_time'),
                'steps_taken': result.get('steps_taken', [])
            }
        }

        # Include additional data based on response type
        if result.get('response_type') == 'quiz' and result.get('generated_quiz'):
            response_data['quiz'] = result['generated_quiz']

        elif result.get('response_type') == 'time_estimation':
            response_data['estimation'] = {
                'hours': result.get('estimated_hours'),
                'breakdown': result.get('time_breakdown'),
                'confidence': result.get('confidence_level')
            }

        elif result.get('response_type') == 'schedule':
            response_data['schedule'] = result.get('schedule')

        logger.info(f"✅ Response generated: {result.get('response')[:50]}...")

        return JsonResponse(response_data)

    except Exception as e:
        logger.error(f"❌ Error in chat API: {e}", exc_info=True)
        return JsonResponse({
            'error': 'Се случи грешка. Ве молиме обидете се повторно.',
            'details': str(e) if request.user.is_staff else None
        }, status=500)


@require_http_methods(["POST"])
def study_agent_stream_api(request):
    """
    Streaming API endpoint for Study Agent
    Returns real-time updates as agent processes the request
    """
    try:
        message = request.POST.get('message', '').strip()

        if not message:
            return JsonResponse({'error': 'Пораката е задолжителна'}, status=400)

        user_id = request.user.id if request.user.is_authenticated else None
        session_id = request.session.session_key

        # TODO: Implement Server-Sent Events (SSE) for streaming
        # For now, return regular response
        agent = get_study_agent()
        result = agent.invoke(
            user_message=message,
            user_id=user_id,
            session_id=session_id
        )

        return JsonResponse({
            'response': result.get('response'),
            'intent': result.get('intent'),
            'steps': result.get('steps_taken', [])
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
        # TODO: Implement chat history storage in database
        # For now, return empty history
        return JsonResponse({
            'history': [],
            'session_id': request.session.session_key
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
        # TODO: Implement history clearing
        return JsonResponse({'success': True})

    except Exception as e:
        logger.error(f"Error clearing chat history: {e}")
        return JsonResponse({'error': str(e)}, status=500)

