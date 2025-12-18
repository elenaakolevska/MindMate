"""
Quiz Generator Service using Llama3

This service generates quizzes from uploaded study materials using
RAG (Retrieval-Augmented Generation) with Ollama Llama3.
"""

import json
import logging
import requests
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

from ..models import Quiz, QuizQuestion, StudyMaterial, Student, StudentPreferences
from .rag_retriever import PostgresRAGRetriever

logger = logging.getLogger(__name__)


@dataclass
class QuizGenerationOptions:
    """Options for quiz generation"""
    questions_count: int = 10
    quiz_type: str = "mixed"  # 'multiple_choice', 'true_false', 'mixed'
    difficulty: str = "medium"  # 'easy', 'medium', 'hard'
    subject_filter: Optional[str] = None
    material_ids: Optional[List[int]] = None


class QuizGenerator:
    """
    AI-powered quiz generator using study materials and Llama3
    """
    
    def __init__(self, ollama_url: str = "http://host.docker.internal:11434"):
        """Initialize quiz generator with Ollama connection"""
        self.ollama_url = ollama_url
        self.model_name = "llama3.2:3b"  # Use smaller model for better performance
        # RAG retriever will be initialized per student when needed
    
    def generate_quiz(
        self,
        student_id: int,
        options: QuizGenerationOptions
    ) -> Tuple[Quiz, List[QuizQuestion]]:
        """
        Generate a quiz from student's study materials
        
        Args:
            student_id: ID of the student
            options: Quiz generation options
            
        Returns:
            Tuple of (Quiz object, List of QuizQuestion objects)
        """
        logger.info(f"Generating quiz for student {student_id} with options: {options}")
        
        try:
            # Get student and preferences
            student = Student.objects.get(id=student_id)
            preferences = getattr(student, 'preferences', None)
            
            # Initialize RAG retriever for this student
            rag_retriever = PostgresRAGRetriever(student_id=str(student_id))
            
            # Adjust options based on preferences
            if preferences and not options.difficulty:
                options.difficulty = preferences.difficulty_preference or 'medium'
            
            # Get relevant content from study materials
            content_chunks = self._get_study_content(student_id, options, rag_retriever)
            
            if not content_chunks:
                raise ValueError("No study materials found for quiz generation")
            
            # Generate questions using Llama3
            questions_data = self._generate_questions_with_llm(content_chunks, options)
            
            # Create Quiz object
            quiz = self._create_quiz_object(student_id, options, questions_data)
            
            # Create QuizQuestion objects
            quiz_questions = self._create_quiz_questions(quiz, questions_data)
            
            logger.info(f"Successfully generated quiz with {len(quiz_questions)} questions")
            return quiz, quiz_questions
            
        except Exception as e:
            logger.error(f"Failed to generate quiz: {e}")
            raise
    
    def _get_study_content(
        self,
        student_id: int,
        options: QuizGenerationOptions,
        rag_retriever: PostgresRAGRetriever
    ) -> List[Dict]:
        """Get relevant content chunks from study materials"""
        try:
            # If specific materials are requested, get content from those
            if options.material_ids:
                content_chunks = []
                for material_id in options.material_ids:
                    chunks = rag_retriever.vector_store.get_document_chunks(material_id)
                    content_chunks.extend(chunks)
            else:
                # Use RAG retriever to get diverse content
                broad_queries = [
                    "key concepts and definitions",
                    "important facts and information", 
                    "main topics and principles",
                    "examples and applications"
                ]
                
                content_chunks = []
                for query in broad_queries:
                    results = rag_retriever.retrieve_context(
                        student_id=student_id,
                        query=query,
                        top_k=3,
                        subject_filter=options.subject_filter
                    )
                    
                    # Convert RetrievalResult to dict format
                    for result in results:
                        content_chunks.append({
                            'text': result.text,
                            'metadata': {
                                'document_title': result.document_title,
                                'subject': result.subject,
                                'document_id': result.document_id
                            }
                        })
            
            # Remove duplicates and limit content
            seen_texts = set()
            unique_chunks = []
            for chunk in content_chunks:
                text_key = chunk['text'][:100]  # First 100 chars as key
                if text_key not in seen_texts:
                    seen_texts.add(text_key)
                    unique_chunks.append(chunk)
                    
                if len(unique_chunks) >= 15:  # Limit for performance
                    break
            
            logger.info(f"Retrieved {len(unique_chunks)} unique content chunks")
            return unique_chunks
            
        except Exception as e:
            logger.error(f"Error retrieving study content: {e}")
            return []
    
    def _generate_questions_with_llm(
        self,
        content_chunks: List[Dict],
        options: QuizGenerationOptions
    ) -> List[Dict]:
        """Generate quiz questions using Llama3"""
        try:
            # Prepare content for LLM
            content_text = self._prepare_content_for_llm(content_chunks)
            
            # Build prompt based on quiz type and difficulty
            prompt = self._build_quiz_generation_prompt(content_text, options)
            
            # Query Llama3
            llm_response = self._query_ollama(prompt)
            
            # Parse LLM response into structured questions
            questions_data = self._parse_quiz_response(llm_response, options)
            
            return questions_data
            
        except Exception as e:
            logger.error(f"Error generating questions with LLM: {e}")
            # Fallback: create simple questions from content
            return self._create_fallback_questions(content_chunks, options)
    
    def _prepare_content_for_llm(self, content_chunks: List[Dict]) -> str:
        """Prepare study material content for LLM prompt"""
        content_parts = []
        
        for i, chunk in enumerate(content_chunks[:10], 1):  # Limit to prevent token overflow
            title = chunk.get('metadata', {}).get('document_title', 'Study Material')
            text = chunk['text']
            content_parts.append(f"Content {i} (from {title}):\\n{text}")
        
        return "\\n\\n".join(content_parts)
    
    def _build_quiz_generation_prompt(
        self,
        content_text: str,
        options: QuizGenerationOptions
    ) -> str:
        """Build prompt for Llama3.2 to generate quiz questions"""
        
        difficulty_guidance = {
            'easy': "Focus on basic recall, definitions, and simple concepts. Questions should test fundamental understanding.",
            'medium': "Include application questions, analysis of concepts, and connections between ideas. Moderate complexity.", 
            'hard': "Create challenging questions requiring synthesis, evaluation, critical thinking, and complex problem-solving."
        }
        
        type_guidance = {
            'multiple_choice': "Create multiple choice questions with 4 options (A, B, C, D) and exactly one correct answer.",
            'true_false': "Create true/false questions with clear, unambiguous statements.",
            'mixed': "Create a mix of multiple choice and true/false questions."
        }
        
        prompt = f"""You are an expert quiz creator. Create {options.questions_count} quiz questions from the study material below.

DIFFICULTY: {options.difficulty.upper()} - {difficulty_guidance.get(options.difficulty, '')}

QUESTION TYPES: {type_guidance.get(options.quiz_type, '')}

CRITICAL FORMATTING REQUIREMENTS:
1. Start each question with "QUESTION X:" where X is the number
2. Follow with "TYPE: multiple_choice" or "TYPE: true_false"  
3. Follow with "QUESTION: [your question text]"
4. For multiple choice: "OPTIONS: A) option1, B) option2, C) option3, D) option4"
5. For true/false: "OPTIONS: A) True, B) False"
6. Follow with "CORRECT_ANSWER: A" (or B, C, D)
7. Follow with "EXPLANATION: [why this is correct]"
8. Leave blank line between questions

EXAMPLE FORMAT:

QUESTION 1:
TYPE: multiple_choice
QUESTION: What is the main concept discussed in the study material?
OPTIONS: A) Concept A, B) Concept B, C) Concept C, D) Concept D
CORRECT_ANSWER: A
EXPLANATION: Based on the study material, Concept A is clearly stated as the main topic.

QUESTION 2:
TYPE: true_false  
QUESTION: The study material states that photosynthesis occurs in chloroplasts.
OPTIONS: A) True, B) False
CORRECT_ANSWER: A
EXPLANATION: The material explicitly mentions that photosynthesis takes place in chloroplasts.

STUDY MATERIAL:
{content_text}

Now create {options.questions_count} questions following the exact format above:"""

        return prompt
    
    def _query_ollama(self, prompt: str) -> str:
        """Query Ollama API with the prompt"""
        try:
            logger.info(f"Querying Ollama at {self.ollama_url} with model {self.model_name}")
            
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,  # Lower temperature for more consistent output
                        "top_k": 40,
                        "top_p": 0.9,
                    }
                },
                timeout=120  # 2 minutes timeout for quiz generation
            )
            
            if response.status_code == 200:
                result = response.json()
                ollama_response = result.get('response', '').strip()
                logger.info(f"Ollama response length: {len(ollama_response)} characters")
                return ollama_response
            else:
                logger.error(f"Ollama API error: {response.status_code} - {response.text}")
                raise requests.RequestException(f"Ollama API error: {response.status_code}")
                
        except requests.RequestException as e:
            logger.error(f"Failed to query Ollama: {e}")
            raise
    
    def _parse_quiz_response(
        self,
        llm_response: str,
        options: QuizGenerationOptions
    ) -> List[Dict]:
        """Parse LLM response into structured question data"""
        questions = []
        
        try:
            # Split response into individual questions
            question_blocks = re.split(r'QUESTION\s+\d+:', llm_response, flags=re.IGNORECASE)
            question_blocks = [block.strip() for block in question_blocks if block.strip()]
            
            for block in question_blocks:
                try:
                    question_data = self._parse_single_question(block)
                    if question_data:
                        questions.append(question_data)
                except Exception as e:
                    logger.warning(f"Failed to parse question block: {e}")
                    continue
            
            # Ensure we have the requested number of questions
            if len(questions) < options.questions_count:
                logger.warning(f"Generated only {len(questions)} questions, requested {options.questions_count}")
            
            return questions[:options.questions_count]  # Limit to requested count
            
        except Exception as e:
            logger.error(f"Failed to parse quiz response: {e}")
            return []
    
    def _parse_single_question(self, question_block: str) -> Optional[Dict]:
        """Parse a single question block into structured data"""
        try:
            lines = [line.strip() for line in question_block.split('\n') if line.strip()]
            
            question_data = {
                'type': 'true_false',  # default
                'question': '',
                'options': [],
                'correct_answer': '',
                'explanation': ''
            }
            
            i = 0
            while i < len(lines):
                line = lines[i]
                line_lower = line.lower()
                
                if line_lower.startswith('type:'):
                    type_value = line.split(':', 1)[1].strip()
                    question_data['type'] = type_value
                    
                elif line_lower.startswith('question:'):
                    question_text = line.split(':', 1)[1].strip()
                    question_data['question'] = question_text
                    
                elif line_lower.startswith('options:'):
                    options_text = line.split(':', 1)[1].strip()
                    question_data['options'] = self._parse_options(options_text)
                    
                elif line_lower.startswith('correct_answer:'):
                    answer = line.split(':', 1)[1].strip()
                    question_data['correct_answer'] = answer
                    
                elif line_lower.startswith('explanation:'):
                    explanation = line.split(':', 1)[1].strip()
                    # Handle multi-line explanations
                    j = i + 1
                    while j < len(lines) and not any(lines[j].lower().startswith(prefix) 
                                                   for prefix in ['type:', 'question:', 'options:', 'correct_answer:', 'explanation:']):
                        explanation += ' ' + lines[j].strip()
                        j += 1
                    question_data['explanation'] = explanation
                    i = j - 1  # Adjust index to account for consumed lines
                    
                i += 1
            
            # Validate required fields
            if not question_data['question']:
                logger.warning(f"Missing question text: {question_data}")
                return None
                
            if not question_data['correct_answer']:
                logger.warning(f"Missing correct answer: {question_data}")
                return None
            
            # Set default options for true/false if missing
            if question_data['type'] == 'true_false' and not question_data['options']:
                question_data['options'] = ['True', 'False']
                
            # Set default explanation if missing
            if not question_data['explanation']:
                question_data['explanation'] = 'This is the correct answer based on the study material.'
            
            return question_data
            
        except Exception as e:
            logger.error(f"Error parsing single question: {e}")
            return None
    
    def _parse_options(self, options_text: str) -> List[str]:
        """Parse question options from text"""
        try:
            # Handle different option formats
            options = []
            
            # Remove extra characters and clean up
            cleaned_text = options_text.strip()
            
            # Try to split by letter patterns like A), B), C), D)
            if re.search(r'[ABCD]\)', cleaned_text):
                # Split by A), B), C), D) patterns
                parts = re.split(r'[ABCD]\)\s*', cleaned_text)
                options = [part.strip().rstrip(',').strip() for part in parts if part.strip()]
            
            # If that didn't work, try comma separation
            elif ',' in cleaned_text:
                options = [part.strip() for part in cleaned_text.split(',') if part.strip()]
            
            # If still no options, use the whole text as single option
            else:
                options = [cleaned_text]
            
            # Clean up options and limit to 4
            final_options = []
            for opt in options:
                if opt and len(opt) > 0:
                    # Remove leading/trailing punctuation
                    clean_opt = re.sub(r'^[^\w]*|[^\w]*$', '', opt)
                    if clean_opt:
                        final_options.append(clean_opt)
            
            return final_options[:4]  # Limit to 4 options
            
        except Exception as e:
            logger.error(f"Error parsing options: {e}")
            # Return default options based on common patterns
            if 'true' in options_text.lower() or 'false' in options_text.lower():
                return ['True', 'False']
            else:
                return ['Option A', 'Option B', 'Option C', 'Option D']
    
    def _create_fallback_questions(
        self,
        content_chunks: List[Dict],
        options: QuizGenerationOptions
    ) -> List[Dict]:
        """Create simple fallback questions when LLM fails"""
        questions = []
        
        # Create questions up to the requested count
        for i in range(options.questions_count):
            # Cycle through available chunks if we need more questions than chunks
            chunk_idx = i % len(content_chunks)
            chunk = content_chunks[chunk_idx]
            
            text = chunk['text']
            title = chunk.get('metadata', {}).get('document_title', 'Study Material')
            
            # Vary question types based on request
            if options.quiz_type == 'true_false' or (options.quiz_type == 'mixed' and i % 2 == 0):
                # Create a true/false question
                question = {
                    'type': 'true_false',
                    'question': f"The following statement from '{title}' is accurate: {text[:150]}...",
                    'options': ['True', 'False'],
                    'correct_answer': 'A',  # Always true since it's from their material
                    'explanation': f"This statement is directly from your study material '{title}'."
                }
            else:
                # Create a multiple choice question with generated options
                question = {
                    'type': 'multiple_choice',
                    'question': f"Based on the content from '{title}', which statement is correct?",
                    'options': [
                        text[:100] + "..." if len(text) > 100 else text,  # Correct option
                        "This is an incorrect option A",
                        "This is an incorrect option B", 
                        "This is an incorrect option C"
                    ],
                    'correct_answer': 'A',
                    'explanation': f"The correct answer is directly from your study material '{title}'."
                }
            
            questions.append(question)
        
        logger.info(f"Created {len(questions)} fallback questions (requested: {options.questions_count})")
        return questions
    
    def _create_quiz_object(
        self,
        student_id: int,
        options: QuizGenerationOptions,
        questions_data: List[Dict]
    ) -> Quiz:
        """Create and save Quiz object"""
        try:
            # Determine subject from content or options
            subject = options.subject_filter or "General"
            
            # Determine primary material if available
            primary_material = None
            if options.material_ids:
                try:
                    primary_material = StudyMaterial.objects.get(id=options.material_ids[0])
                    subject = primary_material.subject or subject
                except StudyMaterial.DoesNotExist:
                    pass
            
            quiz = Quiz.objects.create(
                quiz_type=options.quiz_type,
                subject=subject,
                difficulty=options.difficulty,
                questions_count=len(questions_data),
                generated_from_material=primary_material
            )
            
            return quiz
            
        except Exception as e:
            logger.error(f"Error creating quiz object: {e}")
            raise
    
    def _create_quiz_questions(
        self,
        quiz: Quiz,
        questions_data: List[Dict]
    ) -> List[QuizQuestion]:
        """Create and save QuizQuestion objects"""
        quiz_questions = []
        
        try:
            for question_data in questions_data:
                # Prepare options for storage
                options_for_storage = question_data['options'] if question_data['type'] == 'multiple_choice' else None
                
                quiz_question = QuizQuestion.objects.create(
                    quiz=quiz,
                    question_text=question_data['question'],
                    question_type=question_data['type'],
                    correct_answer=question_data['correct_answer'],
                    options=options_for_storage,
                    explanation=question_data.get('explanation', '')
                )
                
                quiz_questions.append(quiz_question)
            
            logger.info(f"Created {len(quiz_questions)} quiz questions")
            return quiz_questions
            
        except Exception as e:
            logger.error(f"Error creating quiz questions: {e}")
            raise
    
    def get_student_difficulty_preference(self, student_id: int) -> str:
        """Get student's difficulty preference from their profile"""
        try:
            student = Student.objects.get(id=student_id)
            preferences = getattr(student, 'preferences', None)
            if preferences:
                return preferences.difficulty_preference or 'medium'
            return 'medium'
        except Student.DoesNotExist:
            return 'medium'
    
    def validate_quiz_generation_requirements(self, student_id: int) -> Dict[str, bool]:
        """Validate that student has materials available for quiz generation"""
        try:
            # Check if student has any study materials
            student = Student.objects.get(id=student_id)
            materials = StudyMaterial.objects.filter(
                student=student,
                processing_status='completed'
            )
            
            has_materials = materials.exists()
            
            # Check if materials have content in vector store
            has_vector_data = False
            if has_materials:
                # Create RAG retriever to check stats
                rag_retriever = PostgresRAGRetriever(student_id=str(student_id))
                stats = rag_retriever.get_search_stats(student_id)
                has_vector_data = stats.get('available_documents', 0) > 0
            
            return {
                'has_materials': has_materials,
                'has_vector_data': has_vector_data,
                'material_count': materials.count(),
                'can_generate_quiz': has_materials and has_vector_data
            }
            
        except Student.DoesNotExist:
            return {
                'has_materials': False,
                'has_vector_data': False,
                'material_count': 0,
                'can_generate_quiz': False
            }


# Singleton instance
_quiz_generator_instance = None

def get_quiz_generator() -> QuizGenerator:
    """Get singleton instance of QuizGenerator"""
    global _quiz_generator_instance
    if _quiz_generator_instance is None:
        _quiz_generator_instance = QuizGenerator()
    return _quiz_generator_instance
