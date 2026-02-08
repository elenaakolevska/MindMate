# MindMateAPP/utils.py
from django.utils import timezone
from datetime import timedelta
from .models import Student, Progress, Streak, Badge, QuizResult, StudyMaterial
import logging

logger = logging.getLogger(__name__)


def update_student_streak(student):
    """Update student's daily streak based on activity"""
    try:
        # Get or create progress and streak objects
        progress, _ = Progress.objects.get_or_create(
            student=student,
            defaults={'progress_bar': 0.0, 'completed_tasks': 0}
        )
        
        streak, created = Streak.objects.get_or_create(
            progress=progress,
            defaults={'days_count': 0, 'last_day': timezone.now().date() - timedelta(days=1)}
        )
        
        today = timezone.now().date()
        yesterday = today - timedelta(days=1)
        
        # Check if we need to update the streak
        if streak.last_day == today:
            # Already updated today, no change needed
            return streak.days_count
            
        elif streak.last_day == yesterday:
            # Continuing streak from yesterday
            streak.days_count += 1
            streak.last_day = today
            streak.save()
            
            # Award streak badges if applicable
            award_streak_badge(student, streak.days_count)
            
        elif created or streak.last_day < yesterday:
            # First time or streak was broken, start new streak
            streak.days_count = 1  # Start new streak with 1 day
            streak.last_day = today
            streak.save()
            
            # Award streak badges if applicable
            award_streak_badge(student, streak.days_count)
            
        return streak.days_count
        
    except Exception as e:
        logger.error(f"Error updating streak for student {student.id}: {e}")
        return 0


def award_badge(student, badge_name, description=""):
    """Award a badge to a student if they don't already have it"""
    try:
        # Check if student already has this badge
        existing_badge = Badge.objects.filter(
            student=student, 
            badge_name=badge_name
        ).first()
        
        if not existing_badge:
            Badge.objects.create(
                student=student,
                badge_name=badge_name,
                description=description,
                received_at=timezone.now().date()
            )
            logger.info(f"Awarded badge '{badge_name}' to student {student.id}")
            return True
        return False
        
    except Exception as e:
        logger.error(f"Error awarding badge {badge_name} to student {student.id}: {e}")
        return False


def award_streak_badge(student, streak_days):
    """Award badges for streak milestones"""
    streak_milestones = {
        3: ("3-Day Streak", "Maintained learning for 3 consecutive days!"),
        7: ("Week Warrior", "Completed 7 days in a row - excellent dedication!"),
        14: ("Two Week Champion", "14 consecutive days of learning!"),
        30: ("Monthly Master", "Amazing! 30 days of continuous learning!"),
        60: ("Learning Legend", "60 days straight - you're a learning legend!"),
        100: ("Centurion", "100 days of dedication - truly exceptional!")
    }
    
    if streak_days in streak_milestones:
        badge_name, description = streak_milestones[streak_days]
        award_badge(student, badge_name, description)


def check_quiz_badges(student):
    """Check and award quiz-related badges"""
    quiz_count = QuizResult.objects.filter(student=student).count()
    
    quiz_milestones = {
        1: ("First Steps", "Completed your first quiz!"),
        5: ("Quiz Explorer", "Completed 5 quizzes - keep it up!"),
        10: ("Quiz Master", "Reached 10 completed quizzes!"),
        25: ("Quiz Champion", "25 quizzes completed - impressive!"),
        50: ("Quiz Legend", "50 quizzes completed - you're unstoppable!"),
        100: ("Quiz God", "100 quizzes! You've mastered the art of learning!")
    }
    
    # Award all milestones the user has reached
    for milestone, (badge_name, description) in quiz_milestones.items():
        if quiz_count >= milestone:
            award_badge(student, badge_name, description)


def check_document_badges(student):
    """Check and award document upload badges"""
    doc_count = StudyMaterial.objects.filter(student=student).count()
    
    doc_milestones = {
        1: ("First Upload", "Uploaded your first study material!"),
        5: ("Document Organizer", "5 documents uploaded - staying organized!"),
        10: ("Study Collector", "10 documents uploaded - building your library!"),
        25: ("Knowledge Curator", "25 documents - you're a knowledge curator!"),
        50: ("Study Archive", "50 documents - impressive study archive!")
    }
    
    # Award all milestones the user has reached
    for milestone, (badge_name, description) in doc_milestones.items():
        if doc_count >= milestone:
            award_badge(student, badge_name, description)


def check_accuracy_badges(student):
    """Check and award badges based on quiz accuracy"""
    try:
        recent_results = QuizResult.objects.filter(student=student).order_by('-taken_at')[:10]
        
        if recent_results.count() >= 5:
            avg_accuracy = sum(result.accuracy_percentage for result in recent_results[:5]) / 5
            
            accuracy_milestones = {
                90: ("Precision Expert", "90%+ average accuracy on recent quizzes!"),
                95: ("Accuracy Master", "95%+ average accuracy - exceptional!"),
                98: ("Perfection Seeker", "98%+ accuracy - nearly perfect!")
            }
            
            for threshold, (badge_name, description) in accuracy_milestones.items():
                if avg_accuracy >= threshold:
                    award_badge(student, badge_name, description)
                    
    except Exception as e:
        logger.error(f"Error checking accuracy badges for student {student.id}: {e}")


def update_student_activity(student, activity_type="general"):
    """
    Update student streak and check for badges when they perform activities.
    
    Args:
        student: Student instance
        activity_type: Type of activity ("quiz", "upload", "study", "general")
    """
    # Update streak
    streak_days = update_student_streak(student)
    
    # Check for different types of badges based on activity
    if activity_type == "quiz":
        check_quiz_badges(student)
        check_accuracy_badges(student)
    elif activity_type == "upload":
        check_document_badges(student)
    
    # Always check for general engagement badges
    check_engagement_badges(student)
    
    return streak_days


def check_engagement_badges(student):
    """Award badges for overall engagement"""
    try:
        # Get total activities
        quiz_count = QuizResult.objects.filter(student=student).count()
        doc_count = StudyMaterial.objects.filter(student=student).count()
        
        total_activities = quiz_count + doc_count
        
        engagement_milestones = {
            10: ("Active Learner", "Completed 10 learning activities!"),
            25: ("Engaged Student", "25 activities completed - you're engaged!"),
            50: ("Super Student", "50 activities - you're a super student!"),
            100: ("Learning Machine", "100 activities - you're a learning machine!")
        }
        
        # Award all milestones the user has reached
        for milestone, (badge_name, description) in engagement_milestones.items():
            if total_activities >= milestone:
                award_badge(student, badge_name, description)
            
    except Exception as e:
        logger.error(f"Error checking engagement badges for student {student.id}: {e}")