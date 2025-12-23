import logging
import os
import secrets
from datetime import datetime
from typing import List, Dict, Any, Tuple
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
from MindMateAPP.models import StudyMaterial
from ..preprocessing.document_preprocessing import process_document

logger = logging.getLogger(__name__)

# Global singleton for embedding function to prevent multiple model loads
_embedding_function = None

def get_embedding_function():
    """Get or create singleton embedding function to prevent memory leaks"""
    global _embedding_function
    if _embedding_function is None:
        logger.info("Loading SentenceTransformer embedding model (one-time initialization)")
        _embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
    return _embedding_function


class VectorStoreService:
    def __init__(self, persist_directory_path: str = None):
        if persist_directory_path is None:
            from django.conf import settings
            project_root = getattr(settings, 'BASE_DIR', os.path.dirname(os.path.dirname(__file__)))
            persist_directory_path = os.path.join(project_root, 'chroma_db')
        
        # Use lazy-loaded singleton embedding function
        self._embedding_function = None
        self.persist_directory_path = persist_directory_path
        os.makedirs(persist_directory_path, exist_ok=True)
        
        self.client = chromadb.PersistentClient(
            path=persist_directory_path,
            settings=Settings(anonymized_telemetry=False, allow_reset=True)
        )
    
    @property
    def default_embedding_function(self):
        """Lazy load embedding function only when needed"""
        if self._embedding_function is None:
            self._embedding_function = get_embedding_function()
        return self._embedding_function
   
   
    def create_or_get_collection(self, collection_name: str):
        return self.client.get_or_create_collection(name=collection_name, embedding_function=self.default_embedding_function)
    
    
    def process_document(self, document_id):
        doc = StudyMaterial.objects.get(id=document_id)
        student = doc.student
        student_id = student.id if student else "unknown"
        chunks = process_document(document_id)
        if chunks is None:
            logger.error(f"Failed to process document with ID: {document_id}")
            return []
        
        # Save the combined content to the StudyMaterial model
        combined_content = " ".join(chunks)
        doc.content = combined_content
        doc.processing_status = 'completed'
        doc.processing_date = datetime.utcnow()
        doc.save()
        
        metadata = {
            "document_id": document_id,
            "student_id": student_id,
            "processed_at": datetime.utcnow().isoformat(),
            "file_size": len(combined_content),
            "subject": doc.subject
        }
        collection = self.create_or_get_collection(collection_name=f"student_{student_id}_materials")
        for i, chunk in enumerate(chunks):
            collection.add(
                documents=[chunk],
                metadatas=[{**metadata, "chunk_index": i}],
                ids=[f"{document_id}_chunk_{i}_{secrets.token_hex(4)}"]
            )
        logger.info(f"Added {len(chunks)} chunks to collection 'student_{student_id}_materials' for document ID: {document_id}")
        return chunks
    

    def process_multiple_documents(self, document_ids: List[str]) -> Dict[str, Any]:
        for document_id in document_ids:
            chunks = self.process_document(document_id)
            if chunks is None:
                logger.error(f"Processing failed for document ID {document_id}. No chunks were created.")

    
    def query_collection(self, student_id, query: str, n_results: int = 10) -> List[Dict[str, Any]]:
        collection_name = f"student_{student_id}_materials"
        try:
            collection = self.client.get_collection(name=collection_name)
        except:
            logger.warning(f"Collection '{collection_name}' does not exist.")
            return []  
        results = collection.query(
            query_texts=[query],
            n_results=n_results
        )
        formatted_results = []
        for i, (doc, metadata) in enumerate(zip(results['documents'][0], results['metadatas'][0])):
            formatted_results.append({
                "document": doc,
                "metadata": metadata,
                "distance": results['distances'][0][i]  # Individual distance for this result
            })
        return formatted_results
    

    def get_chunked_document(self, document_id) -> List[Dict[str, Any]]:
        student_id = StudyMaterial.objects.get(id=document_id).student.id
        collection_name = f"student_{student_id}_materials"
        try:
            collection = self.client.get_collection(name=collection_name)
        except:
            logger.warning(f"Collection '{collection_name}' does not exist.")
            return [] 
        return collection.get(where={"document_id": document_id})


    def delete_document_chunks(self, document_id):
        student_id = StudyMaterial.objects.get(id=document_id).student.id
        collection_name = f"student_{student_id}_materials"
        try:
            collection = self.client.get_collection(name=collection_name)
        except:
            logger.warning(f"Collection '{collection_name}' does not exist.")
            return False  
        try:
            collection.delete(where={"document_id": str(document_id)})
            return True
        except Exception as e:
            logger.error(f"Error deleting chunks for document ID {document_id}: {e}")
            return False


    def delete_collection_for_student(self, student_id):
        collection_name = f"student_{student_id}_materials"
        try:
            self.client.delete_collection(name=collection_name)
            logger.info(f"Deleted collection '{collection_name}' for student ID: {student_id}")
        except Exception as e:
            logger.error(f"Error deleting collection '{collection_name}': {e}")
    