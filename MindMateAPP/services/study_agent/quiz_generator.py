import json
import logging
import requests
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

from ...models import Quiz, QuizQuestion, StudyMaterial, Student, StudentPreferences
from .rag_retriever import RAGRetriever

logger = logging.getLogger(__name__)

@dataclass
class QuizGenerationOptions:
    """Options for quiz generation"""
    questions_count: int = 3
    quiz_type: str = 'mixed'
    difficulty: str = 'medium'
    subject_filter: Optional[str] = None
    material_ids: Optional[List[int]] = None


class QuizGenerator:
    def __init__(self, ollama_url: str, rag_retriever: Optional[RAGRetriever] = None):
        self.ollama_url = ollama_url
        self.rag_retriever = rag_retriever

    def generate_quiz_from_materials(self, question_count, material_ids, student: Student) -> List[QuizQuestion]:
        """Generate quiz from specific materials (legacy method)"""
        chunks = StudyMaterial.objects.filter(id__in=material_ids, student=student)
        content_list = [doc.content for doc in chunks if doc.content and doc.content.strip()]
        combined_content = " ".join(content_list)
        
        if not combined_content.strip():
            logger.warning(f"No content found in materials {material_ids} for student {student.id}")
            # Return empty list if no content
            return []
        
        # Truncate content if too long (keep first 2000 characters)
        if len(combined_content) > 2000:
            combined_content = combined_content[:2000] + "..."

        prompt = {
            "model": "qwen2.5:7b",
            "prompt": f"""Create a quiz with {question_count} multiple choice questions in Macedonian based on this content:

{combined_content}

IMPORTANT: You must respond with VALID JSON only. No other text, no explanations, no markdown.

Required JSON format:
{{
    "questions": [
        {{
            "question_text": "Question in Macedonian?",
            "question_type": "multiple_choice",
            "correct_answer": "A",
            "options": {{"A": "Option A", "B": "Option B", "C": "Option C", "D": "Option D"}},
            "explanation": "Explanation in Macedonian"
        }}
    ]
}}

Rules:
- Generate exactly {question_count} questions
- Each question must have 4 options (A, B, C, D)
- Correct answer must be one of: A, B, C, D
- All text in Macedonian
- Return ONLY the JSON object, nothing else
- Ensure the JSON is properly formatted and complete
- Keep explanations concise to avoid truncation

JSON:""",
            "stream": False,
            "options": {
                "temperature": 0.3,
                "top_p": 0.8,
                "max_tokens": 8192,
                "num_predict": 8192
            }
        }

        response = requests.post(
            f"{self.ollama_url}/api/generate",
            json=prompt,
            timeout=120
        )

        if response.status_code != 200:
            logger.error(f"Failed to generate quiz: {response.text}")
            raise Exception("Quiz generation failed")

        quiz_data = response.json()
        response_text = quiz_data.get("response", "").strip()
        logger.info(f"LLM Response: {response_text[:500]}...")
        
        quiz_questions = self._parse_quiz_response(response_text)
        return quiz_questions

    def _parse_quiz_response(self, response_content: str) -> List[QuizQuestion]:
        """Parse the JSON response from Ollama and create QuizQuestion objects."""
        try:
            # Clean the response - remove any markdown formatting
            response_content = response_content.strip()
            if response_content.startswith('```json'):
                response_content = response_content[7:]
            if response_content.endswith('```'):
                response_content = response_content[:-3]
            response_content = response_content.strip()
            
            # Try to find JSON in the response
            import re
            json_match = re.search(r'\{.*\}', response_content, re.DOTALL)
            if json_match:
                response_content = json_match.group(0)
            
            # Try to fix common JSON issues
            response_content = self._fix_json_response(response_content)
            
            quiz_data = json.loads(response_content)
            
            quiz_questions = []
            for question_data in quiz_data.get("questions", []):
                question = QuizQuestion(
                    question_text=question_data.get("question_text", ""),
                    question_type=question_data.get("question_type", "multiple_choice"),
                    correct_answer=question_data.get("correct_answer", ""),
                    options=question_data.get("options", {}),
                    explanation=question_data.get("explanation", "")
                )
                quiz_questions.append(question)
            
            logger.info(f"Successfully parsed {len(quiz_questions)} questions")
            return quiz_questions
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse quiz response JSON: {e}")
            logger.error(f"Response content: {response_content[:1000]}")
            
            # Try to extract partial questions if JSON is malformed
            return self._parse_partial_questions(response_content)
        except Exception as e:
            logger.error(f"Error parsing quiz response: {e}")
            logger.error(f"Response content: {response_content[:1000]}")
            return []

    def _fix_json_response(self, response_content: str) -> str:
        """Fix common JSON formatting issues in LLM responses"""
        # Remove trailing commas before closing braces/brackets
        response_content = re.sub(r',(\s*[}\]])', r'\1', response_content)
        
        # Fix unescaped quotes in strings (basic fix)
        # This is tricky, so we'll be conservative
        
        # Ensure proper closing of JSON structure
        if response_content.count('{') > response_content.count('}'):
            response_content += '}' * (response_content.count('{') - response_content.count('}'))
        if response_content.count('[') > response_content.count(']'):
            response_content += ']' * (response_content.count('[') - response_content.count(']'))
            
        return response_content

    def _parse_partial_questions(self, response_content: str) -> List[QuizQuestion]:
        """Attempt to parse partial questions from malformed JSON"""
        questions = []
        
        try:
            # Look for question patterns in the text
            question_pattern = r'"question_text"\s*:\s*"([^"]+)"'
            type_pattern = r'"question_type"\s*:\s*"([^"]+)"'
            answer_pattern = r'"correct_answer"\s*:\s*"([^"]+)"'
            options_pattern = r'"options"\s*:\s*(\{[^{}]+\})'
            explanation_pattern = r'"explanation"\s*:\s*"([^"]*)"'
            
            # Find all question blocks
            question_blocks = re.findall(r'\{[^{}]*"question_text"[^{}]*\}', response_content, re.DOTALL)
            
            for block in question_blocks:
                question_text_match = re.search(question_pattern, block)
                type_match = re.search(type_pattern, block)
                answer_match = re.search(answer_pattern, block)
                options_match = re.search(options_pattern, block)
                explanation_match = re.search(explanation_pattern, block)
                
                if question_text_match:
                    try:
                        options = {}
                        if options_match:
                            options_str = options_match.group(1)
                            options = json.loads(options_str)
                        
                        question = QuizQuestion(
                            question_text=question_text_match.group(1),
                            question_type=type_match.group(1) if type_match else "multiple_choice",
                            correct_answer=answer_match.group(1) if answer_match else "",
                            options=options,
                            explanation=explanation_match.group(1) if explanation_match else ""
                        )
                        questions.append(question)
                    except Exception as e:
                        logger.warning(f"Failed to parse individual question: {e}")
                        continue
            
            logger.info(f"Parsed {len(questions)} questions from partial response")
            return questions
            
        except Exception as e:
            logger.error(f"Failed to parse partial questions: {e}")
            return []

    def validate_quiz_generation_requirements(self, student_id: int) -> Dict:
        """Validate if student can generate quizzes"""
        try:
            student = Student.objects.get(id=student_id)
            materials = StudyMaterial.objects.filter(student=student)
            
            return {
                'can_generate_quiz': materials.exists(),
                'has_materials': materials.exists(),
                'has_vector_data': True,  # Assume vector data exists for now
                'material_count': materials.count()
            }
        except Exception as e:
            logger.error(f"Error validating quiz generation requirements: {e}")
            return {
                'can_generate_quiz': False,
                'has_materials': False,
                'has_vector_data': False,
                'material_count': 0
            }

    def generate_quiz(self, student_id: int, questions_count: int = 10, quiz_type: str = 'mixed', difficulty: str = 'medium', subject_filter: Optional[str] = None, material_ids: Optional[List[int]] = None) -> Tuple[Quiz, List[QuizQuestion]]:
        """Generate a quiz with the given options"""
        try:
            student = Student.objects.get(id=student_id)
            # Get materials based on options
            materials_query = StudyMaterial.objects.filter(student=student)
            if material_ids:
                materials_query = materials_query.filter(id__in=material_ids)
            if subject_filter:
                materials_query = materials_query.filter(subject__icontains=subject_filter)
            materials = materials_query.all()
            if not materials:
                raise ValueError("No study materials found for quiz generation")
            # Combine content from materials
            content_chunks = []
            for material in materials:
                if material.content:
                    content_chunks.append(material.content)
            combined_content = " ".join(content_chunks)
            # Generate quiz using existing method
            quiz_questions = self.generate_quiz_from_materials(questions_count, [m.id for m in materials], student)
            # Prevent creation of quiz with 0 questions
            if not quiz_questions:
                logger.error("No questions could be parsed from LLM response.")
                raise Exception("Quiz generation failed: No valid questions could be parsed. Please try again or use different materials.")
            # Create actual Quiz model instance
            quiz = Quiz.objects.create(
                quiz_type=quiz_type,
                subject=subject_filter or 'General',
                difficulty=difficulty,
                questions_count=questions_count,
                generated_from_material=materials[0] if materials else None
            )
            # Create QuizQuestion instances
            quiz_questions_db = []
            for q_data in quiz_questions:
                question = QuizQuestion.objects.create(
                    quiz=quiz,
                    question_text=q_data.question_text,
                    question_type=q_data.question_type,
                    correct_answer=q_data.correct_answer,
                    options=q_data.options,
                    explanation=q_data.explanation
                )
                quiz_questions_db.append(question)
            return quiz, quiz_questions_db
        except Exception as e:
            logger.error(f"Error generating quiz: {e}")
            raise

    def get_student_difficulty_preference(self, student_id: int) -> str:
        """Get student's preferred difficulty level"""
        try:
            student = Student.objects.get(id=student_id)
            preferences = StudentPreferences.objects.filter(student=student).first()
            if preferences and hasattr(preferences, 'difficulty_preference'):
                return preferences.difficulty_preference
        except Exception as e:
            logger.error(f"Error getting student difficulty preference: {e}")
        
        return 'medium'  # Default difficulty


def get_quiz_generator():
    """Get a quiz generator instance"""
    ollama_url = "http://host.docker.internal:11434"  # Docker-compatible URL
    return QuizGenerator(ollama_url=ollama_url)