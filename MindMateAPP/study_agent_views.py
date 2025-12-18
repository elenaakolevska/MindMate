"""
Study Agent Views - API endpoints for RAG retrieval and study assistance
"""

import json
import logging
import random
from datetime import datetime
from typing import Dict, Any

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator

from .models import Student
from .services.rag_retriever import PostgresRAGRetriever

logger = logging.getLogger(__name__)


def get_student_from_request(request) -> Student:
    """Helper function to get Student object from request."""
    try:
        return Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        raise ValueError("Student not found for authenticated user")


@csrf_exempt
@require_http_methods(["POST"])
@login_required
def search_context(request):
    """
    API endpoint for semantic search in uploaded study materials.
    
    POST /api/study-agent/search/
    
    Request body:
    {
        "query": "explain photosynthesis",
        "top_k": 5,
        "subject_filter": "biology",  // optional
        "min_relevance": 0.3,        // optional
        "include_context": true      // optional, includes surrounding chunks
    }
    
    Response:
    {
        "success": true,
        "query": "explain photosynthesis",
        "results": [
            {
                "text": "Photosynthesis is the process...",
                "document_id": 123,
                "document_title": "Biology Chapter 5",
                "subject": "biology",
                "upload_date": "2024-12-01T10:30:00Z",
                "chunk_index": 5,
                "similarity_score": 0.95,
                "relevance_score": 0.88,
                "recency_score": 0.75,
                "final_score": 0.88,
                "context_chunks": [...] // if include_context=true
            }
        ],
        "total_found": 5,
        "search_stats": {
            "available_subjects": ["biology", "chemistry"],
            "total_chunks": 1250,
            "search_time_ms": 150
        }
    }
    """
    start_time = datetime.now()
    
    try:
        # Parse request body
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({
                "success": False,
                "error": "Invalid JSON in request body"
            }, status=400)
        
        # Validate required fields
        query = data.get("query", "").strip()
        if not query:
            return JsonResponse({
                "success": False,
                "error": "Query parameter is required and cannot be empty"
            }, status=400)
        
        # Get optional parameters
        top_k = data.get("top_k", 5)
        subject_filter = data.get("subject_filter")
        min_relevance = data.get("min_relevance")
        include_context = data.get("include_context", False)
        
        # Validate parameters
        if not isinstance(top_k, int) or top_k <= 0 or top_k > 20:
            return JsonResponse({
                "success": False,
                "error": "top_k must be an integer between 1 and 20"
            }, status=400)
        
        if min_relevance is not None and (not isinstance(min_relevance, (int, float)) or not 0 <= min_relevance <= 1):
            return JsonResponse({
                "success": False,
                "error": "min_relevance must be a number between 0 and 1"
            }, status=400)
        
        # Get student
        try:
            student = get_student_from_request(request)
        except ValueError as e:
            return JsonResponse({
                "success": False,
                "error": str(e)
            }, status=404)
        
        # Get RAG retriever
        rag_retriever = PostgresRAGRetriever(student_id= student.id)
        
        # Perform search
        if include_context:
            # Enhanced search with context
            search_results = rag_retriever.search_with_context_ranking(
                student_id=student.id,
                query=query,
                top_k=top_k,
                subject_filter=subject_filter
            )
            
            # Convert to standard format
            results = []
            for result in search_results:
                primary = result["primary_chunk"]
                doc_info = result["document_info"]
                
                result_data = {
                    "text": primary["text"],
                    "document_id": doc_info["id"],
                    "document_title": doc_info["title"],
                    "subject": doc_info["subject"],
                    "upload_date": doc_info["upload_date"],
                    "chunk_index": primary["chunk_index"],
                    "similarity_score": primary["similarity_score"],
                    "relevance_score": primary["relevance_score"],
                    "final_score": result["final_score"],
                    "context_chunks": result["context_chunks"]
                }
                results.append(result_data)
        else:
            # Standard search
            retrieval_results = rag_retriever.retrieve_context(
                student_id=student.id,
                query=query,
                top_k=top_k,
                subject_filter=subject_filter,
                min_relevance=min_relevance
            )
            
            # Convert to response format
            results = []
            for result in retrieval_results:
                result_data = {
                    "text": result.text,
                    "document_id": result.document_id,
                    "document_title": result.document_title,
                    "subject": result.subject,
                    "upload_date": result.upload_date.isoformat(),
                    "chunk_index": result.chunk_index,
                    "similarity_score": result.similarity_score,
                    "relevance_score": result.relevance_score,
                    "recency_score": result.recency_score,
                    "final_score": result.final_score
                }
                results.append(result_data)
        
        # Get search statistics
        search_stats = rag_retriever.get_search_stats(student.id)
        
        # Calculate search time
        search_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        search_stats["search_time_ms"] = search_time_ms
        
        # Log successful search
        logger.info(
            f"Study Agent search completed: query='{query}', "
            f"student_id={student.id}, results={len(results)}, "
            f"time={search_time_ms}ms"
        )
        
        return JsonResponse({
            "success": True,
            "query": query,
            "results": results,
            "total_found": len(results),
            "search_stats": search_stats
        })
        
    except Exception as e:
        logger.error(f"Error in study agent search: {e}", exc_info=True)
        return JsonResponse({
            "success": False,
            "error": "Internal server error occurred during search"
        }, status=500)


