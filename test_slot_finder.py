#!/usr/bin/env python
"""
Test script for Slot Finder functionality
"""

import os
import sys
import django
from datetime import datetime, timedelta

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'MindMate.settings')
django.setup()

from MindMateAPP.services.slot_finder import SlotFinder, SlotRequest
from MindMateAPP.models import Student, CalendarEvent, StudentPreferences
from django.utils import timezone


def test_slot_finder_integration():
    """Test the SlotFinder service integration with Django models"""
    
    print("🧪 Testing Slot Finder Integration")
    print("=" * 50)
    
    try:
        # Create or get a test student
        student, created = Student.objects.get_or_create(
            email='test_slot_finder@example.com',
            defaults={
                'full_name': 'Test Student for Slot Finder',
                'study_level': 'college',
                'study_direction': 'Computer Science'
            }
        )
        
        if created:
            print(f"✅ Created test student: {student.full_name}")
            
            # Create student preferences
            StudentPreferences.objects.get_or_create(
                student=student,
                defaults={
                    'daily_study_hours': 6.0,
                    'preferred_learning_style': 'visual',
                    'difficulty_preference': 'adaptive'
                }
            )
            print("✅ Created student preferences")
        else:
            print(f"✅ Using existing student: {student.full_name}")
        
        # Clear existing calendar events for clean test
        CalendarEvent.objects.filter(student=student).delete()
        
        # Test 1: Empty calendar scenario
        print("\n1️⃣ Testing empty calendar...")
        
        slot_finder = SlotFinder(student)
        request = SlotRequest(
            duration_hours=2.0,
            subject='mathematics',
            difficulty='hard',
            task_type='exam',
            preferred_times=['morning']
        )
        
        slots = slot_finder.find_slots(request)
        
        print(f"Found {len(slots)} slots for 2-hour hard math exam:")
        for i, slot in enumerate(slots, 1):
            start_str = slot.start_time.strftime('%A %B %d at %I:%M %p')
            end_str = slot.end_time.strftime('%I:%M %p')
            reasons = ', '.join(slot.reasons)
            print(f"  {i}. {start_str} - {end_str} ({slot.duration_hours}h)")
            print(f"     Quality: {slot.quality_score:.2f} | {reasons}")
        
        # Test 2: Busy calendar scenario
        print("\n2️⃣ Testing busy calendar...")
        
        # Add some conflicting events
        now = timezone.now().replace(hour=8, minute=0, second=0, microsecond=0)
        tomorrow = now + timedelta(days=1)
        
        # Morning meeting
        CalendarEvent.objects.create(
            student=student,
            title="Morning Meeting",
            date_time=tomorrow.replace(hour=9),
            end_time=tomorrow.replace(hour=11),
            event_type='personal'
        )
        
        # Afternoon class
        CalendarEvent.objects.create(
            student=student,
            title="Afternoon Class", 
            date_time=tomorrow.replace(hour=14),
            end_time=tomorrow.replace(hour=16),
            event_type='personal'
        )
        
        print("Added conflicting events: 9-11 AM meeting, 2-4 PM class")
        
        busy_slots = slot_finder.find_slots(request)
        
        print(f"Found {len(busy_slots)} slots with busy calendar:")
        for i, slot in enumerate(busy_slots, 1):
            start_str = slot.start_time.strftime('%A %B %d at %I:%M %p')
            end_str = slot.end_time.strftime('%I:%M %p')
            reasons = ', '.join(slot.reasons)
            print(f"  {i}. {start_str} - {end_str} ({slot.duration_hours}h)")
            print(f"     Quality: {slot.quality_score:.2f} | {reasons}")
        
        # Test 3: Large slot splitting
        print("\n3️⃣ Testing large slot splitting...")
        
        # Clear events for this test
        CalendarEvent.objects.filter(student=student).delete()
        
        large_request = SlotRequest(
            duration_hours=8.0,
            subject='computer science',
            difficulty='moderate',
            task_type='project',
            allow_splitting=True
        )
        
        large_slots = slot_finder.find_slots(large_request)
        
        print(f"Found {len(large_slots)} slots for 8-hour project:")
        total_duration = 0
        for i, slot in enumerate(large_slots, 1):
            start_str = slot.start_time.strftime('%A %B %d at %I:%M %p')
            end_str = slot.end_time.strftime('%I:%M %p')
            split_info = " (SPLIT)" if slot.is_split else ""
            total_duration += slot.duration_hours
            reasons = ', '.join(slot.reasons)
            print(f"  {i}. {start_str} - {end_str} ({slot.duration_hours}h){split_info}")
            print(f"     Quality: {slot.quality_score:.2f} | {reasons}")
        
        print(f"Total duration covered: {total_duration}h / {large_request.duration_hours}h requested")
        
        # Test 4: Daily availability summary
        print("\n4️⃣ Testing daily availability summary...")
        
        test_date = (timezone.now() + timedelta(days=1)).date()
        availability = slot_finder.get_daily_availability_summary(test_date)
        
        print(f"Availability for {availability['date']}:")
        print(f"  Free hours: {availability['free_hours']:.1f}h / {availability['total_hours']:.1f}h total")
        print(f"  Availability: {availability['availability_percentage']:.1f}%")
        print(f"  Events: {availability['events_count']}")
        
        print("\n✅ All integration tests completed successfully!")
        
        # Clean up
        CalendarEvent.objects.filter(student=student).delete()
        print("✅ Cleaned up test data")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = test_slot_finder_integration()
    if success:
        print("\n🎉 Slot Finder integration tests PASSED!")
        sys.exit(0)
    else:
        print("\n💥 Slot Finder integration tests FAILED!")
        sys.exit(1)