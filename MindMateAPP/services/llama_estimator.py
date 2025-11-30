"""
AI-powered Task Estimation using LLaMA3

This module integrates LLaMA3 to provide intelligent task estimation
with prompt engineering for educational tasks.
"""

import json
import logging
from typing import Dict, Optional, List
from dataclasses import dataclass

from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

from .task_estimator import TaskEstimate

logger = logging.getLogger(__name__)


@dataclass
class AIEstimationContext:
    """Context for AI-powered estimation"""
    student_level: str  # 'high_school', 'college', 'graduate'
    subject_area: str
    task_complexity: str  # 'basic', 'intermediate', 'advanced'
    historical_performance: Dict
    learning_style: str


class LlamaTaskEstimator:
    """
    LLaMA3-powered task estimation with educational context awareness
    """
    
    def __init__(self, model_name: str = "microsoft/DialoGPT-medium"):
        """
        Initialize LLaMA estimator
        
        Note: Using DialoGPT as a placeholder. In production, you would use:
        - meta-llama/Llama-2-7b-chat-hf
        - meta-llama/Llama-2-13b-chat-hf
        - or similar LLaMA models
        """
        self.model_name = model_name
        self.tokenizer = None
        self.model = None
        self._initialize_model()
    
    def _initialize_model(self):
        """Initialize the LLaMA model (lazy loading)"""
        try:
            # In production, you would load the actual LLaMA model here
            # For demonstration, we'll use a lighter model
            logger.info(f"Initializing AI model: {self.model_name}")
            
            # Uncomment for actual LLaMA usage:
            # self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            # self.model = AutoModelForCausalLM.from_pretrained(
            #     self.model_name,
            #     torch_dtype=torch.float16,
            #     device_map="auto"
            # )
            
            logger.info("AI model initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize AI model: {e}")
            self.model = None
            self.tokenizer = None
    
    def estimate_with_ai(
        self, 
        task_description: str, 
        context: AIEstimationContext,
        base_estimate: float
    ) -> Dict:
        """
        Use LLaMA3 to refine task estimation
        
        Args:
            task_description: Natural language task description
            context: AI estimation context
            base_estimate: Base estimation from heuristic methods
            
        Returns:
            Dict with AI estimation results
        """
        if not self._is_model_available():
            return self._fallback_ai_estimation(task_description, context, base_estimate)
        
        try:
            # Prepare the prompt for LLaMA
            prompt = self._build_estimation_prompt(task_description, context, base_estimate)
            
            # Get AI response
            ai_response = self._query_llama(prompt)
            
            # Parse AI response
            result = self._parse_ai_response(ai_response, base_estimate)
            
            return result
            
        except Exception as e:
            logger.error(f"Error in AI estimation: {e}")
            return self._fallback_ai_estimation(task_description, context, base_estimate)
    
    def _build_estimation_prompt(
        self, 
        task_description: str, 
        context: AIEstimationContext, 
        base_estimate: float
    ) -> str:
        """Build a comprehensive prompt for LLaMA estimation"""
        
        prompt = f"""You are an expert educational time estimation assistant helping students plan their study time effectively.

STUDENT CONTEXT:
- Academic Level: {context.student_level}
- Subject Area: {context.subject_area}
- Learning Style: {context.learning_style}
- Task Complexity: {context.task_complexity}

HISTORICAL PERFORMANCE:
"""
        
        # Add historical performance data
        if context.historical_performance:
            if context.historical_performance.get('accuracy_rate'):
                prompt += f"- Average accuracy on similar tasks: {context.historical_performance['accuracy_rate']:.1f}%\n"
            if context.historical_performance.get('task_count'):
                prompt += f"- Completed similar tasks: {context.historical_performance['task_count']}\n"
            if context.historical_performance.get('avg_study_duration'):
                prompt += f"- Average study duration: {context.historical_performance['avg_study_duration']:.1f} hours\n"
        
        prompt += f"""
TASK TO ESTIMATE:
"{task_description}"

BASELINE ESTIMATE: {base_estimate:.1f} hours

INSTRUCTIONS:
Please provide a refined time estimation considering:
1. The student's academic level and learning style
2. Historical performance patterns
3. Task complexity and subject difficulty
4. Common challenges students face with this type of task

Respond in JSON format:
{{
    "estimated_hours": <number>,
    "confidence_score": <0-100>,
    "reasoning": "<explanation>",
    "factors_considered": ["<factor1>", "<factor2>", ...],
    "difficulty_assessment": "<easy|moderate|challenging|very_challenging>",
    "recommended_approach": "<study strategy recommendation>",
    "potential_obstacles": ["<obstacle1>", "<obstacle2>", ...],
    "time_breakdown": {{
        "preparation": <hours>,
        "main_work": <hours>,
        "review": <hours>
    }}
}}

Be realistic and consider that students often underestimate task complexity. Provide practical, actionable advice.
"""
        
        return prompt
    
    def _query_llama(self, prompt: str) -> str:
        """Query the LLaMA model with the prepared prompt"""
        if not self.model or not self.tokenizer:
            raise RuntimeError("Model not available")
        
        # Tokenize input
        inputs = self.tokenizer.encode(prompt, return_tensors='pt')
        
        # Generate response
        with torch.no_grad():
            outputs = self.model.generate(
                inputs,
                max_length=inputs.shape[1] + 500,
                temperature=0.7,
                do_sample=True,
                pad_token_id=self.tokenizer.eos_token_id,
                num_return_sequences=1
            )
        
        # Decode response
        response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # Extract just the generated part (after the prompt)
        generated_text = response[len(prompt):].strip()
        
        return generated_text
    
    def _parse_ai_response(self, response: str, base_estimate: float) -> Dict:
        """Parse LLaMA response and extract structured estimation data"""
        try:
            # Try to extract JSON from the response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                result = json.loads(json_str)
                
                # Validate and sanitize the result
                return self._validate_ai_result(result, base_estimate)
            else:
                # If no valid JSON found, parse text response
                return self._parse_text_response(response, base_estimate)
                
        except json.JSONDecodeError:
            return self._parse_text_response(response, base_estimate)
    
    def _validate_ai_result(self, result: Dict, base_estimate: float) -> Dict:
        """Validate and sanitize AI estimation result"""
        validated_result = {
            'estimated_hours': base_estimate,
            'confidence_score': 50,
            'reasoning': "AI-generated estimation",
            'factors_considered': [],
            'difficulty_assessment': 'moderate',
            'recommended_approach': 'Standard study approach',
            'potential_obstacles': [],
            'time_breakdown': {
                'preparation': 0.2 * base_estimate,
                'main_work': 0.7 * base_estimate,
                'review': 0.1 * base_estimate
            }
        }
        
        # Safely extract values with validation
        if 'estimated_hours' in result:
            hours = float(result['estimated_hours'])
            # Ensure reasonable bounds (0.1 to 20 hours)
            validated_result['estimated_hours'] = max(0.1, min(20.0, hours))
        
        if 'confidence_score' in result:
            confidence = int(result['confidence_score'])
            validated_result['confidence_score'] = max(0, min(100, confidence))
        
        for key in ['reasoning', 'difficulty_assessment', 'recommended_approach']:
            if key in result and isinstance(result[key], str):
                validated_result[key] = result[key][:500]  # Limit length
        
        for key in ['factors_considered', 'potential_obstacles']:
            if key in result and isinstance(result[key], list):
                validated_result[key] = result[key][:5]  # Limit to 5 items
        
        if 'time_breakdown' in result and isinstance(result['time_breakdown'], dict):
            breakdown = result['time_breakdown']
            total_hours = validated_result['estimated_hours']
            
            validated_result['time_breakdown'] = {
                'preparation': min(breakdown.get('preparation', 0.2 * total_hours), total_hours * 0.5),
                'main_work': min(breakdown.get('main_work', 0.7 * total_hours), total_hours * 0.9),
                'review': min(breakdown.get('review', 0.1 * total_hours), total_hours * 0.3)
            }
        
        return validated_result
    
    def _parse_text_response(self, response: str, base_estimate: float) -> Dict:
        """Parse non-JSON text response from AI"""
        # Extract time estimates from text
        import re
        
        # Look for hour estimates in text
        hour_patterns = [
            r'(\d+(?:\.\d+)?)\s*hours?',
            r'(\d+(?:\.\d+)?)\s*hrs?',
            r'estimate.*?(\d+(?:\.\d+)?)',
        ]
        
        estimated_hours = base_estimate
        for pattern in hour_patterns:
            matches = re.findall(pattern, response.lower())
            if matches:
                try:
                    hours = float(matches[0])
                    if 0.1 <= hours <= 20:  # Reasonable bounds
                        estimated_hours = hours
                        break
                except ValueError:
                    continue
        
        # Extract reasoning (first sentence or paragraph)
        reasoning_match = re.search(r'[.!?]\s*([A-Z][^.!?]*[.!?])', response)
        reasoning = reasoning_match.group(1) if reasoning_match else "AI-generated estimation based on task analysis"
        
        return {
            'estimated_hours': estimated_hours,
            'confidence_score': 60,
            'reasoning': reasoning[:300],
            'factors_considered': ['AI text analysis', 'Task complexity assessment'],
            'difficulty_assessment': 'moderate',
            'recommended_approach': 'Follow structured study plan',
            'potential_obstacles': ['Time management', 'Task complexity'],
            'time_breakdown': {
                'preparation': 0.2 * estimated_hours,
                'main_work': 0.7 * estimated_hours,
                'review': 0.1 * estimated_hours
            }
        }
    
    def _fallback_ai_estimation(
        self, 
        task_description: str, 
        context: AIEstimationContext, 
        base_estimate: float
    ) -> Dict:
        """Provide intelligent fallback estimation when AI model is unavailable"""
        
        # Rule-based intelligence as fallback
        adjustments = []
        
        # Adjust based on student level
        level_multipliers = {
            'high_school': 1.0,
            'college': 1.2,
            'graduate': 1.4
        }
        level_mult = level_multipliers.get(context.student_level, 1.0)
        
        # Adjust based on complexity
        complexity_multipliers = {
            'basic': 0.8,
            'intermediate': 1.0,
            'advanced': 1.3
        }
        complexity_mult = complexity_multipliers.get(context.task_complexity, 1.0)
        
        # Adjust based on learning style
        learning_adjustments = {
            'visual': 0.9,      # Generally faster with visual materials
            'auditory': 1.1,    # May need more time for text-based tasks
            'kinesthetic': 1.2, # May need more hands-on time
            'reading_writing': 0.95
        }
        learning_mult = learning_adjustments.get(context.learning_style, 1.0)
        
        # Calculate adjusted estimate
        adjusted_estimate = base_estimate * level_mult * complexity_mult * learning_mult
        
        # Add historical performance adjustment
        if context.historical_performance.get('accuracy_rate'):
            accuracy = context.historical_performance['accuracy_rate'] / 100.0
            if accuracy < 0.6:
                adjusted_estimate *= 1.4
                adjustments.append("Increased time due to lower historical accuracy")
            elif accuracy > 0.85:
                adjusted_estimate *= 0.9
                adjustments.append("Reduced time due to strong historical performance")
        
        # Generate reasoning
        reasoning_parts = [
            f"Adjusted for {context.student_level} academic level",
            f"Considered {context.task_complexity} task complexity",
            f"Accounted for {context.learning_style} learning style"
        ]
        reasoning = "Intelligent estimation: " + ". ".join(reasoning_parts + adjustments)
        
        # Determine difficulty assessment
        total_multiplier = level_mult * complexity_mult * learning_mult
        if total_multiplier <= 0.9:
            difficulty = "easy"
        elif total_multiplier <= 1.1:
            difficulty = "moderate"
        elif total_multiplier <= 1.3:
            difficulty = "challenging"
        else:
            difficulty = "very_challenging"
        
        return {
            'estimated_hours': max(0.25, min(15.0, adjusted_estimate)),
            'confidence_score': 70,
            'reasoning': reasoning,
            'factors_considered': [
                f"Academic level ({context.student_level})",
                f"Task complexity ({context.task_complexity})",
                f"Learning style ({context.learning_style})",
                "Historical performance data"
            ],
            'difficulty_assessment': difficulty,
            'recommended_approach': self._get_recommended_approach(context, difficulty),
            'potential_obstacles': self._get_potential_obstacles(context, difficulty),
            'time_breakdown': {
                'preparation': 0.15 * adjusted_estimate,
                'main_work': 0.75 * adjusted_estimate,
                'review': 0.1 * adjusted_estimate
            }
        }
    
    def _get_recommended_approach(self, context: AIEstimationContext, difficulty: str) -> str:
        """Get recommended study approach based on context and difficulty"""
        approaches = {
            'visual': {
                'easy': "Use diagrams, charts, and visual aids to reinforce learning",
                'moderate': "Create mind maps and visual summaries while studying",
                'challenging': "Break down complex concepts into visual flowcharts and diagrams",
                'very_challenging': "Use multiple visual representations and practice with visual examples"
            },
            'auditory': {
                'easy': "Read materials aloud or discuss with study partners",
                'moderate': "Use audio recordings and verbal explanations",
                'challenging': "Explain concepts aloud and use discussion-based learning",
                'very_challenging': "Record yourself explaining concepts and listen back repeatedly"
            },
            'kinesthetic': {
                'easy': "Use hands-on practice and real-world applications",
                'moderate': "Combine reading with practical exercises and movement",
                'challenging': "Break study into active sessions with frequent breaks",
                'very_challenging': "Use physical models and extensive hands-on practice"
            },
            'reading_writing': {
                'easy': "Take detailed notes and create written summaries",
                'moderate': "Use structured note-taking and written practice",
                'challenging': "Create comprehensive written study guides and outlines",
                'very_challenging': "Write extensive notes, summaries, and practice problems"
            }
        }
        
        return approaches.get(context.learning_style, {}).get(
            difficulty, "Use a structured approach with regular breaks and review"
        )
    
    def _get_potential_obstacles(self, context: AIEstimationContext, difficulty: str) -> List[str]:
        """Get potential obstacles based on context and difficulty"""
        base_obstacles = {
            'easy': ["Overconfidence", "Rushing through material"],
            'moderate': ["Time management", "Maintaining focus"],
            'challenging': ["Concept complexity", "Information overload", "Motivation"],
            'very_challenging': ["High complexity", "Time pressure", "Stress", "Multiple difficult concepts"]
        }
        
        obstacles = base_obstacles.get(difficulty, ["Time management", "Task complexity"])
        
        # Add subject-specific obstacles
        if 'math' in context.subject_area.lower():
            obstacles.append("Mathematical problem-solving")
        elif 'science' in context.subject_area.lower():
            obstacles.append("Scientific concept understanding")
        elif 'language' in context.subject_area.lower():
            obstacles.append("Language comprehension")
        
        return obstacles[:4]  # Limit to 4 obstacles
    
    def _is_model_available(self) -> bool:
        """Check if AI model is available and loaded"""
        return self.model is not None and self.tokenizer is not None


