import logging
import os
import secrets
from datetime import datetime
from typing import List, Dict, Any, Tuple
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class VectorStoreService:
    def __init__(self, persist_directory: str = None):
        if persist_directory is None:
            from django.conf import settings
            project_root = getattr(settings, 'BASE_DIR', os.path.dirname(os.path.dirname(__file__)))
            persist_directory = os.path.join(project_root, 'chroma_db')
        
        os.makedirs(persist_directory, exist_ok=True)
        
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(anonymized_telemetry=False, allow_reset=True)
        )
        
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

    def _generate_collection_name(self) -> str:
        return f"collection_{secrets.token_hex(16)}"

    def _get_or_create_collection_for_document(self, document_id: int):
        from ..models import StudyMaterial
        
        study_material = StudyMaterial.objects.get(id=document_id)
        
        if not study_material.vector_collection_name:
            collection_name = self._generate_collection_name()
            StudyMaterial.objects.filter(id=document_id).update(
                vector_collection_name=collection_name
            )
        else:
            collection_name = study_material.vector_collection_name
        
        try:
            collection = self.client.get_collection(name=collection_name, embedding_function=None)
        except Exception:
            collection = self.client.create_collection(name=collection_name, embedding_function=None)
        
        return collection, collection_name

    def store_document_chunks(self, document_id: int, student_id: int, chunks: List[str], metadata: Dict[str, Any] = None) -> bool:
        try:
            if not chunks:
                return True
            
            collection, collection_name = self._get_or_create_collection_for_document(document_id)
            
            embeddings = self.embedding_model.encode(chunks).tolist()
            
            ids = [f"doc_{document_id}_chunk_{i}_{secrets.token_hex(8)}" for i in range(len(chunks))]
            
            chunk_metadata = []
            for i, chunk in enumerate(chunks):
                meta = {
                    "document_id": document_id,
                    "student_id": student_id,
                    "chunk_index": i,
                    "created_at": str(datetime.now()),
                    **(metadata or {})
                }
                chunk_metadata.append(meta)
            
            collection.add(
                embeddings=embeddings,
                documents=chunks,
                metadatas=chunk_metadata,
                ids=ids
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to store chunks for document {document_id}: {e}")
            return False

    def get_document_chunks(self, document_id: int) -> List[Dict[str, Any]]:
        try:
            from ..models import StudyMaterial
            
            study_material = StudyMaterial.objects.get(id=document_id)
            if not study_material.vector_collection_name:
                return []
            
            try:
                collection = self.client.get_collection(name=study_material.vector_collection_name)
            except Exception:
                return []
            
            results = collection.get(
                where={"document_id": document_id},
                include=["documents", "metadatas", "embeddings"]
            )
            
            if not results or not results["documents"]:
                return []
            
            chunks = []
            for i in range(len(results["documents"])):
                chunk_data = {
                    "id": results["ids"][i] if "ids" in results else f"chunk_{i}",
                    "text": results["documents"][i],
                    "metadata": results["metadatas"][i] if "metadatas" in results else {},
                    "embedding": results["embeddings"][i] if "embeddings" in results else None
                }
                chunks.append(chunk_data)
            
            chunks.sort(key=lambda x: x["metadata"].get("chunk_index", 0))
            return chunks
            
        except Exception as e:
            logger.error(f"Failed to retrieve chunks for document {document_id}: {e}")
            return []

    def delete_document(self, document_id: int) -> bool:
        try:
            from ..models import StudyMaterial
            
            try:
                study_material = StudyMaterial.objects.get(id=document_id)
                if not study_material.vector_collection_name:
                    return True
                
                collection_name = study_material.vector_collection_name
            except StudyMaterial.DoesNotExist:
                return True
            
            try:
                collection = self.client.get_collection(name=collection_name)
            except Exception:
                study_material.vector_collection_name = None
                study_material.save(update_fields=['vector_collection_name'])
                return True
            
            results = collection.get(
                where={"document_id": document_id},
                include=[]
            )
            
            if results and results.get("ids"):
                collection.delete(ids=results["ids"])
                
                remaining_count = collection.count()
                if remaining_count == 0:
                    self.client.delete_collection(name=collection_name)
            
            study_material.vector_collection_name = None
            study_material.save(update_fields=['vector_collection_name'])
            
            return True
                
        except Exception as e:
            logger.error(f"Failed to delete document {document_id} from vector store: {e}")
            return False

    def delete_student_data(self, student_id: int) -> bool:
        try:
            from ..models import StudyMaterial
            
            study_materials = StudyMaterial.objects.filter(
                student_id=student_id,
                vector_collection_name__isnull=False
            ).exclude(vector_collection_name='')
            
            for study_material in study_materials:
                collection_name = study_material.vector_collection_name
                
                try:
                    collection = self.client.get_collection(name=collection_name)
                    
                    results = collection.get(
                        where={"student_id": student_id},
                        include=[]
                    )
                    
                    if results and results.get("ids"):
                        collection.delete(ids=results["ids"])
                        
                        remaining_count = collection.count()
                        if remaining_count == 0:
                            self.client.delete_collection(name=collection_name)
                    
                    study_material.vector_collection_name = None
                    study_material.save(update_fields=['vector_collection_name'])
                    
                except Exception as e:
                    logger.warning(f"Failed to delete data from collection {collection_name}: {e}")
                    continue
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete student data for student {student_id}: {e}")
            return False

    def search_similar_content(self, student_id: int, query: str, limit: int = 10, filter_metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        try:
            from ..models import StudyMaterial
            
            study_materials = StudyMaterial.objects.filter(
                student_id=student_id,
                vector_collection_name__isnull=False
            ).exclude(vector_collection_name='')
            
            if not study_materials.exists():
                return []
            
            query_embedding = self.embedding_model.encode([query]).tolist()[0]
            all_results = []
            
            for study_material in study_materials:
                collection_name = study_material.vector_collection_name
                
                try:
                    collection = self.client.get_collection(name=collection_name)
                    
                    # Build proper ChromaDB where clause with $and operator
                    base_filter = {"student_id": student_id}
                    if filter_metadata:
                        # ChromaDB requires logical operators for multiple conditions
                        conditions = [{"student_id": {"$eq": student_id}}]
                        for key, value in filter_metadata.items():
                            conditions.append({key: {"$eq": value}})
                        where_clause = {"$and": conditions}
                    else:
                        where_clause = base_filter
                    
                    results = collection.query(
                        query_embeddings=[query_embedding],
                        n_results=limit,
                        where=where_clause,
                        include=["documents", "metadatas", "distances"]
                    )
                    
                    if results and results["documents"] and results["documents"][0]:
                        documents = results["documents"][0]
                        metadatas = results["metadatas"][0] if results["metadatas"] else []
                        distances = results["distances"][0] if results["distances"] else []
                        
                        for i in range(len(documents)):
                            result = {
                                "text": documents[i],
                                "metadata": metadatas[i] if i < len(metadatas) else {},
                                "similarity_score": max(0.0, 1 - distances[i]) if i < len(distances) else 0.0,
                                "document_id": metadatas[i].get("document_id") if i < len(metadatas) else None
                            }
                            all_results.append(result)
                            
                except Exception as e:
                    continue
            
            if not all_results:
                return []
            
            all_results.sort(key=lambda x: x["similarity_score"], reverse=True)
            return all_results[:limit]
            
        except Exception as e:
            logger.error(f"Failed to search similar content: {e}")
            return []

    def get_collection_stats(self, student_id: int) -> Dict[str, Any]:
        try:
            from ..models import StudyMaterial
            
            study_materials = StudyMaterial.objects.filter(
                student_id=student_id,
                vector_collection_name__isnull=False
            ).exclude(vector_collection_name='')
            
            if not study_materials.exists():
                return {
                    "student_id": student_id,
                    "total_collections": 0,
                    "total_chunks": 0,
                    "unique_documents": 0,
                    "subjects": []
                }
            
            total_chunks = 0
            document_ids = set()
            subjects = set()
            
            for study_material in study_materials:
                collection_name = study_material.vector_collection_name
                
                try:
                    collection = self.client.get_collection(name=collection_name)
                    
                    results = collection.get(
                        where={"student_id": student_id},
                        include=["metadatas"]
                    )
                    
                    collection_chunks = len(results["ids"]) if results["ids"] else 0
                    total_chunks += collection_chunks
                    
                    if results["metadatas"]:
                        for metadata in results["metadatas"]:
                            if "document_id" in metadata:
                                document_ids.add(metadata["document_id"])
                            if "subject" in metadata:
                                subjects.add(metadata["subject"])
                    
                except Exception:
                    continue
            
            return {
                "student_id": student_id,
                "total_collections": study_materials.count(),
                "total_chunks": total_chunks,
                "unique_documents": len(document_ids),
                "subjects": list(subjects)
            }
            
        except Exception as e:
            logger.error(f"Failed to get collection stats for student {student_id}: {e}")
            return {"error": str(e)}


_vector_store_instance = None

def get_vector_store() -> VectorStoreService:
    global _vector_store_instance
    if _vector_store_instance is None:
        _vector_store_instance = VectorStoreService()
    return _vector_store_instance
