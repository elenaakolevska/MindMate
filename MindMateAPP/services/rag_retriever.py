import logging
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from django.utils import timezone
from .vector_store import get_vector_store

logger = logging.getLogger(__name__)


@dataclass
class RetrievalResult:
    """Data class for storing retrieval results with metadata"""
    text: str
    document_id: int
    document_title: str
    subject: str
    upload_date: datetime
    chunk_index: int
    similarity_score: float
    relevance_score: float
    recency_score: float
    final_score: float
    metadata: Dict[str, Any]


class RAGRetriever:
    """
    RAG Retrieval System for finding relevant context from uploaded materials.
    Implements semantic search with relevance scoring, subject filtering, and recency ranking.
    """
    
    def __init__(self, relevance_threshold: float = 0.3, recency_weight: float = 0.3, similarity_weight: float = 0.7):
        """
        Initialize RAG Retriever with configurable weights and thresholds.
        
        Args:
            relevance_threshold: Minimum relevance score for including results
            recency_weight: Weight for recency scoring (0-1)
            similarity_weight: Weight for similarity scoring (0-1, should sum with recency_weight to 1)
        """
        self.vector_store = get_vector_store()
        self.relevance_threshold = relevance_threshold
        self.recency_weight = recency_weight
        self.similarity_weight = similarity_weight
        
        if abs(self.recency_weight + self.similarity_weight - 1.0) > 0.01:
            logger.warning("Recency and similarity weights don't sum to 1.0. Normalizing...")
            total_weight = self.recency_weight + self.similarity_weight
            self.recency_weight /= total_weight
            self.similarity_weight /= total_weight

    def retrieve_context(
        self,
        student_id: int,
        query: str,
        top_k: int = 5,
        subject_filter: Optional[str] = None,
        min_relevance: Optional[float] = None
    ) -> List[RetrievalResult]:
        """
        Retrieve relevant context from uploaded materials using semantic search.
        
        Args:
            student_id: ID of the student
            query: Search query string
            top_k: Number of top results to return (default: 5)
            subject_filter: Optional subject to filter by
            min_relevance: Minimum relevance threshold (overrides default)
            
        Returns:
            List of RetrievalResult objects sorted by relevance
        """
        start_time = time.time()
        
        try:
            # Use provided threshold or default
            threshold = min_relevance if min_relevance is not None else self.relevance_threshold
            
            # Prepare filter metadata
            filter_metadata = {}
            if subject_filter:
                filter_metadata["subject"] = subject_filter
            
            # Perform vector search with increased limit for filtering
            search_limit = min(top_k * 3, 50)  # Search more to allow for filtering
            search_results = self.vector_store.search_similar_content(
                student_id=student_id,
                query=query,
                limit=search_limit,
                filter_metadata=filter_metadata if filter_metadata else None
            )
            
            if not search_results:
                logger.info(f"No search results found for query: {query}")
                return []
            
            # Convert to RetrievalResult objects with enhanced scoring
            retrieval_results = []
            for result in search_results:
                try:
                    # Get document metadata
                    doc_metadata = self._get_document_metadata(result.get("document_id"))
                    if not doc_metadata:
                        continue
                    
                    # Calculate enhanced scores
                    similarity_score = result.get("similarity_score", 0.0)
                    recency_score = self._calculate_recency_score(doc_metadata["upload_date"])
                    relevance_score = self._calculate_relevance_score(
                        similarity_score, recency_score
                    )
                    
                    # Apply relevance threshold
                    if relevance_score < threshold:
                        continue
                    
                    # Create RetrievalResult object
                    retrieval_result = RetrievalResult(
                        text=result["text"],
                        document_id=result.get("document_id", 0),
                        document_title=doc_metadata.get("title", "Unknown Document"),
                        subject=doc_metadata.get("subject", ""),
                        upload_date=doc_metadata["upload_date"],
                        chunk_index=result.get("metadata", {}).get("chunk_index", 0),
                        similarity_score=similarity_score,
                        relevance_score=relevance_score,
                        recency_score=recency_score,
                        final_score=relevance_score,  # Could be enhanced with additional factors
                        metadata=result.get("metadata", {})
                    )
                    
                    retrieval_results.append(retrieval_result)
                    
                except Exception as e:
                    logger.warning(f"Error processing search result: {e}")
                    continue
            
            # Sort by final score (highest first)
            retrieval_results.sort(key=lambda x: x.final_score, reverse=True)
            
            # Return top K results
            final_results = retrieval_results[:top_k]
            
            # Log performance
            elapsed_time = time.time() - start_time
            logger.info(
                f"Retrieved {len(final_results)} relevant chunks for query '{query}' "
                f"in {elapsed_time:.3f} seconds (student: {student_id})"
            )
            
            return final_results
            
        except Exception as e:
            logger.error(f"Error in retrieve_context: {e}")
            return []

    def _get_document_metadata(self, document_id: int) -> Optional[Dict[str, Any]]:
        """Get metadata for a document from the database."""
        try:
            from ..models import StudyMaterial
            
            study_material = StudyMaterial.objects.get(id=document_id)
            return {
                "title": study_material.title or study_material.original_filename or "Untitled",
                "subject": study_material.subject or "",
                "upload_date": study_material.upload_date,
                "type": study_material.type,
                "original_filename": study_material.original_filename or "",
                "processing_status": study_material.processing_status
            }
        except Exception as e:
            logger.warning(f"Could not get metadata for document {document_id}: {e}")
            return None

    def _calculate_recency_score(self, upload_date: datetime) -> float:
        """
        Calculate recency score based on how recent the upload is.
        
        Args:
            upload_date: When the document was uploaded
            
        Returns:
            Recency score between 0 and 1 (1 = most recent)
        """
        try:
            # Handle timezone-aware datetime
            if upload_date.tzinfo is None:
                upload_date = timezone.make_aware(upload_date)
            
            now = timezone.now()
            days_old = (now - upload_date).days
            
            # Recency scoring: exponential decay
            # Recent uploads (0-7 days) get high scores
            # Moderate uploads (7-30 days) get medium scores  
            # Older uploads get lower scores
            if days_old <= 7:
                return 1.0
            elif days_old <= 30:
                return 0.8 * (1.0 - (days_old - 7) / 23)  # Linear decay from 0.8 to 0.0
            elif days_old <= 90:
                return 0.3 * (1.0 - (days_old - 30) / 60)  # Linear decay from 0.3 to 0.0
            else:
                return 0.1  # Minimum score for very old documents
                
        except Exception as e:
            logger.warning(f"Error calculating recency score: {e}")
            return 0.5  # Default middle score

    def _calculate_relevance_score(self, similarity_score: float, recency_score: float) -> float:
        """
        Calculate combined relevance score using similarity and recency.
        
        Args:
            similarity_score: Semantic similarity score (0-1)
            recency_score: Recency score (0-1)
            
        Returns:
            Combined relevance score (0-1)
        """
        return (
            self.similarity_weight * similarity_score +
            self.recency_weight * recency_score
        )

    def get_available_subjects(self, student_id: int) -> List[str]:
        """
        Get list of available subjects for a student.
        
        Args:
            student_id: ID of the student
            
        Returns:
            List of subject names
        """
        try:
            from ..models import StudyMaterial
            
            subjects = StudyMaterial.objects.filter(
                student_id=student_id,
                subject__isnull=False
            ).exclude(
                subject=""
            ).values_list("subject", flat=True).distinct()
            
            return list(subjects)
            
        except Exception as e:
            logger.error(f"Error getting available subjects: {e}")
            return []

    def search_with_context_ranking(
        self,
        student_id: int,
        query: str,
        top_k: int = 5,
        subject_filter: Optional[str] = None,
        context_window: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Enhanced search that includes context chunks around relevant results.
        
        Args:
            student_id: ID of the student
            query: Search query string
            top_k: Number of top results to return
            subject_filter: Optional subject to filter by
            context_window: Number of adjacent chunks to include on each side
            
        Returns:
            List of search results with context
        """
        try:
            # Get base results
            base_results = self.retrieve_context(
                student_id=student_id,
                query=query,
                top_k=top_k,
                subject_filter=subject_filter
            )
            
            if not base_results:
                return []
            
            # Enhance results with context
            enhanced_results = []
            for result in base_results:
                try:
                    # Get surrounding context chunks
                    context_chunks = self._get_context_chunks(
                        document_id=result.document_id,
                        chunk_index=result.chunk_index,
                        window_size=context_window
                    )
                    
                    enhanced_result = {
                        "primary_chunk": {
                            "text": result.text,
                            "chunk_index": result.chunk_index,
                            "similarity_score": result.similarity_score,
                            "relevance_score": result.relevance_score
                        },
                        "context_chunks": context_chunks,
                        "document_info": {
                            "id": result.document_id,
                            "title": result.document_title,
                            "subject": result.subject,
                            "upload_date": result.upload_date.isoformat()
                        },
                        "final_score": result.final_score
                    }
                    
                    enhanced_results.append(enhanced_result)
                    
                except Exception as e:
                    logger.warning(f"Error enhancing result with context: {e}")
                    # Fallback to basic result
                    enhanced_results.append({
                        "primary_chunk": {
                            "text": result.text,
                            "chunk_index": result.chunk_index,
                            "similarity_score": result.similarity_score,
                            "relevance_score": result.relevance_score
                        },
                        "context_chunks": [],
                        "document_info": {
                            "id": result.document_id,
                            "title": result.document_title,
                            "subject": result.subject,
                            "upload_date": result.upload_date.isoformat()
                        },
                        "final_score": result.final_score
                    })
            
            return enhanced_results
            
        except Exception as e:
            logger.error(f"Error in search_with_context_ranking: {e}")
            return []

    def _get_context_chunks(
        self,
        document_id: int,
        chunk_index: int,
        window_size: int
    ) -> List[Dict[str, Any]]:
        """
        Get context chunks around a specific chunk.
        
        Args:
            document_id: ID of the document
            chunk_index: Index of the target chunk
            window_size: Number of chunks to include on each side
            
        Returns:
            List of context chunks
        """
        try:
            # Get all chunks for the document
            all_chunks = self.vector_store.get_document_chunks(document_id)
            if not all_chunks:
                return []
            
            # Sort by chunk index
            all_chunks.sort(key=lambda x: x["metadata"].get("chunk_index", 0))
            
            # Find the target chunk and surrounding context
            context_chunks = []
            start_idx = max(0, chunk_index - window_size)
            end_idx = min(len(all_chunks), chunk_index + window_size + 1)
            
            for i in range(start_idx, end_idx):
                if i < len(all_chunks):
                    chunk = all_chunks[i]
                    context_chunks.append({
                        "text": chunk["text"],
                        "chunk_index": chunk["metadata"].get("chunk_index", i),
                        "is_primary": chunk["metadata"].get("chunk_index", i) == chunk_index
                    })
            
            return context_chunks
            
        except Exception as e:
            logger.warning(f"Error getting context chunks: {e}")
            return []

    def get_search_stats(self, student_id: int) -> Dict[str, Any]:
        """
        Get statistics about the searchable content for a student.
        
        Args:
            student_id: ID of the student
            
        Returns:
            Dictionary with search statistics
        """
        try:
            stats = self.vector_store.get_collection_stats(student_id)
            
            # Add subjects information
            available_subjects = self.get_available_subjects(student_id)
            
            # Get recent upload activity
            from ..models import StudyMaterial
            recent_uploads = StudyMaterial.objects.filter(
                student_id=student_id,
                upload_date__gte=timezone.now() - timedelta(days=30),
                processing_status='completed'
            ).count()
            
            stats.update({
                "available_subjects": available_subjects,
                "recent_uploads_30d": recent_uploads,
                "is_searchable": stats.get("total_chunks", 0) > 0
            })
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting search stats: {e}")
            return {"error": str(e)}


# Singleton instance
_rag_retriever_instance = None

def get_rag_retriever() -> RAGRetriever:
    """Get singleton instance of RAGRetriever."""
    global _rag_retriever_instance
    if _rag_retriever_instance is None:
        _rag_retriever_instance = RAGRetriever()
    return _rag_retriever_instance
