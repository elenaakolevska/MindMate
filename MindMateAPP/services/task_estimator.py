"""
Time Agent Task Estimator Service

This service provides intelligent time estimation for student tasks by:
1. Analyzing historical performance data
2. Using AI/ML models for estimation
3. Learning from student patterns
4. Providing realistic time suggestions
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from django.db.models import Avg, Q
from django.utils import timezone

from ..models import (
    Student, StudySession, QuizResult, CalendarEvent, 
    StudyMaterial, ChatbotInteraction, StudentPreferences
)

logger = logging.getLogger(__name__)


@dataclass
class TaskEstimate:
    """Data class for task estimation results"""
    task_description: str
    estimated_hours: float
    confidence_level: float  # 0.0 to 1.0
    factors_considered: List[str]
    reasoning: str
    suggested_start_time: Optional[datetime] = None
    suggested_end_time: Optional[datetime] = None
    difficulty_adjustment: float = 1.0


class TaskEstimatorService:
    """
    Service for estimating task completion times using:
    - Historical performance analysis
    - AI-powered estimation
    - Student-specific patterns
    """
    
    # Default time estimates (in hours) for common task types
    DEFAULT_ESTIMATES = {
        'study': {
            'exam': {'base': 3.0, 'per_credit': 1.0, 'multiplier': 1.5},
            'quiz': {'base': 1.0, 'per_credit': 0.3, 'multiplier': 1.0},
            'homework': {'base': 2.0, 'per_credit': 0.5, 'multiplier': 1.2},
            'reading': {'base': 1.5, 'per_credit': 0.4, 'multiplier': 1.0},
            'assignment': {'base': 2.5, 'per_credit': 0.7, 'multiplier': 1.3},
            'project': {'base': 8.0, 'per_credit': 2.0, 'multiplier': 2.0},
        },
        'subjects': {
            'math': 1.3,
            'mathematics': 1.3,
            'calculus': 1.4,
            'algebra': 1.2,
            'physics': 1.4,
            'chemistry': 1.3,
            'biology': 1.1,
            'computer science': 1.5,
            'programming': 1.6,
            'coding': 1.6,
            'english': 1.0,
            'literature': 1.1,
            'history': 1.0,
            'psychology': 0.9,
            'sociology': 0.9,
        }
    }
    
    def __init__(self, student: Student):
        self.student = student
        self.student_preferences = getattr(student, 'preferences', None)
        
    def estimate_task_time(self, task_description: str, context: Dict = None) -> TaskEstimate:
        """
        Main method to estimate task completion time
        
        Args:
            task_description: Natural language description of the task
            context: Additional context (subject, deadline, etc.)
            
        Returns:
            TaskEstimate object with estimation details
        """
        try:
            # Parse task description to extract key information
            task_info = self._parse_task_description(task_description)
            
            # Apply context if provided
            if context:
                task_info.update(context)
            
            # Get historical performance data
            historical_data = self._get_historical_performance(task_info)
            
            # Calculate base estimate using multiple approaches
            base_estimate = self._calculate_base_estimate(task_info)
            
            # Apply historical adjustments
            historical_adjustment = self._apply_historical_adjustment(
                base_estimate, historical_data, task_info
            )
            
            # Apply student-specific factors
            student_adjustment = self._apply_student_factors(historical_adjustment, task_info)
            
            # Apply AI-powered refinement (if available)
            final_estimate = self._apply_ai_refinement(student_adjustment, task_info)
            
            # Generate reasoning and factors considered
            factors = self._generate_estimation_factors(
                task_info, historical_data, base_estimate, final_estimate
            )
            
            # Calculate confidence level
            confidence = self._calculate_confidence(historical_data, task_info)
            
            return TaskEstimate(
                task_description=task_description,
                estimated_hours=round(final_estimate, 2),  # Round to avoid long decimals
                confidence_level=confidence,
                factors_considered=factors,
                reasoning=self._generate_reasoning(task_info, factors, final_estimate),
                difficulty_adjustment=task_info.get('difficulty_multiplier', 1.0)
            )
        
        except Exception as e:
            logger.error(f"Error estimating task time: {e}")
            # Return safe default estimate
            return TaskEstimate(
                task_description=task_description,
                estimated_hours=2.0,
                confidence_level=0.3,
                factors_considered=["Default fallback estimate"],
                reasoning="Using default estimate due to insufficient data"
            )
    
    def _parse_task_description(self, description: str) -> Dict:
        """Extract task type, subject, and other info from description"""
        description_lower = description.lower()
        
        task_info = {
            'original_description': description,
            'task_type': 'study',  # default
            'subject': None,
            'difficulty_multiplier': 1.0,
            'urgency': 'normal',
            'estimated_pages': None,
        }
        
        # Detect task type
        task_type_keywords = {
            'exam': ['exam', 'test', 'midterm', 'final', 'assessment'],
            'quiz': ['quiz', 'pop quiz', 'short test'],
            'homework': ['homework', 'hw', 'assignment', 'problem set', 'exercises'],
            'reading': ['read', 'reading', 'chapter', 'pages', 'textbook', 'article'],
            'assignment': ['assignment', 'essay', 'report', 'paper', 'write'],
            'project': ['project', 'research', 'presentation', 'thesis', 'capstone'],
        }
        
        for task_type, keywords in task_type_keywords.items():
            if any(keyword in description_lower for keyword in keywords):
                task_info['task_type'] = task_type
                break
        
        # Detect subject
        subjects = list(self.DEFAULT_ESTIMATES['subjects'].keys())
        for subject in subjects:
            if subject in description_lower:
                task_info['subject'] = subject
                break
        
        # Detect difficulty indicators
        difficulty_indicators = {
            'easy': 0.7,
            'simple': 0.8,
            'basic': 0.8,
            'hard': 1.4,
            'difficult': 1.4,
            'complex': 1.5,
            'advanced': 1.3,
            'challenging': 1.3,
        }
        
        for indicator, multiplier in difficulty_indicators.items():
            if indicator in description_lower:
                task_info['difficulty_multiplier'] = multiplier
                break
        
        # Extract page/chapter numbers if mentioned
        import re
        
        # More comprehensive patterns for content extraction
        page_patterns = [
            r'(\d+)\s*(?:pages?|страници)',
            r'читај\s+(\d+)\s*страници',
            r'прочитај\s+(\d+)\s*страници',
            r'(\d+)\s*(?:chapters?|поглавја)',
            r'цел\s+(?:роман|книга|дело)',  # whole novel/book
            r'една\s+страница',  # one page
            r'цело\s+поглавје',  # whole chapter
        ]
        
        # Special cases for full works
        if any(word in description_lower for word in ['роман', 'книга', 'novel', 'book', 'цел']):
            if 'страница' in description_lower or 'page' in description_lower:
                task_info['estimated_pages'] = 1  # single page
            else:
                task_info['estimated_pages'] = 200  # assume average novel length
                task_info['is_full_work'] = True
        
        # Extract specific numbers
        for pattern in page_patterns:
            matches = re.findall(pattern, description_lower)
            if matches and matches[0].isdigit():
                task_info['estimated_pages'] = int(matches[0])
                break
        
        # Handle special single page case
        if '1 page' in description_lower or 'една страница' in description_lower:
            task_info['estimated_pages'] = 1
        
        return task_info
    
    def _get_historical_performance(self, task_info: Dict) -> Dict:
        """Analyze student's historical performance for similar tasks"""
        historical_data = {
            'similar_tasks': [],
            'avg_completion_time': None,
            'accuracy_rate': None,
            'task_count': 0,
            'subject_performance': None,
        }
        
        try:
            # Look for similar study sessions
            similar_sessions = StudySession.objects.filter(
                student=self.student
            ).select_related('material')
            
            # Filter by subject if known
            if task_info.get('subject'):
                similar_sessions = similar_sessions.filter(
                    Q(material__subject__icontains=task_info['subject']) |
                    Q(notes__icontains=task_info['subject'])
                )
            
            # Get quiz performance for similar subjects
            quiz_results = QuizResult.objects.filter(
                student=self.student
            ).select_related('quiz')
            
            if task_info.get('subject'):
                quiz_results = quiz_results.filter(
                    quiz__subject__icontains=task_info['subject']
                )
            
            # Calculate average performance metrics
            if quiz_results.exists():
                avg_accuracy = quiz_results.aggregate(
                    avg_accuracy=Avg('accuracy_percentage')
                )['avg_accuracy']
                
                avg_time = quiz_results.exclude(
                    time_taken__isnull=True
                ).aggregate(
                    avg_time=Avg('time_taken')
                )['avg_time']
                
                historical_data['accuracy_rate'] = avg_accuracy
                historical_data['avg_completion_time'] = avg_time
                historical_data['task_count'] = quiz_results.count()
            
            # Get calendar events for time tracking
            calendar_events = CalendarEvent.objects.filter(
                student=self.student,
                event_type='study_session'
            )
            
            if task_info.get('subject'):
                calendar_events = calendar_events.filter(
                    Q(title__icontains=task_info['subject']) |
                    Q(description__icontains=task_info['subject'])
                )
            
            # Analyze study patterns
            study_durations = []
            for event in calendar_events:
                if event.end_time:
                    duration = event.end_time - event.date_time
                    study_durations.append(duration.total_seconds() / 3600)  # Convert to hours
            
            if study_durations:
                historical_data['avg_study_duration'] = sum(study_durations) / len(study_durations)
                historical_data['study_sessions_count'] = len(study_durations)
            
        except Exception as e:
            logger.error(f"Error getting historical performance: {e}")
        
        return historical_data
    
    def _calculate_base_estimate(self, task_info: Dict) -> float:
        """Calculate base time estimate using heuristics"""
        task_type = task_info.get('task_type', 'study')
        subject = task_info.get('subject')
        
        # Get base estimate from defaults
        task_defaults = self.DEFAULT_ESTIMATES['study'].get(task_type, {
            'base': 2.0, 'per_credit': 0.5, 'multiplier': 1.0
        })
        
        base_time = task_defaults['base']
        
        # Adjust for estimated content (pages, chapters, etc.) - this takes priority
        if task_info.get('estimated_pages'):
            pages = task_info['estimated_pages']
            
            if task_type == 'reading':
                # More realistic reading times
                if pages == 1:
                    base_time = 0.083  # 5 minutes for 1 page
                elif pages <= 5:
                    base_time = pages * 0.05  # 3 minutes per page for short readings
                elif pages <= 20:
                    base_time = pages * 0.067  # 4 minutes per page for medium readings
                elif pages <= 50:
                    base_time = pages * 0.083  # 5 minutes per page for longer readings
                elif task_info.get('is_full_work'):  # Full novel/book
                    base_time = pages * 0.1  # 6 minutes per page for novels
                else:
                    base_time = pages * 0.083  # Default 5 minutes per page
            elif task_type in ['homework', 'assignment']:
                base_time = max(base_time, pages * 0.2)  # 12 minutes per page for assignments
        
        # Adjust for subject difficulty
        if subject and subject in self.DEFAULT_ESTIMATES['subjects']:
            subject_multiplier = self.DEFAULT_ESTIMATES['subjects'][subject]
            base_time *= subject_multiplier
        
        # Apply difficulty multiplier
        base_time *= task_info.get('difficulty_multiplier', 1.0)
        
        # Apply task type multiplier (but not for reading if pages were specified)
        if not (task_type == 'reading' and task_info.get('estimated_pages')):
            base_time *= task_defaults['multiplier']
        
        return max(0.083, base_time)  # Minimum 5 minutes
    
    def _apply_historical_adjustment(
        self, base_estimate: float, historical_data: Dict, task_info: Dict
    ) -> float:
        """Adjust estimate based on historical performance"""
        adjusted_estimate = base_estimate
        
        # Adjust based on accuracy rate (lower accuracy = more time needed)
        if historical_data.get('accuracy_rate') is not None:
            accuracy = historical_data['accuracy_rate'] / 100.0
            if accuracy < 0.7:
                adjusted_estimate *= 1.3  # 30% more time if low accuracy
            elif accuracy > 0.9:
                adjusted_estimate *= 0.9  # 10% less time if high accuracy
        
        # Adjust based on historical completion times
        if historical_data.get('avg_study_duration') is not None and historical_data['task_count'] > 2:
            historical_avg = historical_data['avg_study_duration']
            # Weighted average: 70% base estimate, 30% historical data
            adjusted_estimate = (adjusted_estimate * 0.7) + (historical_avg * 0.3)
        
        return adjusted_estimate
    
    def _apply_student_factors(self, estimate: float, task_info: Dict) -> float:
        """Apply student-specific factors to the estimate"""
        adjusted_estimate = estimate
        
        if not self.student_preferences:
            return adjusted_estimate
        
        # Adjust based on study pace preference
        pace = getattr(self.student_preferences, 'study_pace', 'moderate')
        pace_multipliers = {
            'slow': 1.4,
            'moderate': 1.0,
            'fast': 0.8,
            'intensive': 0.7,
        }
        adjusted_estimate *= pace_multipliers.get(pace, 1.0)
        
        # Adjust based on learning style
        learning_style = getattr(self.student_preferences, 'preferred_learning_style', 'reading_writing')
        if task_info.get('task_type') == 'reading':
            if learning_style == 'visual':
                adjusted_estimate *= 0.9  # Visual learners read faster
            elif learning_style == 'auditory':
                adjusted_estimate *= 1.2  # Might need to read aloud
        
        # Adjust based on difficulty preference
        difficulty_pref = getattr(self.student_preferences, 'difficulty_preference', 'adaptive')
        if difficulty_pref == 'easy' and task_info.get('difficulty_multiplier', 1.0) > 1.2:
            adjusted_estimate *= 1.2  # More time for challenging tasks
        
        return adjusted_estimate
    
    def _apply_ai_refinement(self, estimate: float, task_info: Dict) -> float:
        """Apply AI-powered estimation refinement (placeholder for LLaMA integration)"""
        # TODO: Integrate with LLaMA3 for more sophisticated estimation
        # For now, return the estimate as-is
        return estimate
    
    def _generate_estimation_factors(
        self, task_info: Dict, historical_data: Dict, base_estimate: float, final_estimate: float
    ) -> List[str]:
        """Generate list of factors considered in estimation"""
        factors = []
        
        # Task type factor
        task_type_mk = {
            'reading': 'читање',
            'exam': 'испит', 
            'homework': 'домашна задача',
            'assignment': 'задача',
            'project': 'проект',
            'quiz': 'тест'
        }
        task_type = task_info.get('task_type', 'study')
        factors.append(f"Тип на задача: {task_type_mk.get(task_type, task_type)}")
        
        # Content estimation - most important factor
        if task_info.get('estimated_pages'):
            pages = task_info['estimated_pages']
            if task_type == 'reading':
                if pages == 1:
                    factors.append(f"Содржина: {pages} страница (~ 5 мин)")
                else:
                    factors.append(f"Содржина: {pages} страници (~ {pages * 5:.0f} мин)")
            else:
                factors.append(f"Содржина: {pages} страници материјал")
        
        # Subject factor
        if task_info.get('subject'):
            factors.append(f"Предмет: {task_info['subject']}")
        
        # Difficulty factor
        difficulty_mult = task_info.get('difficulty_multiplier', 1.0)
        if difficulty_mult > 1.1:
            factors.append(f"Зголемена сложеност ({difficulty_mult:.1f}x)")
        elif difficulty_mult < 0.9:
            factors.append(f"Намалена сложеност ({difficulty_mult:.1f}x)")
        
        # Historical performance
        if historical_data.get('task_count', 0) > 0:
            factors.append(f"Врз основа на {historical_data['task_count']} слични задачи")
        
        # Base vs final estimate comparison
        if abs(final_estimate - base_estimate) > 0.1:
            factors.append(f"Прилагодено според вашиот профил")
        
        return factors
    
    def _calculate_confidence(self, historical_data: Dict, task_info: Dict) -> float:
        """Calculate confidence level of the estimate (0.0 to 1.0)"""
        confidence = 0.5  # Base confidence
        
        # Increase confidence based on historical data
        task_count = historical_data.get('task_count', 0)
        if task_count > 5:
            confidence += 0.3
        elif task_count > 2:
            confidence += 0.2
        elif task_count > 0:
            confidence += 0.1
        
        # Increase confidence if we have subject-specific data
        if task_info.get('subject') and historical_data.get('accuracy_rate'):
            confidence += 0.1
        
        # Decrease confidence for very new or complex tasks
        if task_info.get('task_type') == 'project':
            confidence *= 0.8
        
        return min(1.0, confidence)
    
    def _generate_reasoning(self, task_info: Dict, factors: List[str], final_estimate: float) -> str:
        """Generate human-readable reasoning for the estimate"""
        task_type = task_info.get('task_type', 'задача')
        subject = task_info.get('subject', '')
        pages = task_info.get('estimated_pages')
        
        # Build detailed reasoning in Macedonian
        reasoning_parts = []
        
        if pages:
            if task_type == 'reading':
                if pages == 1:
                    reasoning_parts.append(f"За читање на 1 страница се потребни околу 5 минути")
                elif pages <= 5:
                    reasoning_parts.append(f"За читање на {pages} страници се потребни {pages * 3:.0f} минути")
                else:
                    reasoning_parts.append(f"За читање на {pages} страници се потребни околу {pages * 5:.0f} минути")
            else:
                reasoning_parts.append(f"Задачата содржи {pages} страници материјал")
        
        if subject:
            reasoning_parts.append(f"Предметот {subject} има специфични барања")
        
        difficulty_mult = task_info.get('difficulty_multiplier', 1.0)
        if difficulty_mult != 1.0:
            if difficulty_mult > 1.2:
                reasoning_parts.append("Зголемена сложеност на задачата")
            elif difficulty_mult < 0.9:
                reasoning_parts.append("Релативно едноставна задача")
        
        if reasoning_parts:
            reasoning = ". ".join(reasoning_parts) + "."
        else:
            reasoning = f"Проценката е направена врз основа на типот на задачата ({task_type})."
        
        return reasoning
    
    def suggest_time_slot(
        self, estimate: TaskEstimate, preferred_time: Optional[str] = None,
        deadline: Optional[datetime] = None
    ) -> Tuple[Optional[datetime], Optional[datetime]]:
        """
        Suggest optimal time slot for the task
        
        Args:
            estimate: TaskEstimate object
            preferred_time: Preferred time of day ('morning', 'afternoon', 'evening')
            deadline: Task deadline
            
        Returns:
            Tuple of (start_time, end_time)
        """
        try:
            # Get student's existing calendar events
            now = timezone.now()
            future_events = CalendarEvent.objects.filter(
                student=self.student,
                date_time__gte=now
            ).order_by('date_time')
            
            # Find available time slots
            search_start = now.replace(hour=8, minute=0, second=0, microsecond=0)
            if search_start < now:
                search_start += timedelta(days=1)
            
            # Search for available slots over the next 7 days
            for day_offset in range(7):
                current_day = search_start + timedelta(days=day_offset)
                
                # Define time preferences
                time_ranges = self._get_preferred_time_ranges(preferred_time, current_day)
                
                for start_hour, end_hour in time_ranges:
                    slot_start = current_day.replace(hour=start_hour, minute=0)
                    slot_end = slot_start + timedelta(hours=estimate.estimated_hours)
                    
                    # Check if deadline allows this slot
                    if deadline and slot_end > deadline:
                        continue
                    
                    # Check for conflicts with existing events
                    conflicts = future_events.filter(
                        date_time__lt=slot_end,
                        end_time__gt=slot_start
                    )
                    
                    if not conflicts.exists():
                        return slot_start, slot_end
            
            # If no slots found, return None
            return None, None
            
        except Exception as e:
            logger.error(f"Error suggesting time slot: {e}")
            return None, None
    
    def _get_preferred_time_ranges(self, preferred_time: Optional[str], day: datetime) -> List[Tuple[int, int]]:
        """Get preferred time ranges based on preference"""
        if preferred_time == 'morning':
            return [(8, 12)]
        elif preferred_time == 'afternoon':
            return [(13, 17)]
        elif preferred_time == 'evening':
            return [(18, 22)]
        else:
            # Default: try morning, then afternoon, then evening
            return [(9, 12), (14, 17), (19, 21)]
    
    def store_actual_completion_time(
        self, task_description: str, actual_hours: float, 
        estimated_hours: float, context: Dict = None
    ):
        """
        Store actual completion time for learning and improvement
        
        Args:
            task_description: Original task description
            actual_hours: Actual time taken
            estimated_hours: Our estimated time
            context: Additional context about the task
        """
        try:
            # Create a chatbot interaction record for learning
            ChatbotInteraction.objects.create(
                student=self.student,
                bot_type='time_agent',
                event_action=f"Task completion: {task_description}",
                message_content=json.dumps({
                    'task_description': task_description,
                    'estimated_hours': estimated_hours,
                    'actual_hours': actual_hours,
                    'accuracy': abs(estimated_hours - actual_hours) / estimated_hours,
                    'context': context or {}
                }),
                response_content=f"Learned from task: estimated {estimated_hours}h, actual {actual_hours}h"
            )
            
            logger.info(
                f"Stored completion data: {task_description} - "
                f"Estimated: {estimated_hours}h, Actual: {actual_hours}h"
            )
            
        except Exception as e:
            logger.error(f"Error storing completion time: {e}")
    
    def get_student_performance_summary(self) -> Dict:
        """Get summary of student's time estimation performance"""
        try:
            # Get time agent interactions
            interactions = ChatbotInteraction.objects.filter(
                student=self.student,
                bot_type='time_agent',
                event_action__startswith='Task completion:'
            )
            
            if not interactions.exists():
                return {
                    'total_tasks': 0,
                    'average_accuracy': None,
                    'improvement_trend': None
                }
            
            accuracies = []
            for interaction in interactions:
                try:
                    data = json.loads(interaction.message_content)
                    accuracy = 1.0 - data.get('accuracy', 0.5)  # Convert error to accuracy
                    accuracies.append(accuracy)
                except (json.JSONDecodeError, KeyError):
                    continue
            
            if not accuracies:
                return {
                    'total_tasks': interactions.count(),
                    'average_accuracy': None,
                    'improvement_trend': None
                }
            
            avg_accuracy = sum(accuracies) / len(accuracies)
            
            # Calculate improvement trend (compare first half to second half)
            improvement_trend = None
            if len(accuracies) >= 4:
                mid_point = len(accuracies) // 2
                first_half_avg = sum(accuracies[:mid_point]) / mid_point
                second_half_avg = sum(accuracies[mid_point:]) / (len(accuracies) - mid_point)
                improvement_trend = second_half_avg - first_half_avg
            
            return {
                'total_tasks': len(accuracies),
                'average_accuracy': avg_accuracy,
                'improvement_trend': improvement_trend
            }
            
        except Exception as e:
            logger.error(f"Error getting performance summary: {e}")
            return {
                'total_tasks': 0,
                'average_accuracy': None,
                'improvement_trend': None
            }