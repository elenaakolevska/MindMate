import logging
import requests
from typing import List, Dict, Any
from MindMateAPP.services.study_agent.vector_store import VectorStoreService
from MindMateAPP.services.study_agent.chat_history_service import PostgresChatHistoryManager
from MindMateAPP.models import Student
logger = logging.getLogger(__name__)

class RAGRetriever:

    def __init__(self, student_id: str):
        
        self.vector_store = VectorStoreService()
        self.student_id = student_id
        self.bot_type = "study_agent"  # Set bot_type for chat history
        self.chat_manager = PostgresChatHistoryManager(bot_type=self.bot_type)
        self.session_id = self._initialize_session()
        self.fallback_response = (
            "I'm currently having trouble connecting to my AI model to generate a detailed response. "
            "However, based on the context available, I can see that you're asking about your study materials. "
            "Please ensure that Ollama is running locally, or check back in a moment. "
            "In the meantime, you might want to review the relevant sections in your uploaded documents."
        )
        self.ollama_url = "http://host.docker.internal:11434"  # Docker-compatible URL
        self.model_name = "qwen2.5:7b"  
        
        # Remove QuizGenerator initialization to prevent circular dependency and memory issues
        # QuizGenerator will be created only when needed in views
        
        # Verify student exists
        try:
            self.student = Student.objects.get(id=student_id)
        except Student.DoesNotExist:
            raise ValueError(f"Student with ID {student_id} not found")
    
    def _initialize_chat_manager(self):
        """Initialize the MongoDB chat history manager only."""
        from .chat_history_service import PostgresChatHistoryManager
        return PostgresChatHistoryManager()
    
    def _initialize_session(self) -> str:
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

    def open_new_session(self) -> str:
        session_id = self.chat_manager.create_session(
            self.student_id,
            {"created_by": "rag_retriever", "type": "study_session"}
        )
        logger.info(f"Created new session: {session_id}")
        # Update the current session_id
        self.session_id = session_id
        return session_id

    #Utilities for Chat and Chat History
    def get_sessions(self):
        """Return all sessions for the current user as a list of dicts."""
        try:
            sessions = self.chat_manager.get_sessions(self.student_id)
            return sessions if sessions else []
        except Exception as e:
            print(f"Error retrieving sessions: {e}")
            return []
        
    def get_chat_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get chat history for the current session"""
        return self.chat_manager.get_chat_history(
            self.student_id, 
            self.session_id, 
            limit
        )
    
    def get_session_history(self, session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get chat history for a specific session"""
        return self.chat_manager.get_chat_history(
            self.student_id, 
            session_id, 
            limit
        )
    

    #Querying and Response Generation Methods
    def _improve_query(self, query: str, is_interactive: bool = False) -> str:
        prompt_text = (
            "You are an assistant that is a part of a RAG system. Your task is to rewrite vague or ambiguous questions to be more specific and helpful for document search."
            "Rewrite the following question to be as clear, specific, and context-rich as possible for a document retrieval system. "
            "Do not answer the question, just rewrite it.\n"
            f"Original: {query}\nImproved:"
        )
        prompt = {
                "model": self.model_name,
                "prompt": prompt_text,
                "stream": False,
                "options": {
                    "temperature": 0.3,
                    "top_p": 0.9,
                    "max_tokens": 8192,
                    "num_predict": 1024
                }
            }
        
        try:
            completion = requests.post(
                f"{self.ollama_url}/api/generate",
                json=prompt,
                timeout=90
            )
            if completion.status_code == 200:
                response_json = completion.json()
                improved_query = response_json.get("response", "").strip()
                if improved_query:
                    return improved_query
                else:
                    return query
        except Exception:
            pass
        return query
    
    def get_document_context(self, query: str, n_results: int = 5) -> str:
        """Retrieve relevant document chunks and build context string."""
        results = self.vector_store.query_collection(
            self.student_id, query, n_results=n_results
        )
        
        if not results:
            return ""
        
        context_parts = []
        for result in results:
            doc_text = result["document"]
            metadata = result["metadata"]
            source = metadata.get("source", "Unknown Source")
            chunk_index = metadata.get("chunk_index", "N/A")
            context_parts.append(f"Source: {source}, Chunk: {chunk_index}\n{doc_text}\n")
        
        context_string = "\n---\n".join(context_parts)
        return context_string

    def _get_relevant_conversation_history(self, query, limit: int = 5) -> str:
        """Retrieve recent chat history and format it."""
        history = self.chat_manager.search_chat_history(self.student_id, query=query, session_id=self.session_id, limit=limit)
        history_parts = []
        for entry in history:
            role = entry.get("message_type", "user")
            content = entry.get("message", "")
            history_parts.append(f"{role.capitalize()}: {content}")
        history_string = "\n".join(history_parts)
        return history_string

    def _build_prompt(self, query, context_string: str, history_text: str = "") -> str:
        """Build the system message for the LLM."""
        
        return f"""You are a knowledgeable AI assistant that can answer questions about literature, science, and various other topics. 

When answering:
- Respond in the SAME language as the user's question (Macedonian for Macedonian questions, English for English questions)
- Use the provided context to give accurate, detailed responses. Be specific and informative.
- If previous conversation history is available, reference it when relevant
- Use ONLY the provided context and conversation history to answer questions. If you don't know the answer, state that clearly.
- Provide ONLY a direct answer - do not add extra text or follow-up questions outside your response
- Keep your response focused and concise
- If the question is vague or ambiguous, ask for clarification

Context:
{context_string}

History:
{history_text}

If you find conflicting information in the context, use the most recent information to answer the question.

Question: {query}

Please provide your answer directly without any additional formatting or follow-up questions:"""

    def generate_response(self, query: str) -> str:
        """Generate response using Ollama."""
        print("Generating response...")
        try:
            self.chat_manager.add_message(
                student_id=self.student_id,
                session_id=self.session_id,
                message=query,
                message_type="user")
        except Exception as e:
            logger.error(f"Failed to add user message to chat history: {e}")
        
        try:
            context_string = self.get_document_context(query, n_results=5)
            history = self._get_relevant_conversation_history(query, limit=5)
            improved_query = self._improve_query(query)  
            prompt_text = self._build_prompt(improved_query, context_string, history)
            
            prompt = {
                "model": self.model_name,
                "prompt": prompt_text,
                "stream": False,
                "options": {
                    "temperature": 0.3,
                    "top_p": 0.9,
                    "max_tokens": 8192,
                    "num_predict": 2048
                }
            }
            
            completion = requests.post(
                f"{self.ollama_url}/api/generate",
                json=prompt,
                timeout=120
            )
            
            if completion.status_code == 200:
                print("Response received from Ollama.")
                response_json = completion.json()
                response_text = response_json.get("response", "").strip()
                
                if response_text:
                    # Clean up the response - no longer expecting JSON format
                    final_response = response_text.strip()
                    
                    # Remove any JSON artifacts if they accidentally appear
                    if final_response.startswith('{') and '"response"' in final_response:
                        try:
                            import json
                            # If it's still JSON format, extract the response field
                            parsed = json.loads(final_response)
                            if isinstance(parsed, dict) and 'response' in parsed:
                                final_response = parsed['response']
                        except (json.JSONDecodeError, Exception):
                            # If JSON parsing fails, use the text as is
                            pass
                    
                    # Store response in chat history
                    try:
                        self.chat_manager.add_message(
                            student_id=self.student_id,
                            session_id=self.session_id,
                            message=final_response,
                            message_type="assistant")
                    except Exception as e:
                        logger.error(f"Failed to store response in chat history: {e}")
                    
                    return final_response
                else:
                    return self.fallback_response
            else:
                logger.error(f"Ollama API returned status {completion.status_code}: {completion.text}")
                return self.fallback_response
                
        except requests.exceptions.Timeout:
            logger.error("Ollama request timed out")
            return "Жалам, барањето траеше премногу долго. Ве молиме обидете се повторно."
        except requests.exceptions.ConnectionError:
            logger.error("Could not connect to Ollama")
            return "Не можам да се поврзам со AI моделот. Проверете дали Ollama работи."
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return self.fallback_response



    def get_available_subjects(self, student_id: int) -> List[str]:
        """Get list of available subjects for the student"""
        try:
            # Get all documents for the student
            from MindMateAPP.models import StudyMaterial
            documents = StudyMaterial.objects.filter(student_id=student_id)
            
            subjects = set()
            for doc in documents:
                if doc.subject:
                    subjects.add(doc.subject.lower().strip())
            
            return list(subjects)
            
        except Exception as e:
            logger.error(f"Error getting available subjects: {e}")
            return []

    def get_search_stats(self, student_id: int) -> Dict[str, Any]:
        """Get search statistics for the student"""
        try:
            from MindMateAPP.models import StudyMaterial
            from datetime import datetime, timedelta
            
            # Get document counts
            total_documents = StudyMaterial.objects.filter(student_id=student_id).count()
            
            # Get recent uploads (last 30 days)
            thirty_days_ago = datetime.now() - timedelta(days=30)
            recent_uploads = StudyMaterial.objects.filter(
                student_id=student_id,
                upload_date__gte=thirty_days_ago
            ).count()
            
            # Get available subjects
            subjects = self.get_available_subjects(student_id)
            
            # Try to get collection info from vector store
            try:
                collection_name = f"student_{student_id}_materials"
                collection = self.vector_store.client.get_collection(name=collection_name)
                total_chunks = collection.count()
            except:
                total_chunks = 0
            
            return {
                "student_id": student_id,
                "total_collections": 1 if total_documents > 0 else 0,
                "total_chunks": total_chunks,
                "unique_documents": total_documents,
                "available_subjects": subjects,
                "recent_uploads_30d": recent_uploads,
                "is_searchable": total_chunks > 0
            }
            
        except Exception as e:
            logger.error(f"Error getting search stats: {e}")
            return {
                "student_id": student_id,
                "total_collections": 0,
                "total_chunks": 0,
                "unique_documents": 0,
                "available_subjects": [],
                "recent_uploads_30d": 0,
                "is_searchable": False
            }

    def generate_quiz_from_documents(self, question_count: int, material_ids: List[int]) -> Dict:
        #TODO question count and material ids should be sent from frontend
        from MindMateAPP.services.study_agent.quiz_generator import QuizGenerationOptions, QuizGenerator
        
        # Create QuizGenerator instance only when needed to prevent memory issues
        quiz_generator = QuizGenerator(ollama_url=self.ollama_url)
        
        options = QuizGenerationOptions(
            questions_count=question_count,
            material_ids=material_ids
        )
        quiz, questions = quiz_generator.generate_quiz(
            student_id=int(self.student_id),
            questions_count=options.questions_count,
            material_ids=options.material_ids
        )
        return {"quiz": quiz, "questions": questions}
        
    
    def summarize_document(self, document: str) -> str:
        
        prompt = {
            "model": self.model_name,
            "prompt": f"Your task is to summarize any content given and return a shorter version that will contain all important information from the following document in Macedonian:\n\n{document}\n\nSummary:",
            "stream": False,
            "options": {
                "temperature": 0.3,
                "top_p": 0.9,
                "max_tokens": 8192,
                "num_predict": 1024
            }
        }   
        try:
            completion = requests.post(
                f"{self.ollama_url}/api/generate",
                json=prompt,
                timeout=90
            )
            if completion.status_code == 200:
                response_json = completion.json()
                summary = response_json.get("response", "").strip()
                return summary
            else:
                logger.error(f"Failed to summarize document: {completion.text}")
                return "Не можам да генерирам резиме во моментов."
        except Exception as e:
            logger.error(f"Error summarizing document: {e}")
            return 'Грешка при резимирање на документот.'