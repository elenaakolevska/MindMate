"""
RAG Retriever with PostgreSQL Chat History
Uses Django ORM instead of MongoDB for chat history storage
"""

import logging
import requests
from typing import List, Dict, Any, Optional, Tuple
import json

from .vector_store import VectorStoreService
from .chat_history_service import PostgresChatHistoryManager
from ..models import Student, StudyMaterial, ChatbotInteraction

logger = logging.getLogger(__name__)


class PostgresRAGRetriever:
    """
    RAG (Retrieval Augmented Generation) system using PostgreSQL for chat history
    """
    
    def __init__(self, student_id: str):
        """
        Initialize the RAG retriever for a specific student
        
        Args:
            student_id: The ID of the student using the system
        """
        self.vector_store = VectorStoreService()
        self.student_id = student_id
        self.bot_type = "study_agent"  # Set bot_type for chat history
        self.chat_manager = PostgresChatHistoryManager(bot_type=self.bot_type)
        self.session_id = self._initialize_session()
        
        # Initialize Ollama client configuration (same as quiz generator)
        self.ollama_url = "http://host.docker.internal:11434"  # Docker-compatible URL
        self.model_name = "llama3.2:3b"  # Same model as quiz generator
        
        # Verify student exists
        try:
            self.student = Student.objects.get(id=student_id)
        except Student.DoesNotExist:
            raise ValueError(f"Student with ID {student_id} not found")

    def _initialize_session(self) -> str:
        """Initialize or get existing chat session"""
        try:
            # Get recent sessions for this student
            sessions = self.chat_manager.get_sessions(self.student_id, limit=1)
            
            if sessions:
                # Use the most recent session
                session_id = sessions[0]["session_id"]
                logger.info(f"Using existing session: {session_id}")
            else:
                # Create new session
                session_id = self.chat_manager.create_session(
                    self.student_id,
                    {"created_by": "rag_retriever", "type": "study_session"}
                )
                logger.info(f"Created new session: {session_id}")
            
            return session_id
            
        except Exception as e:
            logger.error(f"Error initializing session: {e}")
            # Create a fallback session ID
            import time
            return f"session_{self.student_id}_{int(time.time())}"

    def query(self, user_question: str, max_context_chunks: int = 5, 
             context_window: int = 10) -> Dict[str, Any]:
        """
        Process a user question using RAG approach with PostgreSQL chat history
        
        Args:
            user_question: The question from the user
            max_context_chunks: Maximum number of document chunks to retrieve
            context_window: Number of recent chat messages to include for context
            
        Returns:
            Dict containing response, sources, and metadata
        """
        try:
            logger.info(f"Processing query for student {self.student_id}: {user_question}")
            
            # Step 1: Store the user question in chat history
            self.chat_manager.add_message(
                self.student_id, 
                self.session_id, 
                user_question, 
                "user"
            )
            
            # Step 2: Get recent chat context
            recent_context = self.chat_manager.get_recent_context(
                self.student_id, 
                self.session_id, 
                context_window
            )
            
            # Step 3: Search chat history for relevant previous discussions
            chat_search_results = self.chat_manager.search_chat_history(
                self.student_id, 
                user_question, 
                session_id=None,  # Search across all sessions
                limit=3
            ) or []  # Ensure we have a list, not None
            
            # Step 4: Retrieve relevant document chunks from vector store
            document_results = self.vector_store.query_collection(
                student_id=int(self.student_id),
                query=user_question,
                n_results=max_context_chunks
            )
            
            # Convert VectorStoreService format to expected format
            formatted_document_results = {
                "documents": [[item["document"] for item in document_results]],
                "metadatas": [[item["metadata"] for item in document_results]],
                "distances": [[0.0] * len(document_results)]  # Placeholder distances
            }
            
            # Step 5: Build comprehensive context
            context = self._build_context(
                user_question=user_question,
                recent_chat=recent_context,
                chat_history_matches=chat_search_results,
                document_chunks=formatted_document_results
            )
            
            # Step 6: Generate response using Ollama
            response = self._generate_response(context)
            
            # Step 7: Store assistant response in chat history
            self.chat_manager.add_response(
                self.student_id,
                self.session_id,
                response,
                {
                    "document_sources": len(document_results.get("documents", [])),
                    "chat_context_used": len(recent_context),
                    "chat_history_matches": len(chat_search_results)
                }
            )
            
            # Step 8: Prepare response data
            response_data = {
                "response": response,
                "sources": self._extract_sources(formatted_document_results),
                "context_used": {
                    "recent_chat_messages": len(recent_context),
                    "document_chunks": len(formatted_document_results.get("documents", [[]])[0]),
                    "chat_history_matches": len(chat_search_results)
                },
                "session_id": self.session_id,
                "student_id": self.student_id
            }
            
            logger.info(f"Successfully processed query with {len(formatted_document_results.get('documents', [[]])[0])} document sources")
            return response_data
            
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            error_response = f"I'm sorry, I encountered an error processing your question: {str(e)}"
            
            # Still try to store the error response
            try:
                self.chat_manager.add_response(
                    self.student_id,
                    self.session_id,
                    error_response,
                    {"error": str(e)}
                )
            except:
                pass  # Don't fail on logging errors
            
            return {
                "response": error_response,
                "sources": [],
                "context_used": {"error": str(e)},
                "session_id": self.session_id,
                "student_id": self.student_id
            }

    def _build_context(self, user_question: str, recent_chat: List[Dict], 
                      chat_history_matches: List[Dict], 
                      document_chunks: Dict) -> str:
        """Build comprehensive context for the LLM"""
        
        context_parts = []
        
        # Add document context
        if document_chunks.get("documents"):
            context_parts.append("=== RELEVANT STUDY MATERIALS ===")
            for i, (doc, metadata) in enumerate(zip(
                document_chunks["documents"][0], 
                document_chunks["metadatas"][0] or []
            )):
                source_info = ""
                if metadata and isinstance(metadata, dict):
                    source_info = f" (Source: {metadata.get('source', 'Unknown')})"
                context_parts.append(f"Document {i+1}{source_info}:\n{doc}")
            context_parts.append("")
        
        # Add relevant chat history
        if chat_history_matches:
            context_parts.append("=== RELEVANT PREVIOUS DISCUSSIONS ===")
            for match in chat_history_matches:
                context_parts.append(
                    f"Previous {match['message_type']}: {match['message']} "
                    f"(Similarity: {match.get('similarity_score', 0):.2f})"
                )
            context_parts.append("")
        
        # Add recent conversation context
        if recent_chat:
            context_parts.append("=== RECENT CONVERSATION ===")
            for message in recent_chat[-5:]:  # Last 5 messages
                role = "Student" if message["message_type"] == "user" else "Assistant"
                context_parts.append(f"{role}: {message['message']}")
            context_parts.append("")
        
        # Add current question
        context_parts.append("=== CURRENT QUESTION ===")
        context_parts.append(f"Student: {user_question}")
        context_parts.append("")
        
        # Add instructions
        context_parts.append("=== INSTRUCTIONS ===")
        context_parts.append(
            "You are a helpful study assistant. Use the provided study materials and conversation context "
            "to give a comprehensive, accurate answer. If the materials don't contain relevant information, "
            "say so and provide general guidance based on your knowledge. Always be encouraging and educational."
        )
        
        return "\n".join(context_parts)

    def _generate_response(self, context: str) -> str:
        """Generate response using Ollama local LLM"""
        try:
            # Prepare the prompt for Ollama
            prompt = {
                "model": self.model_name,
                "prompt": context,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "max_tokens": 1000
                }
            }
            
            # Make request to Ollama
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json=prompt,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("response", "I apologize, but I couldn't generate a response.")
            else:
                logger.error(f"Ollama API error: {response.status_code} - {response.text}")
                return self._fallback_response()
                
        except requests.RequestException as e:
            logger.error(f"Error connecting to Ollama: {e}")
            return self._fallback_response()
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return self._fallback_response()

    def _fallback_response(self) -> str:
        """Generate a fallback response when Ollama is not available"""
        return (
            "I'm currently having trouble connecting to my AI model to generate a detailed response. "
            "However, based on the context available, I can see that you're asking about your study materials. "
            "Please ensure that Ollama is running locally, or check back in a moment. "
            "In the meantime, you might want to review the relevant sections in your uploaded documents."
        )

    def _extract_sources(self, document_results: Dict) -> List[Dict[str, Any]]:
        """Extract source information from document results"""
        sources = []
        
        if not document_results.get("metadatas"):
            return sources
        
        metadatas = document_results["metadatas"][0] if document_results["metadatas"] else []
        for metadata in metadatas:
            if metadata and isinstance(metadata, dict):
                sources.append({
                    "source": metadata.get("source", "Unknown"),
                    "chunk_id": metadata.get("chunk_id", ""),
                    "document_id": metadata.get("document_id", ""),
                    "page": metadata.get("page", "")
                })
        
        return sources

    def get_chat_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get chat history for the current session"""
        return self.chat_manager.get_chat_history(
            self.student_id, 
            self.session_id, 
            limit
        )

    def search_documents(self, query: str, max_results: int = 10) -> Dict[str, Any]:
        """Search only in documents (no chat context)"""
        try:
            results = self.vector_store.query_collection(
                student_id=int(self.student_id),
                query=query,
                n_results=max_results
            )
            
            # Convert to expected format
            formatted_results = {
                "documents": [[item["document"] for item in results]],
                "metadatas": [[item["metadata"] for item in results]],
                "distances": [[0.0] * len(results)]
            }
            
            return {
                "results": formatted_results,
                "sources": self._extract_sources(formatted_results),
                "query": query
            }
            
        except Exception as e:
            logger.error(f"Error searching documents: {e}")
            return {"error": str(e), "query": query}

    def get_session_info(self) -> Dict[str, Any]:
        """Get information about the current session"""
        try:
            stats = self.chat_manager.get_session_stats(self.student_id, self.session_id)
            return {
                "session_id": self.session_id,
                "student_id": self.student_id,
                "student_name": self.student.full_name,
                "stats": stats
            }
        except Exception as e:
            logger.error(f"Error getting session info: {e}")
            return {"error": str(e)}

    def clear_session(self) -> bool:
        """Clear the current session and start a new one"""
        try:
            # Delete current session
            self.chat_manager.delete_session(self.student_id, self.session_id)
            
            # Initialize new session
            self.session_id = self.chat_manager.create_session(
                self.student_id,
                {"created_by": "rag_retriever", "type": "study_session", "cleared": True}
            )
            
            logger.info(f"Cleared session and created new session: {self.session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error clearing session: {e}")
            return False

    def get_student_documents(self) -> List[Dict[str, Any]]:
        """Get list of documents uploaded by the student"""
        try:
            materials = StudyMaterial.objects.filter(
                student=self.student,
                processing_status='completed'
            ).order_by('-upload_date')
            
            documents = []
            for material in materials:
                documents.append({
                    "id": material.id,
                    "title": material.title,
                    "filename": material.original_filename,
                    "type": material.type,
                    "upload_date": material.upload_date.isoformat(),
                    "subject": material.subject,
                    "collection_name": material.vector_collection_name
                })
            
            return documents
            
        except Exception as e:
            logger.error(f"Error getting student documents: {e}")
            return []

    def analyze_conversation_topics(self) -> Dict[str, Any]:
        """Analyze topics discussed in recent conversations"""
        try:
            # Get recent chat history
            recent_messages = self.chat_manager.get_chat_history(
                self.student_id, 
                self.session_id, 
                limit=100
            )
            
            if not recent_messages:
                return {"topics": [], "message_count": 0}
            
            # Simple topic extraction (you could enhance this with more sophisticated NLP)
            user_messages = [msg["message"] for msg in recent_messages if msg["message_type"] == "user"]
            
            # Count common topics/subjects mentioned
            topics = {}
            common_subjects = [
                "math", "science", "history", "english", "physics", "chemistry", 
                "biology", "literature", "programming", "computer", "economics"
            ]
            
            for message in user_messages:
                message_lower = message.lower()
                for subject in common_subjects:
                    if subject in message_lower:
                        topics[subject] = topics.get(subject, 0) + 1
            
            # Sort topics by frequency
            sorted_topics = sorted(topics.items(), key=lambda x: x[1], reverse=True)
            
            return {
                "topics": sorted_topics[:5],  # Top 5 topics
                "message_count": len(user_messages),
                "session_id": self.session_id
            }
            
        except Exception as e:
            logger.error(f"Error analyzing conversation topics: {e}")
            return {"error": str(e)}

    def search_with_context_ranking(self, query: str, n_results: int = 10, 
                                   subject_filter: str = None) -> Dict[str, Any]:
        """
        Enhanced search with context ranking - compatibility method for study_agent_views
        """
        try:
            # Use the existing search_documents method
            results = self.search_documents(query, n_results)
            
            # Format results to match expected format
            if "error" in results:
                return {"error": results["error"]}
            
            # Transform to expected format
            document_results = results.get("results", {})
            formatted_results = []
            
            if document_results.get("documents"):
                for i, (doc, metadata) in enumerate(zip(
                    document_results["documents"][0], 
                    document_results["metadatas"][0] or [{}] * len(document_results["documents"][0])
                )):
                    # Filter by subject if specified
                    if subject_filter:
                        doc_subject = metadata.get("subject", "").lower()
                        if subject_filter.lower() not in doc_subject:
                            continue
                    
                    formatted_results.append({
                        "content": doc,
                        "metadata": metadata,
                        "score": document_results.get("distances", [[0] * len(document_results["documents"][0])])[0][i],
                        "source": metadata.get("source", "Unknown")
                    })
            
            return {
                "results": formatted_results,
                "total_results": len(formatted_results),
                "query": query
            }
            
        except Exception as e:
            logger.error(f"Error in search_with_context_ranking: {e}")
            return {"error": str(e)}

    def retrieve_context(self, student_id: str, query: str, top_k: int = 5, 
                        subject_filter: str = None) -> Dict[str, Any]:
        """
        Retrieve context for a query - compatibility method for study_agent_views
        """
        try:
            # Use search_with_context_ranking
            search_results = self.search_with_context_ranking(
                query, n_results=top_k, subject_filter=subject_filter
            )
            
            if "error" in search_results:
                return search_results
            
            # Format for context usage
            context_chunks = []
            for result in search_results.get("results", []):
                context_chunks.append({
                    "content": result["content"],
                    "source": result["source"],
                    "metadata": result["metadata"],
                    "relevance_score": 1.0 - result["score"]  # Convert distance to similarity
                })
            
            return {
                "context_chunks": context_chunks,
                "total_chunks": len(context_chunks),
                "query": query,
                "student_id": student_id
            }
            
        except Exception as e:
            logger.error(f"Error retrieving context: {e}")
            return {"error": str(e)}

    def get_search_stats(self, student_id: str) -> Dict[str, Any]:
        """
        Get search statistics for a student - compatibility method
        """
        try:
            student = Student.objects.get(id=student_id)
            
            # Get statistics from chat interactions
            total_queries = ChatbotInteraction.objects.filter(
                student=student,
                bot_type=self.bot_type,
                event_action="message_user"
            ).count()
            
            total_responses = ChatbotInteraction.objects.filter(
                student=student,
                bot_type=self.bot_type,
                event_action="message_assistant"
            ).count()
            
            # Get recent activity (last 7 days)
            from django.utils import timezone
            from datetime import timedelta
            
            recent_date = timezone.now() - timedelta(days=7)
            recent_queries = ChatbotInteraction.objects.filter(
                student=student,
                bot_type=self.bot_type,
                event_action="message_user",
                action_time__gte=recent_date
            ).count()
            
            # Get document count
            document_count = StudyMaterial.objects.filter(
                student=student,
                processing_status='completed'
            ).count()
            
            return {
                "total_queries": total_queries,
                "total_responses": total_responses,
                "recent_queries_7_days": recent_queries,
                "available_documents": document_count,
                "student_id": student_id
            }
            
        except Student.DoesNotExist:
            logger.error(f"Student with ID {student_id} not found")
            return {"error": f"Student with ID {student_id} not found"}
        except Exception as e:
            logger.error(f"Error getting search stats: {e}")
            return {"error": str(e)}

    def get_available_subjects(self, student_id: str) -> List[str]:
        """
        Get available subjects from student's documents
        """
        try:
            student = Student.objects.get(id=student_id)
            
            # Get subjects from uploaded materials
            materials = StudyMaterial.objects.filter(
                student=student,
                processing_status='completed'
            ).exclude(subject__isnull=True).exclude(subject__exact="")
            
            subjects = set()
            for material in materials:
                if material.subject:
                    subjects.add(material.subject.strip())
            
            # Also analyze chat history for mentioned subjects
            try:
                recent_messages = self.chat_manager.get_chat_history(
                    student_id, self.session_id, limit=100
                )
                
                # Simple subject detection in messages
                common_subjects = [
                    "mathematics", "math", "science", "history", "english", 
                    "physics", "chemistry", "biology", "literature", "programming", 
                    "computer science", "economics", "psychology", "sociology"
                ]
                
                for message in recent_messages:
                    message_lower = message["message"].lower()
                    for subject in common_subjects:
                        if subject in message_lower:
                            subjects.add(subject.title())
                            
            except Exception:
                pass  # Don't fail if chat history analysis fails
            
            return sorted(list(subjects))
            
        except Student.DoesNotExist:
            logger.error(f"Student with ID {student_id} not found")
            return []
        except Exception as e:
            logger.error(f"Error getting available subjects: {e}")
            return []
