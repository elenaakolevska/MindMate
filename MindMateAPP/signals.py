"""
Django signals for MindMate OCR processing.
Auto-triggers OCR when StudyMaterial is saved with a file.
"""

import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from .models import StudyMaterial
from .services.document_preprocessing import process_document
import os

logger = logging.getLogger(__name__)


@receiver(post_save, sender=StudyMaterial)
def process_study_material_ocr(sender, instance, created, **kwargs):
    if not created or not instance.file_path or instance.processing_status != 'pending':
        return
    
    logger.info(f"Starting OCR processing for StudyMaterial ID: {instance.id}, File: {instance.original_filename}")
    try:
        StudyMaterial.objects.filter(id=instance.id).update(
            processing_status='processing'
        )
        # Get the full file path (assuming it's relative to MEDIA_ROOT or absolute)
        file_path = instance.file_path
        if not os.path.isabs(file_path):
            from django.conf import settings
            file_path = os.path.join(settings.MEDIA_ROOT, file_path)
        
        # Check if file exists
        if not os.path.exists(file_path):
            error_msg = f"File not found: {file_path}"
            logger.error(error_msg)
            StudyMaterial.objects.filter(id=instance.id).update(
                processing_status='failed',
                processing_error=error_msg,
                processing_date=timezone.now()
            )
            return
        chunks = process_document(file_path)
        
        if chunks:
            content = '\n\n'.join(chunks)
            final_status = 'completed'
            error_message = ''
            StudyMaterial.objects.filter(id=instance.id).update(
                content=content,
                processing_status=final_status,
                processing_error=error_message,
                processing_date=timezone.now(),
                file_size=os.path.getsize(file_path) if os.path.exists(file_path) else 0,
          
                title=instance.title or instance.original_filename or f"Document {instance.id}"
            )
            
            logger.info(f"OCR processing completed for StudyMaterial ID: {instance.id}. "
                       f"Status: {final_status}, Characters extracted: {len(content)}")
  
        
        else:
            error_msg = "Document processing returned no chunks"
            logger.warning(f"OCR warning for StudyMaterial ID {instance.id}: {error_msg}")
            
            StudyMaterial.objects.filter(id=instance.id).update(
                processing_status='failed',
                processing_error=error_msg,
                processing_date=timezone.now()
            )
        
    except Exception as e:
        error_msg = f"Unexpected error during OCR processing: {str(e)}"
        logger.error(f"OCR error for StudyMaterial ID {instance.id}: {error_msg}")
        
        StudyMaterial.objects.filter(id=instance.id).update(
            processing_status='failed',
            processing_error=error_msg,
            processing_date=timezone.now()
        )
