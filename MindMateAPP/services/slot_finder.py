"""
Time Agent Slot Finder Service

This service finds available time slots in a student's calendar for scheduling study sessions.
It considers:
- Existing calendar events and conflicts
- Time constraints (no slots after 10pm, minimum 30min duration)
- Student preferences (daily study hours, learning style)
- Subject difficulty prioritization (morning for hard subjects/exams)
"""

import logging
from datetime import datetime, timedelta, time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from django.utils import timezone
from django.db.models import Q

from ..models import CalendarEvent, Student, StudentPreferences

logger = logging.getLogger(__name__)


@dataclass
class TimeSlot:
    """Data class for available time slots"""
    start_time: datetime
    end_time: datetime
    duration_hours: float
    quality_score: float  # 0.0 to 1.0 rating based on optimality
    reasons: List[str]  # Why this slot was suggested
    is_split: bool = False  # Whether this is part of a larger task split
    original_duration: Optional[float] = None  # Original requested duration if split


@dataclass
class SlotRequest:
    """Data class for slot finding requests"""
    duration_hours: float
    subject: Optional[str] = None
    difficulty: str = 'moderate'  # easy, moderate, hard, very_hard
    task_type: str = 'study'  # study, exam, homework, etc.
    deadline: Optional[datetime] = None
    preferred_times: Optional[List[str]] = None  # morning, afternoon, evening
    allow_splitting: bool = True
    min_session_duration: float = 0.5  # Minimum 30 minutes


