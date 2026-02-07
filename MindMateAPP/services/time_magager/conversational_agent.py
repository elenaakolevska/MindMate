"""
Conversational Time Agent using Llama3

This service provides intelligent, conversational interactions for time management,
task estimation, and calendar slot finding using Ollama Llama3.
"""

import json
import logging
import requests
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class ConversationContext:
    """Context for maintaining conversation state"""
    student_id: int
    conversation_history: List[Dict]
    current_task: Optional[str] = None
    last_intent: Optional[str] = None  # 'time_estimation', 'slot_finding', 'general_chat'
    last_parameters: Optional[Dict] = None


class ConversationalTimeAgent:
    """
    Intelligent conversational agent for time management using Llama3
    """
    
    def __init__(self, ollama_url: str = None):
        from django.conf import settings
        self.ollama_url = ollama_url or getattr(settings, 'OLLAMA_URL', 'http://host.docker.internal:11434')
        self.model_name = getattr(settings, 'OLLAMA_MODEL', 'qwen2.5:7b')
        
    def process_message(
        self, 
        message: str, 
        context: ConversationContext
    ) -> Dict:
        """
        Process user message and determine appropriate response
        
        Returns:
            Dict with response, intent, and any extracted parameters
        """
        try:
            # Build conversation prompt
            conversation_prompt = self._build_conversation_prompt(message, context)
            
            # Get LLM response
            llm_response = self._query_ollama(conversation_prompt)
            
            # Parse LLM response to extract intent and parameters
            parsed_response = self._parse_llm_response(llm_response, message)
            
            # Update conversation context
            self._update_context(context, message, parsed_response)
            
            return parsed_response
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return {
                'intent': 'error',
                'response': 'Извинете, се случи грешка. Можете ли да го повторите прашањето?',
                'parameters': {},
                'confidence': 0
            }
    
    def _build_conversation_prompt(
        self, 
        message: str, 
        context: ConversationContext
    ) -> str:
        """Build conversation prompt for Llama3"""
        
        # Get recent conversation history (last 3 exchanges)
        recent_history = context.conversation_history[-6:] if context.conversation_history else []
        
        prompt = f"""You are Time Agent, an intelligent assistant for time planning that helps students. Your task is to understand what the user wants and respond appropriately.

YOUR CAPABILITIES:
1. TIME ESTIMATION - when user asks how much time is needed for a task
2. FINDING TIME SLOTS - when user wants to find free time slots in calendar  
3. GENERAL CHAT - when user has questions about learning, organization, advice

RULES:
- Always respond in Macedonian language (using Latin script)
- Be friendly and helpful
- If you're not sure what the user wants, ask for clarification
- For time estimation, extract the task and subject
- For finding slots, extract time, subject, difficulty
- For general chat, give useful advice
- Keep responses natural and conversational in Macedonian

CONVERSATION HISTORY:"""

        # Add conversation history
        for entry in recent_history:
            role = "User" if entry.get('role') == 'user' else "Time Agent"
            prompt += f"\n{role}: {entry.get('message', '')}"
        
        prompt += f"""

CURRENT USER MESSAGE: "{message}"

RESPONSE FORMAT (REQUIRED JSON):
{{
    "intent": "time_estimation|slot_finding|general_chat",
    "response": "your response in Macedonian using Latin script",
    "confidence": 85,
    "parameters": {{
        "task_description": "task description (if any)",
        "subject": "subject (if any)", 
        "duration_hours": how many hours (for slot finding),
        "difficulty": "easy|moderate|hard|challenging",
        "preferred_time": "morning|afternoon|evening (if any)",
        "urgency": "high|medium|low"
    }},
    "follow_up_questions": ["question1", "question2"],
    "suggestions": ["advice1", "advice2"]
}}

IMPORTANT: 
- For "popladne nekoj termin" -> intent: "slot_finding", extract parameters for finding slots
- For "kolku vreme treba za matematika" -> intent: "time_estimation"
- For "kako da ucham podobro" -> intent: "general_chat"
- Always return valid JSON!
- Respond in natural Macedonian using Latin script (e.g., "Zdravo, kako mozham da vi pomognam?")

Your response:"""

        return prompt
    
    def _query_ollama(self, prompt: str) -> str:
        """Query Ollama API with the conversation prompt"""
        try:
            logger.info(f"Querying Ollama at {self.ollama_url} with model {self.model_name}")
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "top_p": 0.9,
                        "num_predict": 2048,
                        "max_tokens": 8192,
                        "stop": ["\n\nКорисник:", "\n\nTime Agent:"]
                    }
                },
                timeout=120  # Increased timeout for larger models like Qwen2.5
            )
            
            if response.status_code == 200:
                result = response.json()
                ollama_response = result.get('response', '').strip()
                logger.info(f"Ollama response: {ollama_response[:200]}...")
                return ollama_response
            else:
                logger.error(f"Ollama API error: {response.status_code} - {response.text}")
                return ""
                
        except requests.RequestException as e:
            logger.error(f"Request to Ollama failed: {e}")
            # Try fallback to smaller model if the primary model fails
            logger.info(f"Trying fallback to llama3.2:3b model (primary was {self.model_name})")
            if True:
                try:
                    fallback_response = requests.post(
                        f"{self.ollama_url}/api/generate",
                        json={
                            "model": "llama3.2:3b",
                            "prompt": prompt,
                            "stream": False,
                            "options": {
                                "temperature": 0.7,
                                "top_p": 0.9,
                                "num_predict": 512,
                                "max_tokens": 2048
                            }
                        },
                        timeout=60
                    )
                    if fallback_response.status_code == 200:
                        result = fallback_response.json()
                        return result.get('response', '').strip()
                except Exception as fallback_error:
                    logger.error(f"Fallback model also failed: {fallback_error}")
            return ""
        except Exception as e:
            logger.error(f"Unexpected error querying Ollama: {e}")
            return ""
    
    def _parse_llm_response(self, llm_response: str, original_message: str) -> Dict:
        """Parse LLM response and extract structured data"""
        try:
            # Try to extract JSON from the response
            json_start = llm_response.find('{')
            json_end = llm_response.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = llm_response[json_start:json_end]
                parsed = json.loads(json_str)
                
                # Validate and sanitize
                return self._validate_parsed_response(parsed, original_message)
            else:
                # Fallback parsing if JSON extraction fails
                return self._fallback_parse(llm_response, original_message)
                
        except json.JSONDecodeError as e:
            logger.warning(f"JSON decode error: {e}, attempting fallback parsing")
            return self._fallback_parse(llm_response, original_message)
    
    def _validate_parsed_response(self, parsed: Dict, original_message: str) -> Dict:
        """Validate and sanitize parsed LLM response"""
        
        # Ensure required fields
        validated = {
            'intent': parsed.get('intent', 'general_chat'),
            'response': parsed.get('response', 'Може ли да го повторите прашањето?'),
            'confidence': max(0, min(100, parsed.get('confidence', 70))),
            'parameters': {},
            'follow_up_questions': [],
            'suggestions': []
        }
        
        # Validate intent
        valid_intents = ['time_estimation', 'slot_finding', 'general_chat']
        if validated['intent'] not in valid_intents:
            validated['intent'] = 'general_chat'
        
        # Validate parameters
        if 'parameters' in parsed and isinstance(parsed['parameters'], dict):
            params = parsed['parameters']
            
            # Extract and validate duration
            if 'duration_hours' in params:
                try:
                    duration = float(params['duration_hours'])
                    validated['parameters']['duration_hours'] = max(0.25, min(12.0, duration))
                except (ValueError, TypeError):
                    pass
            
            # Extract other string parameters
            for key in ['task_description', 'subject', 'difficulty', 'preferred_time', 'urgency']:
                if key in params and isinstance(params[key], str):
                    validated['parameters'][key] = params[key][:200]  # Limit length
        
        # Validate follow-up questions and suggestions
        for key in ['follow_up_questions', 'suggestions']:
            if key in parsed and isinstance(parsed[key], list):
                validated[key] = [str(item)[:100] for item in parsed[key][:3]]  # Max 3 items
        
        return validated
    
    def _fallback_parse(self, response: str, original_message: str) -> Dict:
        """Fallback parsing when JSON extraction fails"""
        
        # Simple keyword-based intent detection
        message_lower = original_message.lower()
        
        # Determine intent based on keywords
        intent = 'general_chat'
        
        slot_keywords = [
            'термин', 'време', 'слот', 'најди', 'слободно', 'календар',
            'попладне', 'утро', 'вечер', 'кога можам'
        ]
        
        time_keywords = [
            'колку време', 'проценка', 'треба ми', 'за колку', 'времетраење'
        ]
        
        if any(keyword in message_lower for keyword in slot_keywords):
            intent = 'slot_finding'
        elif any(keyword in message_lower for keyword in time_keywords):
            intent = 'time_estimation'
        
        # Extract basic parameters
        parameters = {}
        
        # Extract duration (simple regex)
        import re
        duration_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:час|hour|h)', message_lower)
        if duration_match:
            try:
                parameters['duration_hours'] = float(duration_match.group(1))
            except ValueError:
                pass
        
        # Extract time preference
        if 'попладne' in message_lower or 'afternoon' in message_lower:
            parameters['preferred_time'] = 'afternoon'
        elif 'утро' in message_lower or 'morning' in message_lower:
            parameters['preferred_time'] = 'morning'
        elif 'вечер' in message_lower or 'evening' in message_lower:
            parameters['preferred_time'] = 'evening'
        
        # Generate appropriate response based on intent
        if intent == 'slot_finding':
            response_text = "🗓️ Разбирам дека сакате да најдете термин. Ќе ви помогнам да најдам слободно време во вашиот календар."
        elif intent == 'time_estimation':
            response_text = "⏱️ Ќе направам проценка на потребното време за вашата задача."
        else:
            response_text = response if response else "Како можам да ви помогнам со планирањето на времето?"
        
        return {
            'intent': intent,
            'response': response_text,
            'confidence': 60,
            'parameters': parameters,
            'follow_up_questions': [],
            'suggestions': []
        }
    
    def _update_context(
        self, 
        context: ConversationContext, 
        message: str, 
        response: Dict
    ):
        """Update conversation context with new exchange"""
        
        # Add user message to history
        context.conversation_history.append({
            'role': 'user',
            'message': message,
            'timestamp': datetime.now().isoformat()
        })
        
        # Add agent response to history
        context.conversation_history.append({
            'role': 'agent', 
            'message': response['response'],
            'intent': response['intent'],
            'timestamp': datetime.now().isoformat()
        })
        
        # Update current context
        context.last_intent = response['intent']
        context.last_parameters = response.get('parameters', {})
        
        # Keep history manageable (last 20 messages)
        if len(context.conversation_history) > 20:
            context.conversation_history = context.conversation_history[-20:]
    
    def get_conversation_summary(self, context: ConversationContext) -> Dict:
        """Get a summary of the current conversation context"""
        
        recent_intents = []
        for entry in context.conversation_history[-10:]:  # Last 5 exchanges
            if entry.get('role') == 'agent' and entry.get('intent'):
                recent_intents.append(entry['intent'])
        
        # Count intent frequencies
        intent_counts = {}
        for intent in recent_intents:
            intent_counts[intent] = intent_counts.get(intent, 0) + 1
        
        return {
            'total_messages': len(context.conversation_history),
            'last_intent': context.last_intent,
            'recent_intent_pattern': intent_counts,
            'has_ongoing_task': bool(context.current_task),
            'last_parameters': context.last_parameters
        }


