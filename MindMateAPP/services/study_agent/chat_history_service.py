"""
PostgreSQL-based Chat History Service for RAG System
Uses Django ORM with existing ChatbotInteraction model
"""

import json
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime
from django.utils import timezone
from django.db import transaction
from django.db.models import Q

from ...models import ChatbotInteraction, Student
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

logger = logging.getLogger(__name__)


class PostgresChatHistoryManager:
    
    def __init__(self, bot_type: str = "study_agent"):
        self.bot_type = bot_type
        self.vectorizer = TfidfVectorizer(stop_words='english', max_features=1000)
        
    def create_session(self, student_id: str, session_metadata: Dict[str, Any] = None) -> str:
       
        try:
            student = Student.objects.get(id=student_id)
            session_id = f"session_{student_id}_{int(timezone.now().timestamp())}"
            session_entry = ChatbotInteraction.objects.create(
                student=student,
                bot_type=self.bot_type,
                event_action="session_created",
                message_content=json.dumps({
                    "session_id": session_id,
                    "metadata": session_metadata or {},
                    "created_at": timezone.now().isoformat()
                }),
                response_content="Session created successfully"
            )
            
            logger.info(f"Created new session {session_id} for student {student_id}")
            return session_id
            
        except Student.DoesNotExist:
            logger.error(f"Student with ID {student_id} not found")
            raise ValueError(f"Student with ID {student_id} not found")
        except Exception as e:
            logger.error(f"Error creating session: {e}")
            raise

    def get_sessions(self, student_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent chat sessions for a student
        """
        try:
            student = Student.objects.get(id=student_id)
            
            # Get session creation entries
            session_interactions = ChatbotInteraction.objects.filter(
                student=student,
                bot_type=self.bot_type,
                event_action="session_created"
            ).order_by('-action_time')[:limit]
            
            sessions = []
            for interaction in session_interactions:
                try:
                    message_data = json.loads(interaction.message_content)
                    sessions.append({
                        "session_id": message_data.get("session_id"),
                        "created_at": interaction.action_time.isoformat(),
                        "metadata": message_data.get("metadata", {}),
                        "interaction_id": interaction.id
                    })
                except json.JSONDecodeError:
                    logger.warning(f"Could not parse session data for interaction {interaction.id}")
                    continue
            
            return sessions
            
        except Student.DoesNotExist:
            logger.error(f"Student with ID {student_id} not found")
            return []
        except Exception as e:
            logger.error(f"Error getting sessions: {e}")
            return []

    def add_message(self, student_id: str, session_id: str, message: str, 
                   message_type: str = "user", context: Dict[str, Any] = None) -> str:
        """
        Add a message to the chat history
        """
        try:
            student = Student.objects.get(id=student_id)
            
            # Create message entry
            message_data = {
                "session_id": session_id,
                "message_type": message_type,  # "user" or "assistant"
                "message": message,
                "context": context or {},
                "timestamp": timezone.now().isoformat()
            }
            
            interaction = ChatbotInteraction.objects.create(
                student=student,
                bot_type=self.bot_type,
                event_action=f"message_{message_type}",
                message_content=json.dumps(message_data),
                response_content=""  # Will be filled for assistant messages
            )
            
            logger.info(f"Added {message_type} message to session {session_id}")
            return str(interaction.id)
            
        except Student.DoesNotExist:
            logger.error(f"Student with ID {student_id} not found")
            raise ValueError(f"Student with ID {student_id} not found")
        except Exception as e:
            logger.error(f"Error adding message: {e}")
            raise

    def add_response(self, student_id: str, session_id: str, response: str, 
                    context: Dict[str, Any] = None) -> str:
        """
        Add an assistant response to the chat history
        """
        return self.add_message(student_id, session_id, response, "assistant", context)

    def get_chat_history(self, student_id: str, session_id: str, 
                        limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get chat history for a specific session
        """
        try:
            student = Student.objects.get(id=student_id)
            
            # Get all messages for this session (excluding session_created)
            interactions = ChatbotInteraction.objects.filter(
                student=student,
                bot_type=self.bot_type,
                message_content__contains=f'"session_id": "{session_id}"'
            ).exclude(
                event_action="session_created"
            ).order_by('action_time')[:limit]
            
            chat_history = []
            for interaction in interactions:
                try:
                    message_data = json.loads(interaction.message_content)
                    
                    # Extract message info
                    message_entry = {
                        "id": str(interaction.id),
                        "session_id": session_id,
                        "message_type": message_data.get("message_type", "user"),
                        "message": message_data.get("message", ""),
                        "context": message_data.get("context", {}),
                        "timestamp": interaction.action_time.isoformat(),
                        "action_time": interaction.action_time
                    }
                    
                    chat_history.append(message_entry)
                    
                except json.JSONDecodeError:
                    logger.warning(f"Could not parse message data for interaction {interaction.id}")
                    continue
            
            return sorted(chat_history, key=lambda x: x["action_time"])
            
        except Student.DoesNotExist:
            logger.error(f"Student with ID {student_id} not found")
            return []
        except Exception as e:
            logger.error(f"Error getting chat history: {e}")
            return []

    def get_recent_context(self, student_id: str, session_id: str, 
                          messages_count: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent messages for context
        """
        try:
            full_history = self.get_chat_history(student_id, session_id, limit=100)
            
            # Return the most recent messages
            return full_history[-messages_count:] if full_history else []
            
        except Exception as e:
            logger.error(f"Error getting recent context: {e}")
            return []

    def search_chat_history(self, student_id: str, query: str, 
                           session_id: str = None, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search through chat history using text similarity
        """
        try:
            student = Student.objects.get(id=student_id)
            
            # Base query
            interactions_query = ChatbotInteraction.objects.filter(
                student=student,
                bot_type=self.bot_type
            ).exclude(event_action="session_created")
            
            # Filter by session if provided
            if session_id:
                interactions_query = interactions_query.filter(
                    message_content__contains=f'"session_id": "{session_id}"'
                )
            
            # Get all relevant interactions
            interactions = interactions_query.order_by('-action_time')
            
            # Extract messages and compute similarity
            messages = []
            message_texts = []
            
            for interaction in interactions:
                try:
                    message_data = json.loads(interaction.message_content)
                    message_text = message_data.get("message", "")
                    
                    if message_text:
                        messages.append({
                            "id": str(interaction.id),
                            "message": message_text,
                            "message_type": message_data.get("message_type", "user"),
                            "session_id": message_data.get("session_id"),
                            "timestamp": interaction.action_time.isoformat(),
                            "context": message_data.get("context", {})
                        })
                        message_texts.append(message_text)
                        
                except json.JSONDecodeError:
                    continue
            
            if not message_texts:
                return []
            
            # Compute similarity using TF-IDF
            try:
                # Fit TF-IDF vectorizer on all messages plus query
                all_texts = message_texts + [query]
                tfidf_matrix = self.vectorizer.fit_transform(all_texts)
                
                # Get similarity scores between query and all messages
                query_vector = tfidf_matrix[-1]
                message_vectors = tfidf_matrix[:-1]
                
                similarities = cosine_similarity(query_vector, message_vectors).flatten()
                
                # Create results with similarity scores
                results = []
                for i, message in enumerate(messages):
                    if similarities[i] > 0.1:  # Minimum similarity threshold
                        message["similarity_score"] = float(similarities[i])
                        results.append(message)
                
                # Sort by similarity score and return top results
                results.sort(key=lambda x: x["similarity_score"], reverse=True)
                return results[:limit]
                
            except Exception as e:
                logger.warning(f"TF-IDF search failed, falling back to text search: {e}")
                
                # Fallback to simple text search
                results = []
                query_lower = query.lower()
                for message in messages:
                    if query_lower in message["message"].lower():
                        message["similarity_score"] = 0.5  # Default score for text match
                        results.append(message)
                
                return results[:limit]
            
        except Student.DoesNotExist:
            logger.error(f"Student with ID {student_id} not found")
            return []
        except Exception as e:
            logger.error(f"Error searching chat history: {e}")
            return []

    def delete_session(self, student_id: str, session_id: str) -> bool:
        """
        Delete a chat session and all its messages
        """
        try:
            student = Student.objects.get(id=student_id)
            
            with transaction.atomic():
                # Delete all interactions for this session
                deleted_count = ChatbotInteraction.objects.filter(
                    student=student,
                    bot_type=self.bot_type,
                    message_content__contains=f'"session_id": "{session_id}"'
                ).delete()
                
                logger.info(f"Deleted session {session_id} with {deleted_count[0]} interactions")
                return True
                
        except Student.DoesNotExist:
            logger.error(f"Student with ID {student_id} not found")
            return False
        except Exception as e:
            logger.error(f"Error deleting session: {e}")
            return False

    def get_session_stats(self, student_id: str, session_id: str) -> Dict[str, Any]:
        """
        Get statistics for a chat session
        """
        try:
            student = Student.objects.get(id=student_id)
            
            interactions = ChatbotInteraction.objects.filter(
                student=student,
                bot_type=self.bot_type,
                message_content__contains=f'"session_id": "{session_id}"'
            )
            
            user_messages = 0
            assistant_messages = 0
            total_interactions = 0
            
            first_interaction = None
            last_interaction = None
            
            for interaction in interactions:
                try:
                    message_data = json.loads(interaction.message_content)
                    message_type = message_data.get("message_type")
                    
                    if message_type == "user":
                        user_messages += 1
                    elif message_type == "assistant":
                        assistant_messages += 1
                    
                    total_interactions += 1
                    
                    if first_interaction is None or interaction.action_time < first_interaction:
                        first_interaction = interaction.action_time
                    if last_interaction is None or interaction.action_time > last_interaction:
                        last_interaction = interaction.action_time
                        
                except json.JSONDecodeError:
                    continue
            
            duration = None
            if first_interaction and last_interaction:
                duration = (last_interaction - first_interaction).total_seconds()
            
            return {
                "session_id": session_id,
                "total_interactions": total_interactions,
                "user_messages": user_messages,
                "assistant_messages": assistant_messages,
                "duration_seconds": duration,
                "first_interaction": first_interaction.isoformat() if first_interaction else None,
                "last_interaction": last_interaction.isoformat() if last_interaction else None
            }
            
        except Student.DoesNotExist:
            logger.error(f"Student with ID {student_id} not found")
            return {}
        except Exception as e:
            logger.error(f"Error getting session stats: {e}")
            return {}

    def cleanup_old_sessions(self, student_id: str, days_old: int = 30) -> int:
        """
        Clean up old chat sessions
        """
        try:
            student = Student.objects.get(id=student_id)
            
            cutoff_date = timezone.now() - timezone.timedelta(days=days_old)
            
            with transaction.atomic():
                deleted_count = ChatbotInteraction.objects.filter(
                    student=student,
                    bot_type=self.bot_type,
                    action_time__lt=cutoff_date
                ).delete()
                
                logger.info(f"Cleaned up {deleted_count[0]} old interactions for student {student_id}")
                return deleted_count[0]
                
        except Student.DoesNotExist:
            logger.error(f"Student with ID {student_id} not found")
            return 0
        except Exception as e:
            logger.error(f"Error cleaning up old sessions: {e}")
            return 0