class PromptEngineering:
    """
    Advanced prompt engineering for educational task estimation
    """
    
    @staticmethod
    def create_estimation_prompt(
        task_description: str,
        student_context: Dict,
        historical_data: Dict = None
    ) -> str:
        """Create optimized prompt for task estimation"""
        
        prompt = f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>

You are an expert educational time estimation assistant with deep knowledge of student learning patterns and academic task requirements. Your goal is to provide accurate, realistic time estimates that help students succeed.

<|eot_id|><|start_header_id|>user<|end_header_id|>

STUDENT PROFILE:
- Academic Level: {student_context.get('academic_level', 'Not specified')}
- Field of Study: {student_context.get('field_of_study', 'Not specified')}  
- Learning Style: {student_context.get('learning_style', 'Not specified')}
- Study Pace Preference: {student_context.get('study_pace', 'Not specified')}

TASK DESCRIPTION:
"{task_description}"

"""
        
        if historical_data:
            prompt += "HISTORICAL PERFORMANCE:\n"
            if historical_data.get('accuracy_rate'):
                prompt += f"- Average accuracy: {historical_data['accuracy_rate']:.1f}%\n"
            if historical_data.get('completion_rate'):
                prompt += f"- Task completion rate: {historical_data['completion_rate']:.1f}%\n"
            if historical_data.get('avg_time_deviation'):
                prompt += f"- Average time estimate deviation: {historical_data['avg_time_deviation']:.1f}%\n"
        
        prompt += """
