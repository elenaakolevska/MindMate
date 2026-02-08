#!/usr/bin/env python
"""
Backfill badges for existing users who had activities before the badge system was implemented.
Run this script to award badges based on past activities.
"""

import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'MindMate.settings')
django.setup()

from MindMateAPP.models import Student, QuizResult, StudyMaterial, Badge
from MindMateAPP.utils import (
    award_badge, 
    check_quiz_badges, 
    check_document_badges, 
    check_accuracy_badges,
    check_engagement_badges
)
from django.contrib.auth.models import User


def backfill_badges_for_all_users():
    """Backfill badges for all existing users"""
    
    print("🔄 Backfilling badges for existing users...")
    print("=" * 60)
    
    students = Student.objects.all()
    
    for student in students:
        print(f"\n👤 Processing {student.full_name}...")
        
        # Get current counts
        quiz_count = QuizResult.objects.filter(student=student).count()
        doc_count = StudyMaterial.objects.filter(student=student).count()
        current_badge_count = Badge.objects.filter(student=student).count()
        
        print(f"   Current status: {quiz_count} quizzes, {doc_count} docs, {current_badge_count} badges")
        
        # Award welcome badge if they don't have it
        if current_badge_count == 0:
            award_badge(
                student, 
                "Welcome to MindMate", 
                "Congratulations on joining MindMate! Start your learning journey!"
            )
        
        # Check for quiz-based badges
        if quiz_count > 0:
            check_quiz_badges(student)
            check_accuracy_badges(student)
        
        # Check for document-based badges
        if doc_count > 0:
            check_document_badges(student)
        
        # Check for engagement badges
        check_engagement_badges(student)
        
        # Show new badge count
        new_badge_count = Badge.objects.filter(student=student).count()
        badges_added = new_badge_count - current_badge_count
        
        if badges_added > 0:
            print(f"   ✅ Awarded {badges_added} new badges!")
            
            # Show the new badges
            new_badges = Badge.objects.filter(student=student).order_by('-received_at')[:badges_added]
            for badge in new_badges:
                print(f"      🏆 {badge.badge_name}: {badge.description}")
        else:
            print(f"   ℹ️ No new badges awarded")
    
    print(f"\n🎉 Backfill process completed!")


def backfill_badges_for_user(username):
    """Backfill badges for a specific user"""
    
    try:
        user = User.objects.get(username=username)
        student = Student.objects.get(user=user)
        
        print(f"🔄 Backfilling badges for {student.full_name}...")
        print("=" * 50)
        
        # Get current counts
        quiz_count = QuizResult.objects.filter(student=student).count()
        doc_count = StudyMaterial.objects.filter(student=student).count()
        current_badge_count = Badge.objects.filter(student=student).count()
        
        print(f"Current status:")
        print(f"  - Quizzes completed: {quiz_count}")
        print(f"  - Documents uploaded: {doc_count}")
        print(f"  - Current badges: {current_badge_count}")
        
        # Award welcome badge if they don't have it
        if current_badge_count == 0:
            award_badge(
                student, 
                "Welcome to MindMate", 
                "Congratulations on joining MindMate! Start your learning journey!"
            )
        
        # Check for quiz-based badges
        if quiz_count > 0:
            check_quiz_badges(student)
            check_accuracy_badges(student)
        
        # Check for document-based badges  
        if doc_count > 0:
            check_document_badges(student)
        
        # Check for engagement badges
        check_engagement_badges(student)
        
        # Show results
        new_badge_count = Badge.objects.filter(student=student).count()
        badges_added = new_badge_count - current_badge_count
        
        print(f"\n📊 Results:")
        print(f"  - Badges before: {current_badge_count}")
        print(f"  - Badges after: {new_badge_count}")
        print(f"  - New badges awarded: {badges_added}")
        
        if badges_added > 0:
            print(f"\n🏆 New badges earned:")
            new_badges = Badge.objects.filter(student=student).order_by('-received_at')[:badges_added]
            for badge in new_badges:
                print(f"    - {badge.badge_name}: {badge.description}")
        
        return badges_added
        
    except (User.DoesNotExist, Student.DoesNotExist):
        print(f"❌ User '{username}' not found")
        return 0


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # Backfill for specific user
        username = sys.argv[1]
        backfill_badges_for_user(username)
    else:
        # Backfill for all users
        backfill_badges_for_all_users()