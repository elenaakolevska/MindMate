#!/usr/bin/env python
"""
Test script for the new streak and badge functionality.
Run this in the Django shell to test various scenarios.
"""

import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'MindMate.settings')
django.setup()

from MindMateAPP.models import Student, QuizResult, Quiz, StudyMaterial
from MindMateAPP.utils import (
    update_student_activity, 
    award_badge, 
    check_quiz_badges,
    check_document_badges,
    update_student_streak
)
from django.contrib.auth.models import User


def test_streak_and_badges():
    """Test the streak and badge functionality"""
    
    print("🧪 Testing Streak and Badge System")
    print("=" * 50)
    
    # Get or create a test user
    try:
        user = User.objects.get(username='test_api_user')
        student = Student.objects.get(user=user)
        print(f"✅ Using existing student: {student.full_name}")
    except (User.DoesNotExist, Student.DoesNotExist):
        print("❌ No test student found. Please create a student account first.")
        return
    
    print(f"\n📊 Current Status:")
    print(f"   - Quizzes completed: {QuizResult.objects.filter(student=student).count()}")
    print(f"   - Documents uploaded: {StudyMaterial.objects.filter(student=student).count()}")
    
    # Test streak update
    print(f"\n🔥 Testing Streak Updates...")
    streak_days = update_student_streak(student)
    print(f"   Current streak: {streak_days} days")
    
    # Test badge awarding
    print(f"\n🏆 Testing Badge Awards...")
    badge_awarded = award_badge(student, "Test Badge", "This is a test badge")
    if badge_awarded:
        print("   ✅ Test badge awarded successfully!")
    else:
        print("   ℹ️ Test badge already exists or failed to award")
    
    # Test quiz badges
    print(f"\n🎯 Checking Quiz Badges...")
    check_quiz_badges(student)
    
    # Test document badges
    print(f"\n📄 Checking Document Badges...")
    check_document_badges(student)
    
    # Test activity update (simulating quiz completion)
    print(f"\n⚡ Testing Activity Update (simulating quiz)...")
    new_streak = update_student_activity(student, activity_type="quiz")
    print(f"   New streak after activity: {new_streak} days")
    
    # Show final badge count
    from MindMateAPP.models import Badge
    badge_count = Badge.objects.filter(student=student).count()
    print(f"\n🎊 Final Results:")
    print(f"   Total badges earned: {badge_count}")
    
    if badge_count > 0:
        print(f"   Recent badges:")
        recent_badges = Badge.objects.filter(student=student).order_by('-received_at')[:3]
        for badge in recent_badges:
            print(f"     - {badge.badge_name}: {badge.description}")
    
    print(f"\n✅ Test completed!")


if __name__ == "__main__":
    test_streak_and_badges()