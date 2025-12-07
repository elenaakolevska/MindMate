# Temporary file for delete document view

from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.apps import apps
import logging

# Dynamically resolve models to avoid static "Import '.models' could not be resolved" errors.
# This uses the current package name as the Django app label.
_app_label = (__package__.split('.')[-1] if __package__ else None) or (__name__.split('.')[0] if __name__ else None)
try:
    Student = apps.get_model(_app_label, 'Student')
    StudyMaterial = apps.get_model(_app_label, 'StudyMaterial')
except Exception as e:
    raise ImportError(f"Could not import Student and StudyMaterial models for app '{_app_label}': {e}")

logger = logging.getLogger(__name__)

@login_required
@csrf_exempt
@require_http_methods(["DELETE"])
def delete_document(request, document_id):
    """Delete a document"""
    try:
        student = Student.objects.get(user=request.user)
        
        # Get the document
        try:
            document = StudyMaterial.objects.get(id=document_id, student=student)
        except StudyMaterial.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Document not found'
            }, status=404)
        
        # Delete file from disk if it exists
        if document.file_path:
            import os
            from django.conf import settings
            full_path = os.path.join(settings.MEDIA_ROOT, document.file_path)
            if os.path.exists(full_path):
                try:
                    os.remove(full_path)
                except Exception as e:
                    logger.warning(f"Could not delete file {full_path}: {e}")
        
        # Delete from database
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
