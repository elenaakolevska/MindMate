"""
Study Agent LangGraph Nodes
Individual processing nodes for the study agent workflow
"""

import logging
from typing import Dict, Any
from datetime import datetime

from ..services.llm_service import get_llm_service
from ..services.prompt_templates import (
    PromptTemplates,
    get_system_prompt,
    PromptType,
    get_prompt_template
)
from .agent_state import StudyAgentState

logger = logging.getLogger(__name__)


class StudyAgentNodes:
    """Collection of processing nodes for Study Agent"""

    def __init__(self):
        self.llm_service = get_llm_service()
        self.templates = PromptTemplates()

    def classify_intent(self, state: StudyAgentState) -> StudyAgentState:
        """
        Node: Classify user intent

        Determines what the user wants to do based on their message.
        """
        logger.info(f"🔍 Classifying intent for message: {state['user_message'][:50]}...")

        try:
            # Add step to tracking
            steps = state.get('steps_taken', [])
            steps.append('classify_intent')
            state['steps_taken'] = steps

            # Use LLM to classify intent
            prompt = self.templates.intent_classification_prompt(state['user_message'])

            response = self.llm_service.generate(
                prompt=prompt,
                system_prompt=get_system_prompt("study"),
                temperature=0.3  # Lower temperature for classification
            )

            intent = response.content.strip().lower()

            # Validate intent
            valid_intents = [
                "quiz_generation",
                "question_answering",
                "content_summary",
                "general_chat",
                "file_upload"
            ]

            # Time estimation and schedule planning belong to Time Agent
            time_agent_intents = ["time_estimation", "schedule_planning"]

            # Check if this belongs to Time Agent
            if intent in time_agent_intents:
                state['intent'] = 'redirect_to_time_agent'
                state['original_intent'] = intent
                state['confidence'] = 0.9
                state['current_step'] = 'intent_classified'
                logger.info(f"⚠️  Intent {intent} should use Time Agent")
            elif intent not in valid_intents:
                # Default to question_answering if unclear
                intent = "question_answering"
                state['intent'] = intent
                state['confidence'] = 0.5
                state['current_step'] = 'intent_classified'
            else:
                state['intent'] = intent
                state['confidence'] = 0.9
                state['current_step'] = 'intent_classified'

            logger.info(f"✅ Intent classified: {intent} (confidence: {confidence})")

        except Exception as e:
            logger.error(f"❌ Error in classify_intent: {e}")
            state['error'] = str(e)
            state['error_type'] = 'intent_classification_error'
            state['intent'] = 'general_chat'  # Fallback
            state['confidence'] = 0.3

        return state

    def retrieve_context(self, state: StudyAgentState) -> StudyAgentState:
        """
        Node: Retrieve relevant context

        Fetches student data, uploaded files, or relevant background information.
        """
        logger.info("📚 Retrieving context...")

        try:
            steps = state.get('steps_taken', [])
            steps.append('retrieve_context')
            state['steps_taken'] = steps

            # Retrieve student data if user_id is provided
            if state.get('user_id'):
                # TODO: Fetch from database
                state['student_data'] = {
                    'study_level': 'факултет',
                    'study_direction': 'Компјутерски науки',
                    'daily_study_hours': 4,
                    'learning_style': 'визуелен'
                }
                logger.info(f"✅ Retrieved student data for user {state['user_id']}")

            # Process uploaded files if any
            if state.get('uploaded_files'):
                # TODO: Extract text from files
                state['extracted_text'] = "Извлечен текст од документите..."
                logger.info(f"✅ Extracted text from {len(state['uploaded_files'])} file(s)")

            state['current_step'] = 'context_retrieved'

        except Exception as e:
            logger.error(f"❌ Error in retrieve_context: {e}")
            state['error'] = str(e)
            state['error_type'] = 'context_retrieval_error'

        return state

    def generate_quiz(self, state: StudyAgentState) -> StudyAgentState:
        """
        Node: Generate quiz

        Creates a quiz based on the provided content or topic.
        """
        logger.info("📝 Generating quiz...")

        try:
            steps = state.get('steps_taken', [])
            steps.append('generate_quiz')
            state['steps_taken'] = steps

            # Extract quiz parameters from user message or use defaults
            content = state.get('extracted_text') or state.get('context') or state['user_message']
            quiz_type = state.get('quiz_type', 'повеќекратен избор')
            difficulty = state.get('quiz_difficulty', 'средна')
            num_questions = state.get('num_questions', 5)

            # Generate quiz prompt
            prompt = self.templates.quiz_generation_prompt(
                content=content,
                quiz_type=quiz_type,
                difficulty=difficulty,
                num_questions=num_questions,
                language='mk'
            )

            # Generate quiz with LLM
            response = self.llm_service.generate(
                prompt=prompt,
                system_prompt=get_system_prompt("study"),
                json_mode=True
            )

            # Parse JSON response
            quiz_data = self.llm_service.parse_json_response(response)

            if quiz_data:
                state['generated_quiz'] = quiz_data
                state['response_type'] = 'quiz'
                state['response'] = f"Генериран квиз со {len(quiz_data.get('questions', []))} прашања."
                logger.info(f"✅ Quiz generated with {len(quiz_data.get('questions', []))} questions")
            else:
                raise ValueError("Failed to parse quiz JSON")

            state['current_step'] = 'quiz_generated'

        except Exception as e:
            logger.error(f"❌ Error in generate_quiz: {e}")
            state['error'] = str(e)
            state['error_type'] = 'quiz_generation_error'
            state['response'] = "Жалам, имаше проблем при генерирање на квизот."

        return state

    def estimate_time(self, state: StudyAgentState) -> StudyAgentState:
        """
        Node: Estimate task time

        Provides time estimation for a study task.
        """
        logger.info("⏱️ Estimating time...")

        try:
            steps = state.get('steps_taken', [])
            steps.append('estimate_time')
            state['steps_taken'] = steps

            task_description = state.get('task_description') or state['user_message']
            student_context = state.get('student_data', {
                'study_level': 'факултет',
                'daily_study_hours': 4
            })

            # Generate estimation prompt
            prompt = self.templates.task_estimation_prompt(
                task_description=task_description,
                student_context=student_context
            )

            # Get estimation from LLM
            response = self.llm_service.generate(
                prompt=prompt,
                system_prompt=get_system_prompt("time"),
                json_mode=True
            )

            # Parse JSON response
            estimation_data = self.llm_service.parse_json_response(response)

            if estimation_data:
                state['estimated_hours'] = estimation_data.get('estimated_hours', 2.0)
                state['time_breakdown'] = estimation_data.get('time_breakdown', {})
                state['confidence_level'] = str(estimation_data.get('confidence_percentage', 70))
                state['response_type'] = 'time_estimation'
                state['response'] = f"Проценето време: {state['estimated_hours']} часа"
                logger.info(f"✅ Time estimated: {state['estimated_hours']} hours")
            else:
                raise ValueError("Failed to parse estimation JSON")

            state['current_step'] = 'time_estimated'

        except Exception as e:
            logger.error(f"❌ Error in estimate_time: {e}")
            state['error'] = str(e)
            state['error_type'] = 'time_estimation_error'
            state['response'] = "Жалам, имаше проблем при проценка на времето."

        return state

    def plan_schedule(self, state: StudyAgentState) -> StudyAgentState:
        """
        Node: Plan study schedule

        Creates an optimized study schedule.
        """
        logger.info("📅 Planning schedule...")

        try:
            steps = state.get('steps_taken', [])
            steps.append('plan_schedule')
            state['steps_taken'] = steps

            tasks = state.get('tasks', [])
            available_hours = state.get('available_hours', 8.0)
            preferences = state.get('student_data', {
                'learning_style': 'прилагодлив',
                'study_pace': 'умерено'
            })

            # Generate schedule prompt
            prompt = self.templates.study_planning_prompt(
                tasks=tasks if tasks else [{'description': state['user_message'], 'estimated_hours': 2}],
                available_hours=available_hours,
                preferences=preferences
            )

            # Get schedule from LLM
            response = self.llm_service.generate(
                prompt=prompt,
                system_prompt=get_system_prompt("time"),
                json_mode=True
            )

            # Parse JSON response
            schedule_data = self.llm_service.parse_json_response(response)

            if schedule_data:
                state['schedule'] = schedule_data
                state['response_type'] = 'schedule'
                state['response'] = f"Креиран распоред со {len(schedule_data.get('schedule', []))} сесии."
                logger.info(f"✅ Schedule created with {len(schedule_data.get('schedule', []))} sessions")
            else:
                raise ValueError("Failed to parse schedule JSON")

            state['current_step'] = 'schedule_planned'

        except Exception as e:
            logger.error(f"❌ Error in plan_schedule: {e}")
            state['error'] = str(e)
            state['error_type'] = 'schedule_planning_error'
            state['response'] = "Жалам, имаше проблем при планирање на распоредот."

        return state

    def answer_question(self, state: StudyAgentState) -> StudyAgentState:
        """
        Node: Answer student question

        Provides a detailed answer to the student's question.
        """
        logger.info("💡 Answering question...")

        try:
            steps = state.get('steps_taken', [])
            steps.append('answer_question')
            state['steps_taken'] = steps

            question = state.get('question') or state['user_message']
            context = state.get('extracted_text') or state.get('context', '')
            student_level = state.get('student_data', {}).get('study_level', 'факултет')

            # Generate answer prompt
            prompt = self.templates.question_answering_prompt(
                question=question,
                context=context,
                student_level=student_level,
                language='mk'
            )

            # Get answer from LLM
            response = self.llm_service.generate(
                prompt=prompt,
                system_prompt=get_system_prompt("study"),
                temperature=0.7
            )

            state['answer'] = response.content
            state['response'] = response.content
            state['response_type'] = 'answer'
            state['current_step'] = 'question_answered'

            logger.info(f"✅ Question answered (length: {len(response.content)} chars)")

        except Exception as e:
            logger.error(f"❌ Error in answer_question: {e}")
            state['error'] = str(e)
            state['error_type'] = 'question_answering_error'
            state['response'] = "Жалам, имаше проблем при одговарање на прашањето."

        return state

    def summarize_content(self, state: StudyAgentState) -> StudyAgentState:
        """
        Node: Summarize content

        Creates a summary of study materials.
        """
        logger.info("📋 Summarizing content...")

        try:
            steps = state.get('steps_taken', [])
            steps.append('summarize_content')
            state['steps_taken'] = steps

            content = state.get('extracted_text') or state.get('context') or state['user_message']
            summary_type = 'concise'  # Can be 'concise', 'detailed', 'exam_prep'

            # Generate summary prompt
            prompt = self.templates.content_summary_prompt(
                content=content,
                summary_type=summary_type,
                language='mk'
            )

            # Get summary from LLM
            response = self.llm_service.generate(
                prompt=prompt,
                system_prompt=get_system_prompt("study"),
                json_mode=True
            )

            # Parse JSON response
            summary_data = self.llm_service.parse_json_response(response)

            if summary_data:
                state['summary'] = summary_data.get('summary', '')
                state['key_concepts'] = summary_data.get('key_concepts', [])
                state['study_tips'] = summary_data.get('study_tips', [])
                state['response'] = summary_data.get('summary', '')
                state['response_type'] = 'summary'
                logger.info(f"✅ Content summarized")
            else:
                raise ValueError("Failed to parse summary JSON")

            state['current_step'] = 'content_summarized'

        except Exception as e:
            logger.error(f"❌ Error in summarize_content: {e}")
            state['error'] = str(e)
            state['error_type'] = 'summarization_error'
            state['response'] = "Жалам, имаше проблем при резимирање на содржината."

        return state

    def redirect_to_time_agent(self, state: StudyAgentState) -> StudyAgentState:
        """
        Node: Redirect to Time Agent

        Handles requests that should go to Time Agent instead of Study Agent.
        """
        logger.info("⏰ Redirecting to Time Agent...")

        try:
            steps = state.get('steps_taken', [])
            steps.append('redirect_to_time_agent')
            state['steps_taken'] = steps

            original_intent = state.get('original_intent', 'time_estimation')

            if original_intent == 'time_estimation':
                state['response'] = """За проценка на време за задачи, те молам користи го **Time Agent**.

Time Agent е специјализиран за:
⏱️ Проценка на време за задачи
📅 Планирање на распоред
⏰ Управување со време

Јас сум Study Agent и се фокусирам на:
📝 Генерирање квизови
❓ Одговарање на прашања  
📄 Резиме на содржина

Ќе те префрлам на Time Agent наскоро!"""

            elif original_intent == 'schedule_planning':
                state['response'] = """За планирање на распоред, те молам користи го **Time Agent**.

Time Agent е специјализиран за:
📅 Планирање на распореди
⏰ Оптимизација на време
📊 Управување со задачи

Јас сум Study Agent и се фокусирам на:
📝 Генерирање квизови
❓ Одговарање на прашања
📄 Резиме на содржина"""

            else:
                state['response'] = "Ова прашање е подобро за Time Agent. Ќе те префрлам наскоро!"

            state['response_type'] = 'redirect'
            state['current_step'] = 'redirected_to_time_agent'

            logger.info(f"✅ Redirect message created")

        except Exception as e:
            logger.error(f"❌ Error in redirect_to_time_agent: {e}")
            state['error'] = str(e)
            state['response'] = "За прашања за време и распоред, те молам користи го Time Agent."

        return state

    def handle_general_chat(self, state: StudyAgentState) -> StudyAgentState:
        """
        Node: Handle general conversation

        Handles greetings, casual questions, and general chat.
        """
        logger.info("💬 Handling general chat...")

        try:
            steps = state.get('steps_taken', [])
            steps.append('handle_general_chat')
            state['steps_taken'] = steps

            # Generate a friendly response
            response = self.llm_service.generate(
                prompt=state['user_message'],
                system_prompt=get_system_prompt("study"),
                temperature=0.8
            )

            state['response'] = response.content
            state['response_type'] = 'chat'
            state['current_step'] = 'general_chat_handled'

            logger.info(f"✅ General chat handled")

        except Exception as e:
            logger.error(f"❌ Error in handle_general_chat: {e}")
            state['error'] = str(e)
            state['error_type'] = 'general_chat_error'
            state['response'] = "Здраво! Како можам да ти помогнам со учењето денес?"

        return state

    def finalize_response(self, state: StudyAgentState) -> StudyAgentState:
        """
        Node: Finalize response

        Prepares the final response and marks the workflow as complete.
        """
        logger.info("✅ Finalizing response...")

        try:
            steps = state.get('steps_taken', [])
            steps.append('finalize_response')
            state['steps_taken'] = steps

            # Calculate processing time
            if state.get('timestamp'):
                start_time = datetime.fromisoformat(state['timestamp'])
                end_time = datetime.now()
                processing_time = (end_time - start_time).total_seconds()
                state['processing_time'] = processing_time

            # Ensure response is set
            if not state.get('response'):
                state['response'] = "Обработката заврши успешно."

            # Mark as complete
            state['should_end'] = True
            state['current_step'] = 'completed'

            logger.info(f"✅ Response finalized. Steps: {', '.join(steps)}")

        except Exception as e:
            logger.error(f"❌ Error in finalize_response: {e}")
            state['error'] = str(e)
            state['should_end'] = True

        return state

