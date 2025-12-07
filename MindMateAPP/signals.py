import logging
import os
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from .models import StudyMaterial, Student
from .services.document_preprocessing import process_document
from .services.vector_store import get_vector_store

logger = logging.getLogger(__name__)


@receiver(post_save, sender=StudyMaterial)
def process_study_material_ocr(sender, instance, created, **kwargs):
    if not created or not instance.file_path or instance.processing_status != 'pending':
        return
    
    try:
        StudyMaterial.objects.filter(id=instance.id).update(processing_status='processing')
        
        file_path = instance.file_path
        if not os.path.isabs(file_path):
            from django.conf import settings
            file_path = os.path.join(settings.MEDIA_ROOT, file_path)
        
        if not os.path.exists(file_path):
            error_msg = f"File not found: {file_path}"
            StudyMaterial.objects.filter(id=instance.id).update(
                processing_status='failed',
                processing_error=error_msg,
                processing_date=timezone.now()
            )
            return

        chunks = process_document(file_path)
        
        if chunks:
            content = '\n\n'.join(chunks)
            StudyMaterial.objects.filter(id=instance.id).update(
                content=content,
                processing_status='completed',
                processing_error='',
                processing_date=timezone.now(),
                file_size=os.path.getsize(file_path) if os.path.exists(file_path) else 0,
                title=instance.title or instance.original_filename or f"Document {instance.id}"
            )
            
            try:
                vector_store = get_vector_store()
                metadata = {
                    "subject": instance.subject,
                    "upload_date": str(instance.upload_date),
                    "filename": instance.original_filename,
                    "document_type": instance.type,
                    "title": instance.title or instance.original_filename
                }
                
                vector_store.store_document_chunks(
                    student_id=instance.student.id,
                    document_id=instance.id,
                    chunks=chunks,
                    metadata=metadata
                )
            except Exception as e:
                logger.error(f"Vector store error for document {instance.id}: {e}")
        else:
            StudyMaterial.objects.filter(id=instance.id).update(
                processing_status='failed',
                processing_error="Document processing returned no chunks",
                processing_date=timezone.now()
            )
        
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
        
        vector_store = get_vector_store()
        vector_store.delete_document(document_id=document_id)
            
    except Exception as e:
        logger.error(f"Vector store cleanup error for document {getattr(instance, 'id', 'unknown')}: {e}")


@receiver(post_delete, sender=Student)
def cleanup_student_vector_store(sender, instance, **kwargs):
    try:
        student_id = instance.id
        if student_id is None:
            return
        
        vector_store = get_vector_store()
        vector_store.delete_student_data(student_id)
            
    except Exception as e:
        logger.error(f"Vector store student cleanup error for student {getattr(instance, 'id', 'unknown')}: {e}")
