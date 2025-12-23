import logging
import os
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from .models import StudyMaterial, Student
from .services.study_agent.vector_store import VectorStoreService

logger = logging.getLogger(__name__)


@receiver(post_save, sender=StudyMaterial)
def process_study_materials(sender, instance, created, **kwargs):
    if not created or not instance.file_path or instance.processing_status != 'pending':
        return
    try:
        StudyMaterial.objects.filter(id=instance.id).update(processing_status='processing')
        
        try:
            vector_store = VectorStoreService()
            vector_store.process_document(instance.id)
        except Exception as e:
            logger.error(f"Vector store error for document {instance.id}: {e}")
        
    except Exception as e:
        StudyMaterial.objects.filter(id=instance.id).update(
            processing_status='failed',
            processing_error=f"Unexpected error during OCR processing: {str(e)}",
            processing_date=timezone.now()
        )


@receiver(post_delete, sender=StudyMaterial)
def cleanup_study_material_vector_store(sender, instance, **kwargs):
    try:
        document_id = instance.id
        if document_id is None:
            return
        
        vector_store = VectorStoreService()
        vector_store.delete_document_chunks(document_id=document_id)
            
    except Exception as e:
        logger.error(f"Vector store cleanup error for document {getattr(instance, 'id', 'unknown')}: {e}")


@receiver(post_delete, sender=Student)
def cleanup_student_vector_store(sender, instance, **kwargs):
    try:
        student_id = instance.id
        if student_id is None:
            return
        
        vector_store = VectorStoreService()
        vector_store.delete_collection_for_student(student_id)
            
    except Exception as e:
        logger.error(f"Vector store student cleanup error for student {getattr(instance, 'id', 'unknown')}: {e}")