class IntentRouter:
    """
    Routes processed intents to appropriate services
    """
    
    def __init__(self):
        pass
    
    def route_intent(self, intent: str, parameters: Dict, student) -> Dict:
        """
        Route intent to appropriate service and return response data
        """
        if intent == 'time_estimation':
            return self._route_time_estimation(parameters, student)
        elif intent == 'slot_finding':
            return self._route_slot_finding(parameters, student)
        elif intent == 'general_chat':
            return self._route_general_chat(parameters, student)
        else:
            return {
                'success': False,
                'error': 'Unknown intent',
                'message': 'Не можам да го разберам вашето барање.'
            }
    
    def _route_time_estimation(self, parameters: Dict, student) -> Dict:
        """Route to time estimation service"""
        from ... import time_agent_views
        
        # Build request data for time estimation
        request_data = {
            'task_description': parameters.get('task_description', 'Општа задача'),
            'subject_area': parameters.get('subject', ''),
            'difficulty': parameters.get('difficulty', 'moderate')
        }
        
        return {
            'success': True,
            'action': 'time_estimation',
            'data': request_data,
            'message': 'Насочувам кон проценка на време...'
        }
    
    def _route_slot_finding(self, parameters: Dict, student) -> Dict:
        """Route to slot finding service"""
        
        # Build request data for slot finding
        request_data = {
            'duration_hours': parameters.get('duration_hours', 2.0),
            'subject': parameters.get('subject'),
            'difficulty': parameters.get('difficulty', 'moderate'),
            'task_type': 'study',
            'preferred_times': [parameters['preferred_time']] if parameters.get('preferred_time') else None,
            'allow_splitting': True
        }
        
        return {
            'success': True,
            'action': 'slot_finding',  
            'data': request_data,
            'message': 'Насочувам кон наоѓање термини...'
        }
    
    def _route_general_chat(self, parameters: Dict, student) -> Dict:
        """Handle general chat responses"""
        
        return {
            'success': True,
            'action': 'general_chat',
            'data': parameters,
            'message': 'Одговарам на вашето прашање...'
        }