@require_http_methods(["GET"])
@login_required
def get_available_subjects(request):
    """
    Get list of available subjects for filtering.
    
    GET /api/study-agent/subjects/
    
    Response:
    {
        "success": true,
        "subjects": ["biology", "chemistry", "physics"],
        "total_subjects": 3
    }
    """
    try:
        # Get student
        try:
            student = get_student_from_request(request)
        except ValueError as e:
            return JsonResponse({
                "success": False,
                "error": str(e)
            }, status=404)
        
        # Get RAG retriever and available subjects
        rag_retriever = PostgresRAGRetriever(student_id= student.id)
        subjects = rag_retriever.get_available_subjects(student.id)
        
        return JsonResponse({
            "success": True,
            "subjects": subjects,
            "total_subjects": len(subjects)
        })
        
    except Exception as e:
        logger.error(f"Error getting available subjects: {e}", exc_info=True)
        return JsonResponse({
            "success": False,
            "error": "Internal server error"
        }, status=500)


@require_http_methods(["GET"])
@login_required
def get_search_stats(request):
    """
    Get comprehensive search statistics for a student.
    
    GET /api/study-agent/stats/
    
    Response:
    {
        "success": true,
        "stats": {
            "student_id": 123,
            "total_collections": 5,
            "total_chunks": 1250,
            "unique_documents": 15,
            "available_subjects": ["biology", "chemistry"],
            "recent_uploads_30d": 3,
            "is_searchable": true
        }
    }
    """
    try:
        # Get student
        try:
            student = get_student_from_request(request)
        except ValueError as e:
            return JsonResponse({
                "success": False,
                "error": str(e)
            }, status=404)
        
        # Get RAG retriever and statistics
        rag_retriever = PostgresRAGRetriever(student_id= student.id)
        stats = rag_retriever.get_search_stats(student.id)
        
        return JsonResponse({
            "success": True,
            "stats": stats
        })
        
    except Exception as e:
        logger.error(f"Error getting search statistics: {e}", exc_info=True)
        return JsonResponse({
            "success": False,
            "error": "Internal server error"
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
@login_required
def chat_with_study_agent(request):
    """
    Chat endpoint for the Study Agent with RAG context.
    
    POST /api/study-agent/chat/
    
    Request body:
    {
        "message": "Can you explain photosynthesis?",
        "subject_filter": "biology",  // optional
        "use_context": true          // optional, whether to include RAG context
    }
    
    Response:
    {
        "success": true,
        "response": "Based on your study materials, photosynthesis is...",
        "context_used": [
            {
                "text": "Photosynthesis process excerpt...",
                "document_title": "Biology Chapter 5",
                "relevance_score": 0.88
            }
        ],
        "sources": ["Biology Chapter 5", "Plant Biology Notes"]
    }
    """
    try:
        # Parse request body
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({
                "success": False,
                "error": "Invalid JSON in request body"
            }, status=400)
        
        # Validate required fields
        message = data.get("message", "").strip()
        if not message:
            return JsonResponse({
                "success": False,
                "error": "Message parameter is required and cannot be empty"
            }, status=400)
        
        # Get optional parameters
        subject_filter = data.get("subject_filter")
        use_context = data.get("use_context", True)
        
        # Get student
        try:
            student = get_student_from_request(request)
        except ValueError as e:
            return JsonResponse({
                "success": False,
                "error": str(e)
            }, status=404)
        
        # Initialize response data
        response_data = {
            "success": True,
            "response": "",
            "context_used": [],
            "sources": []
        }
        
        # Get relevant context if requested
        if use_context:
            rag_retriever = PostgresRAGRetriever(student_id= student.id)
            context_results = rag_retriever.retrieve_context(
                student_id=student.id,
                query=message,
                top_k=3,  # Get top 3 most relevant chunks
                subject_filter=subject_filter
            )
            
            if context_results:
                # Prepare context for LLM
                context_texts = []
                sources = set()
                
                for result in context_results:
                    context_texts.append(result.text)
                    sources.add(result.document_title)
                    
                    response_data["context_used"].append({
                        "text": result.text[:200] + "..." if len(result.text) > 200 else result.text,
                        "document_title": result.document_title,
                        "subject": result.subject,
                        "relevance_score": result.relevance_score
                    })
                
                response_data["sources"] = list(sources)
                
                # Generate enhanced response using LLM
                response_text = generate_llm_response(context_results, message, list(sources))
                response_data["response"] = response_text
                
            else:
                # No relevant context found
                response_data["response"] = f"""Ne mozhev da najdam specificni informacii za "{message}" vo vashite kaceni materijali za uchenje.

**Za podobra pomosh:**
1. 📚 Kachete relevantni materijali za ova tema
2. 🔍 Proverete dali ste go koristele tochniot filter za predmet
3. 💬 Probajte da go preformulirate prashanjeto so drugi kluchni zborovi

**Sepak mozham da pomognam so:**
- Opshti strategii za uchenje
- Objasnuvanje kako da gi organizirate materijalite
- Predlaganje tehniki za uchenje

Shto sakate da istrazime?"""
        else:
            # Direct response without context
            response_data["response"] = f"""Zdravo! Jas sum vashiot AI Study Assistant.

**Za da dobijam personalizirana pomosh so vasheto prashanje: "{message}"**

Preporachuvam da ovozmozhite prebaruvanje na kontekst za da mozham da se referiraam na vashite kacheni materijali za tocni, personalizirani odgovori.

**Mozham da vi pomognam so:**
- 📖 Objasnuvanje na koncepti od vashite materijali
- 📝 Kreiranje sažetoci i vodiči za uchenje
- ❓ Generiranje vežbalni prashanja
- 🎯 Raschlenuvanje na kompleksni temi

Sakate li da prebaram vo vashite materijali za informacii za ova tema?"""
        
        # Log interaction
        logger.info(f"Study Agent chat: student_id={student.id}, message_length={len(message)}, context_used={len(response_data['context_used'])}")
        
        return JsonResponse(response_data)
        
    except Exception as e:
        logger.error(f"Error in study agent chat: {e}", exc_info=True)
        return JsonResponse({
            "success": False,
            "error": "Internal server error occurred during chat"
        }, status=500)


def generate_llm_response(context_results, message, sources):
    """Generate an intelligent response using existing Ollama LLM service"""
    
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # Import the existing conversational agent
        from .services.conversational_agent import ConversationalTimeAgent, ConversationContext
        
        # Create LLM agent instance
        llm_agent = ConversationalTimeAgent()
        
        # Prepare context from documents
        context_text = ""
        if context_results:
            context_text = "\n\n".join([
                f"Document: {result.document_title}\n"
                f"Content: {result.text[:500]}..."
                for result in context_results[:3]
            ])
        
        # Enhanced prompt for study assistance
        enhanced_message = f"""You are a Study Agent - an intelligent learning assistant that helps students with their studies.

STUDENT QUESTION: {message}

CONTEXT FROM DOCUMENTS:
{context_text if context_text else "No documents available."}

SOURCES: {', '.join(sources) if sources else 'No sources'}

INSTRUCTIONS:
1. Answer the student's question clearly and concisely
2. Use information from the provided documents if relevant
3. Give concrete, useful study advice
4. Be friendly and encouraging
5. If the question is general, provide tips for better learning
6. Structure your response in a helpful way
7. Always respond in Macedonian language using Latin script (e.g., "Zdravo, kako mozham da vi pomognam?")

Respond in Macedonian using Latin script:"""

        # Create conversation context for this session
        context = ConversationContext(
            student_id=0,  # Placeholder, would use actual student ID
            conversation_history=[],
            current_task="study_assistance"
        )
        
        # Use the existing LLM service
        llm_response = llm_agent.process_message(enhanced_message, context)
        
        # Format the response nicely
        response_text = llm_response.get('response', 'Ne mozhev da generiram odgovor.')
        
        # Add document context if available
        if context_results:
            formatted_response = f"""
📚 **Study Agent odgovor:**

{response_text}

**Relevantni informacii od dokumentite:**
"""
            for i, result in enumerate(context_results[:3], 1):
                doc_name = result.document_title
                content_preview = result.text[:200]
                formatted_response += f"""

{i}. **{doc_name}**
   {content_preview}...
"""
            
            if sources:
                formatted_response += f"\n\n**Izvori:** {', '.join(sources)}"
            
            # Add suggestions if provided by LLM
            suggestions = llm_response.get('suggestions', [])
            if suggestions:
                formatted_response += "\n\n💡 **Dopolnitelni soveti:**\n"
                for suggestion in suggestions:
                    formatted_response += f"• {suggestion}\n"
            
            return formatted_response
        else:
            # No documents, just return LLM response with helpful formatting
            formatted_response = f"""
🤖 **Study Agent odgovor:**

{response_text}

💡 **Soveti:**
- Prikachete PDF, Word ili tekst dokumenti za podobra pomosh
- Bidete konkretni vo vashite prashanja
- Mozhete da postavuvate prashanja za sodrzhinata od dokumentite
"""
            
            # Add suggestions if provided by LLM
            suggestions = llm_response.get('suggestions', [])
            if suggestions:
                formatted_response += "\n\n**Preporaki:**\n"
                for suggestion in suggestions:
                    formatted_response += f"• {suggestion}\n"
            
            return formatted_response
            
    except ImportError as e:
        logger.error(f"Could not import conversational agent: {e}")
        return generate_fallback_response(context_results, message, sources)
    except Exception as e:
        logger.error(f"Error using LLM service: {e}")
        return generate_fallback_response(context_results, message, sources)


def generate_fallback_response(context_results, message, sources):
    """Fallback response when LLM service is not available"""
    if context_results:
        formatted_response = f"""
📚 **Vrz osnova na vashite dokumenti:**

{message}

**Relevantni informacii:**
"""
        for i, result in enumerate(context_results[:3], 1):
            doc_name = result.document_title
            content_preview = result.text[:300]
            formatted_response += f"""

{i}. **{doc_name}**
   {content_preview}...
"""
        
        if sources:
            formatted_response += f"\n\n**Izvori:** {', '.join(sources)}"
        
        return formatted_response
    else:
        return f"""
🤖 **Study Agent odgovor:**

{message}

Za podobra pomosh, molam prikachete relevantni dokumenti koi se odnesuvaat na vasheto prashanje.

💡 **Soveti:**
- Prikachete PDF, Word ili tekst dokumenti
- Bidete konkretni vo vashite prashanja
- Mozhete da postavuvate prashanja za sodrzhinata od dokumentite
"""


def generate_enhanced_study_response(context_results, message, sources):
    """Generate an enhanced response using the context"""
    
    if not context_results:
        return "I couldn't find relevant information in your study materials."
    
    # Analyze the question type
    question_lower = message.lower()
    is_summary_request = any(word in question_lower for word in ['summary', 'summarize', 'overview', 'main points'])
    is_explanation_request = any(word in question_lower for word in ['explain', 'what is', 'how does', 'why'])
    is_definition_request = any(word in question_lower for word in ['define', 'definition', 'meaning'])
    
    # Create structured response
    response_parts = []
    
    # Introduction
    if is_summary_request:
        response_parts.append(f"📋 **Summary of {', '.join(sources)}**\n")
    elif is_explanation_request:
        response_parts.append(f"💡 **Explanation from your study materials:**\n")
    elif is_definition_request:
        response_parts.append(f"📖 **Definition from your materials:**\n")
    else:
        response_parts.append(f"📚 **Information from your study materials:**\n")
    
    # Main content from context
    key_points = []
    for i, result in enumerate(context_results[:3]):  # Use top 3 results
        # Extract key information (simplified)
        content = result.text.strip()
        if len(content) > 300:
            content = content[:300] + "..."
        key_points.append(f"• {content}")
    
    response_parts.append("\n".join(key_points))
    
    # Add sources
    response_parts.append(f"\n**📁 Sources:** {', '.join(sources)}")
    
    # Add helpful follow-up
    follow_ups = [
        "Would you like me to elaborate on any specific aspect?",
        "Do you need clarification on any of these points?", 
        "Should I generate practice questions about this topic?",
        "Would you like a more detailed explanation of any concept?"
    ]
    
    response_parts.append(f"\n**💬 {random.choice(follow_ups)}**")
    
    return "\n".join(response_parts)