class SlotFinder:
    """
    Service for finding optimal time slots for study sessions
    """
    
    # Time constraints
    MIN_SESSION_DURATION = 0.5  # 30 minutes minimum
    MAX_SESSION_DURATION = 6.0  # 6 hours maximum per session
    DAY_START_HOUR = 6  # 6 AM
    DAY_END_HOUR = 22  # 10 PM (no slots after this)
    OPTIMAL_DAY_END_HOUR = 21  # 9 PM for better quality scores
    
    # Quality scoring weights
    TIME_OF_DAY_WEIGHTS = {
        'morning': {'easy': 0.7, 'moderate': 0.9, 'hard': 1.0, 'very_hard': 1.0, 'challenging': 1.0},
        'afternoon': {'easy': 1.0, 'moderate': 0.8, 'hard': 0.8, 'very_hard': 0.7, 'challenging': 0.8},
        'evening': {'easy': 0.9, 'moderate': 0.6, 'hard': 0.6, 'very_hard': 0.5, 'challenging': 0.6},
        'night': {'easy': 0.6, 'moderate': 0.4, 'hard': 0.3, 'very_hard': 0.2, 'challenging': 0.3}
    }
    
    def __init__(self, student: Student):
        self.student = student
        self.student_preferences = getattr(student, 'preferences', None)
        
    def find_slots(self, request: SlotRequest, max_suggestions: int = 3) -> List[TimeSlot]:
        """
        Find optimal time slots for the given request
        
        Args:
            request: SlotRequest with duration, subject, difficulty, etc.
            max_suggestions: Maximum number of slots to return
            
        Returns:
            List of TimeSlot objects, sorted by quality score (best first)
        """
        try:
            # Get existing calendar events
            existing_events = self._get_existing_events(request.deadline)
            
            # Generate candidate slots
            candidate_slots = self._generate_candidate_slots(request, existing_events)
            
            # Filter by constraints
            valid_slots = self._apply_constraints(candidate_slots, request)
            
            # Score and rank slots
            scored_slots = self._score_slots(valid_slots, request)
            
            # Handle splitting if no single slots found and splitting is allowed
            if len(scored_slots) < max_suggestions and request.allow_splitting:
                split_slots = self._find_split_slots(request, existing_events)
                scored_slots.extend(split_slots)
                # Re-sort after adding split slots
                scored_slots.sort(key=lambda x: x.quality_score, reverse=True)
            
            # Return top suggestions
            return scored_slots[:max_suggestions]
            
        except Exception as e:
            logger.error(f"Error finding slots: {e}")
            return []
    
    def _get_existing_events(self, deadline: Optional[datetime] = None) -> List[CalendarEvent]:
        """Get student's existing calendar events"""
        try:
            now = timezone.now()
            end_date = deadline or (now + timedelta(days=14))  # Look 2 weeks ahead by default
            
            return list(CalendarEvent.objects.filter(
                student=self.student,
                date_time__gte=now,
                date_time__lte=end_date
            ).order_by('date_time'))
            
        except Exception as e:
            logger.error(f"Error getting existing events: {e}")
            return []
    
    def _generate_candidate_slots(self, request: SlotRequest, existing_events: List[CalendarEvent]) -> List[TimeSlot]:
        """Generate potential time slots between existing events"""
        candidate_slots = []
        
        # Start from tomorrow (or today if early enough)
        now = timezone.now()
        start_date = now.replace(hour=self.DAY_START_HOUR, minute=0, second=0, microsecond=0)
        if start_date <= now:
            start_date += timedelta(days=1)
        
        # Search period (up to deadline or 14 days)
        search_end = request.deadline or (now + timedelta(days=14))
        
        current_date = start_date.date()
        while datetime.combine(current_date, time.min).replace(tzinfo=start_date.tzinfo) <= search_end:
            # Get events for this day
            day_events = [
                event for event in existing_events
                if event.date_time.date() == current_date
            ]
            
            # Find gaps in the day
            day_slots = self._find_day_gaps(current_date, day_events, request.duration_hours)
            candidate_slots.extend(day_slots)
            
            current_date += timedelta(days=1)
        
        return candidate_slots
    
    def _find_day_gaps(self, date: datetime.date, events: List[CalendarEvent], duration: float) -> List[TimeSlot]:
        """Find available gaps within a single day"""
        slots = []
        
        # Create time boundaries for the day
        day_start = datetime.combine(date, time(self.DAY_START_HOUR, 0)).replace(
            tzinfo=timezone.get_current_timezone()
        )
        day_end = datetime.combine(date, time(self.DAY_END_HOUR, 0)).replace(
            tzinfo=timezone.get_current_timezone()
        )
        
        # Sort events by start time
        events = sorted(events, key=lambda x: x.date_time)
        
        # Add day boundaries as "events" to simplify logic
        boundaries = [
            type('Event', (), {
                'date_time': day_start - timedelta(hours=1),
                'end_time': day_start
            })(),
            *events,
            type('Event', (), {
                'date_time': day_end,
                'end_time': day_end + timedelta(hours=1)
            })()
        ]
        
        # Find gaps between consecutive events
        for i in range(len(boundaries) - 1):
            gap_start = boundaries[i].end_time or (boundaries[i].date_time + timedelta(hours=1))
            gap_end = boundaries[i + 1].date_time
            
            # Ensure gap is within day bounds
            gap_start = max(gap_start, day_start)
            gap_end = min(gap_end, day_end)
            
            if gap_start < gap_end:
                gap_duration = (gap_end - gap_start).total_seconds() / 3600.0
                
                # If gap is large enough, create slots
                if gap_duration >= self.MIN_SESSION_DURATION:
                    # Try to fit the requested duration
                    if gap_duration >= duration:
                        slot_end = gap_start + timedelta(hours=duration)
                        slots.append(TimeSlot(
                            start_time=gap_start,
                            end_time=slot_end,
                            duration_hours=duration,
                            quality_score=0.0,  # Will be calculated later
                            reasons=[]
                        ))
                    
                    # Also consider partial slots if shorter than requested
                    elif gap_duration >= self.MIN_SESSION_DURATION:
                        slots.append(TimeSlot(
                            start_time=gap_start,
                            end_time=gap_end,
                            duration_hours=gap_duration,
                            quality_score=0.0,  # Will be calculated later
                            reasons=[]
                        ))
        
        return slots
    
    def _apply_constraints(self, slots: List[TimeSlot], request: SlotRequest) -> List[TimeSlot]:
        """Apply time and preference constraints"""
        valid_slots = []
        
        for slot in slots:
            # Check minimum duration
            if slot.duration_hours < request.min_session_duration:
                continue
            
            # Check maximum session duration
            if slot.duration_hours > self.MAX_SESSION_DURATION:
                # Adjust to max duration
                slot.end_time = slot.start_time + timedelta(hours=self.MAX_SESSION_DURATION)
                slot.duration_hours = self.MAX_SESSION_DURATION
            
            # Check daily study hours limit
            if self._exceeds_daily_study_limit(slot):
                continue
            
            # Check time preferences
            if request.preferred_times and not self._matches_preferred_time(slot, request.preferred_times):
                continue
            
            valid_slots.append(slot)
        
        return valid_slots
    
    def _exceeds_daily_study_limit(self, slot: TimeSlot) -> bool:
        """Check if adding this slot would exceed daily study hours limit"""
        if not self.student_preferences:
            return False
        
        daily_limit = getattr(self.student_preferences, 'daily_study_hours', 8.0)
        
        # Get existing study sessions for the same day
        slot_date = slot.start_time.date()
        existing_study_time = 0.0
        
        try:
            day_events = CalendarEvent.objects.filter(
                student=self.student,
                date_time__date=slot_date,
                event_type='study_session'
            )
            
            for event in day_events:
                if event.end_time:
                    duration = (event.end_time - event.date_time).total_seconds() / 3600.0
                    existing_study_time += duration
                else:
                    existing_study_time += 1.0  # Assume 1 hour if no end time
            
        except Exception as e:
            logger.error(f"Error checking daily study limit: {e}")
            return False
        
        return (existing_study_time + slot.duration_hours) > daily_limit
    
    def _matches_preferred_time(self, slot: TimeSlot, preferred_times: List[str]) -> bool:
        """Check if slot matches preferred times of day"""
        slot_hour = slot.start_time.hour
        
        time_periods = {
            'morning': (6, 12),
            'afternoon': (12, 17),
            'evening': (17, 22),
            'night': (22, 24)  # Generally not preferred
        }
        
        slot_periods = []
        for period, (start, end) in time_periods.items():
            if start <= slot_hour < end:
                slot_periods.append(period)
        
        return any(period in preferred_times for period in slot_periods)
    
    def _score_slots(self, slots: List[TimeSlot], request: SlotRequest) -> List[TimeSlot]:
        """Score slots based on various factors and sort by quality"""
        
        for slot in slots:
            score = 0.0
            reasons = []
            
            # Time of day scoring (most important factor)
            time_score = self._calculate_time_of_day_score(slot, request.difficulty)
            score += time_score * 0.4  # 40% weight
            
            # Duration matching scoring
            duration_score = self._calculate_duration_score(slot, request.duration_hours)
            score += duration_score * 0.25  # 25% weight
            
            # Proximity to deadline scoring
            if request.deadline:
                deadline_score = self._calculate_deadline_score(slot, request.deadline)
                score += deadline_score * 0.2  # 20% weight
            else:
                score += 0.8 * 0.2  # Default score if no deadline
            
            # Day of week scoring (weekdays slightly better for hard subjects)
            weekday_score = self._calculate_weekday_score(slot, request.difficulty)
            score += weekday_score * 0.1  # 10% weight
            
            # Continuity scoring (prefer slots not broken by short breaks)
            continuity_score = self._calculate_continuity_score(slot)
            score += continuity_score * 0.05  # 5% weight
            
            slot.quality_score = min(1.0, score)  # Cap at 1.0
            slot.reasons = self._generate_slot_reasons(slot, request, time_score, duration_score)
        
        # Sort by quality score (best first)
        return sorted(slots, key=lambda x: x.quality_score, reverse=True)
    
    def _calculate_time_of_day_score(self, slot: TimeSlot, difficulty: str) -> float:
        """Calculate score based on time of day and task difficulty"""
        hour = slot.start_time.hour
        
        # Determine time period
        if 6 <= hour < 12:
            period = 'morning'
        elif 12 <= hour < 17:
            period = 'afternoon'
        elif 17 <= hour < 21:
            period = 'evening'
        else:
            period = 'night'
        
        # Get base score from weights
        base_score = self.TIME_OF_DAY_WEIGHTS[period].get(difficulty, 0.5)
        
        # Apply fine-grained adjustments
        if period == 'morning':
            # Peak morning hours (8-10 AM) are best for hard/moderate tasks
            if difficulty in ['hard', 'very_hard', 'challenging', 'moderate'] and 8 <= hour <= 10:
                base_score = min(1.0, base_score + 0.1)
        elif period == 'evening':
            # Later evening gets progressively worse
            if hour >= 20:
                base_score *= 0.8
        elif period == 'night':
            # Night hours are generally poor
            base_score *= 0.5
        
        return base_score
    
    def _calculate_duration_score(self, slot: TimeSlot, requested_duration: float) -> float:
        """Score based on how well slot duration matches request"""
        if slot.duration_hours >= requested_duration:
            return 1.0  # Perfect match or better
        else:
            # Partial match - score based on percentage
            return slot.duration_hours / requested_duration
    
    def _calculate_deadline_score(self, slot: TimeSlot, deadline: datetime) -> float:
        """Score based on proximity to deadline"""
        time_until_deadline = (deadline - slot.end_time).total_seconds() / 3600.0  # Hours
        
        if time_until_deadline < 0:
            return 0.0  # Past deadline
        elif time_until_deadline < 2:
            return 0.3  # Very tight deadline
        elif time_until_deadline < 12:
            return 0.6  # Tight deadline
        elif time_until_deadline < 48:
            return 1.0  # Good timing
        else:
            return 0.8  # Plenty of time, but not urgent
    
    def _calculate_weekday_score(self, slot: TimeSlot, difficulty: str) -> float:
        """Score based on day of week"""
        weekday = slot.start_time.weekday()  # 0=Monday, 6=Sunday
        
        if difficulty in ['hard', 'very_hard', 'challenging', 'moderate']:
            # Prefer weekdays for hard/moderate tasks  
            if weekday < 5:  # Monday-Friday
                return 1.0
            else:
                return 0.7
        else:
            # Easy/moderate tasks work well any day
            if weekday < 5:
                return 0.9
            else:
                return 1.0  # Weekends can be good for easier tasks
    
    def _calculate_continuity_score(self, slot: TimeSlot) -> float:
        """Score based on slot continuity (prefer uninterrupted time)"""
        # This is a simplified scoring - in real implementation you might
        # check for short breaks that interrupt focus
        if slot.duration_hours >= 2.0:
            return 1.0  # Good long block
        elif slot.duration_hours >= 1.0:
            return 0.8  # Decent block
        else:
            return 0.6  # Short block
    
    def _generate_slot_reasons(self, slot: TimeSlot, request: SlotRequest, 
                             time_score: float, duration_score: float) -> List[str]:
        """Generate human-readable reasons for why this slot was suggested"""
        reasons = []
        
        hour = slot.start_time.hour
        difficulty = request.difficulty
        
        # Time-based reasons
        if 8 <= hour <= 10 and difficulty in ['hard', 'very_hard']:
            reasons.append("Оптимално утринско време за тешки задачи")
        elif 6 <= hour < 12:
            reasons.append("Добро утринско време за учење")
        elif 12 <= hour < 17:
            reasons.append("Продуктивно попладневно време")
        elif 17 <= hour < 20:
            reasons.append("Вечерно време за учење")
        
        # Duration reasons
        if duration_score >= 1.0:
            if slot.duration_hours > request.duration_hours:
                reasons.append("Доволно време со резерва")
            else:
                reasons.append("Совршено време за задачата")
        else:
            reasons.append("Делумно време - можна поделба")
        
        # Deadline reasons
        if request.deadline:
            time_until = (request.deadline - slot.end_time).total_seconds() / 3600.0
            if time_until < 12:
                reasons.append("Блиску до крајниот рок")
            elif time_until < 48:
                reasons.append("Добра временска рамка")
        
        # Weekend/weekday
        if slot.start_time.weekday() >= 5:  # Weekend
            reasons.append("Викенд - повеќе време за фокус")
        
        return reasons[:3]  # Limit to top 3 reasons
    
    def _find_split_slots(self, request: SlotRequest, existing_events: List[CalendarEvent]) -> List[TimeSlot]:
        """Find multiple smaller slots that together satisfy the duration requirement"""
        if request.duration_hours <= self.MAX_SESSION_DURATION:
            return []  # No need to split
        
        # Calculate how many sessions needed
        sessions_needed = int((request.duration_hours + self.MAX_SESSION_DURATION - 0.1) / self.MAX_SESSION_DURATION)
        session_duration = request.duration_hours / sessions_needed
        
        # Ensure minimum session duration
        if session_duration < request.min_session_duration:
            sessions_needed = int(request.duration_hours / request.min_session_duration)
            session_duration = request.duration_hours / sessions_needed
        
        # Create modified request for shorter sessions
        split_request = SlotRequest(
            duration_hours=session_duration,
            subject=request.subject,
            difficulty=request.difficulty,
            task_type=request.task_type,
            deadline=request.deadline,
            preferred_times=request.preferred_times,
            allow_splitting=False,  # Prevent recursive splitting
            min_session_duration=request.min_session_duration
        )
        
        # Find slots for each session
        split_slots = []
        temp_events = existing_events.copy()
        
        for session_num in range(sessions_needed):
            # Find candidates for this session
            candidates = self._generate_candidate_slots(split_request, temp_events)
            valid_candidates = self._apply_constraints(candidates, split_request)
            
            if not valid_candidates:
                break  # Can't find enough slots
            
            # Score and pick the best
            scored_candidates = self._score_slots(valid_candidates, split_request)
            if scored_candidates:
                best_slot = scored_candidates[0]
                
                # Mark as split and add to results
                best_slot.is_split = True
                best_slot.original_duration = request.duration_hours
                best_slot.reasons.append(f"Сесија {session_num + 1} од {sessions_needed}")
                
                # Reduce quality score for split sessions
                best_slot.quality_score *= 0.8
                
                split_slots.append(best_slot)
                
                # Add this slot as a temporary event to avoid overlaps
                temp_events.append(type('TempEvent', (), {
                    'date_time': best_slot.start_time,
                    'end_time': best_slot.end_time,
                    'student': self.student
                })())
        
        # Only return if we found all needed sessions
        if len(split_slots) == sessions_needed:
            return split_slots
        else:
            return []
    
    def get_daily_availability_summary(self, date: datetime.date) -> Dict:
        """Get a summary of availability for a specific date"""
        try:
            # Get events for the date
            events = CalendarEvent.objects.filter(
                student=self.student,
                date_time__date=date
            ).order_by('date_time')
            
            # Calculate total free time
            day_start = datetime.combine(date, time(self.DAY_START_HOUR, 0)).replace(
                tzinfo=timezone.get_current_timezone()
            )
            day_end = datetime.combine(date, time(self.DAY_END_HOUR, 0)).replace(
                tzinfo=timezone.get_current_timezone()
            )
            
            total_day_hours = (day_end - day_start).total_seconds() / 3600.0
            busy_hours = 0.0
            
            for event in events:
                event_end = event.end_time or (event.date_time + timedelta(hours=1))
                event_start = max(event.date_time, day_start)
                event_end = min(event_end, day_end)
                
                if event_start < event_end:
                    busy_hours += (event_end - event_start).total_seconds() / 3600.0
            
            free_hours = total_day_hours - busy_hours
            
            return {
                'date': date.isoformat(),
                'total_hours': total_day_hours,
                'busy_hours': busy_hours,
                'free_hours': free_hours,
                'availability_percentage': (free_hours / total_day_hours) * 100 if total_day_hours > 0 else 0,
                'events_count': events.count()
            }
            
        except Exception as e:
            logger.error(f"Error getting daily availability: {e}")
            return {
                'date': date.isoformat(),
                'total_hours': 0,
                'busy_hours': 0,
                'free_hours': 0,
                'availability_percentage': 0,
                'events_count': 0
            }