ESTIMATION REQUIREMENTS:
1. Provide a realistic time estimate in hours (be conservative but not excessive)
2. Consider the student's academic level and learning style
3. Account for preparation, main work, and review time
4. Include potential challenges and mitigation strategies
5. Suggest optimal time management approach

Provide your response in the following JSON format:
{
    "estimated_hours": <float>,
    "confidence_percentage": <integer 1-100>,
    "time_breakdown": {
        "preparation": <float>,
        "active_work": <float>, 
        "review_consolidation": <float>
    },
    "difficulty_level": "<easy|moderate|challenging|very_challenging>",
    "key_factors": [
        "<factor1>",
        "<factor2>", 
        "<factor3>"
    ],
    "recommended_strategy": "<detailed_study_approach>",
    "potential_challenges": [
        "<challenge1>",
        "<challenge2>"
    ],
    "success_tips": [
        "<tip1>",
        "<tip2>"
    ]
}

<|eot_id|><|start_header_id|>assistant<|end_header_id|>"""
        
        return prompt
    
    @staticmethod
    def create_performance_analysis_prompt(
        student_data: Dict,
        task_history: List[Dict]
    ) -> str:
        """Create prompt for analyzing student performance patterns"""
        
        return f"""Analyze this student's task completion patterns and provide insights for improving time estimation accuracy:

STUDENT DATA:
{json.dumps(student_data, indent=2)}

RECENT TASK HISTORY:
{json.dumps(task_history, indent=2)}

Please analyze:
1. Estimation accuracy trends
2. Subject-specific performance patterns  
3. Time management strengths/weaknesses
4. Recommendations for improvement

Provide structured analysis in JSON format."""