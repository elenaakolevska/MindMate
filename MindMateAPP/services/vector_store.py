import logging
import os
import secrets
from datetime import datetime
from typing import List, Dict, Any, Tuple
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
from MindMateAPP.models import StudyMaterial
from .document_preprocessing import process_document

logger = logging.getLogger(__name__)


class VectorStoreService:
    def __init__(self, persist_directory_path: str = None):
        if persist_directory_path is None:
            from django.conf import settings
            project_root = getattr(settings, 'BASE_DIR', os.path.dirname(os.path.dirname(__file__)))
            persist_directory_path = os.path.join(project_root, 'chroma_db')
        self.default_embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
        os.makedirs(persist_directory_path, exist_ok=True)
        
        self.client = chromadb.PersistentClient(
            path=persist_directory_path,
            settings=Settings(anonymized_telemetry=False, allow_reset=True)
        )
   
   
    def create_or_get_collection(self, collection_name: str):
        return self.client.get_or_create_collection(name=collection_name, embedding_function=self.default_embedding_function)
    
    
    def process_document(self, document_id):
        doc = StudyMaterial.objects.get(id=document_id)
        student = doc.student
        student_id = student.id if student else "unknown"
        chunks = process_document(document_id)
        metadata = {
            "document_id": document_id,
            "student_id": student_id,
            "processed_at": datetime.utcnow().isoformat(),
            "file_size": len(str(chunks)) if chunks else 0,  # Use chunks length instead of file size
            "subject": doc.subject
        }
        if chunks is None:
            logger.error(f"Failed to process document with ID: {document_id}")
            return []
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
        for doc, metadata in zip(results['documents'][0], results['metadatas'][0]):
            formatted_results.append({
                "document": doc,
                "metadata": metadata
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
    