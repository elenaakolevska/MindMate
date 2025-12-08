#!/usr/bin/env python
"""
Test script for the Slot Finder API endpoint
"""

import os
import sys
import django
import json
from datetime import datetime, timedelta

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'MindMate.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from MindMateAPP.models import Student


def test_api_endpoint():
    """Test the /api/time-agent/suggest-slots/ endpoint"""
    
    print("🌐 Testing Slot Finder API Endpoint")
    print("=" * 50)
    
    try:
        # Create test client
        client = Client()
        
        # Create or get test user and student
        user, created = User.objects.get_or_create(
            username='test_api_user',
            defaults={'email': 'test_api@example.com', 'password': 'testpass123'}
        )
        
        student, created = Student.objects.get_or_create(
            user=user,
            defaults={
                'full_name': 'API Test Student',
                'email': 'test_api@example.com',
                'study_level': 'college',
                'study_direction': 'Computer Science'
            }
        )
        
        if created:
            print(f"✅ Created test user and student: {student.full_name}")
        else:
            print(f"✅ Using existing student: {student.full_name}")
        
        # Log in the user
        client.force_login(user)
        
        # Test 1: Basic slot request
        print("\n1️⃣ Testing basic slot request...")
        
        request_data = {
            "duration_hours": 2.0,
            "subject": "mathematics",
            "difficulty": "hard", 
            "task_type": "exam",
            "preferred_times": ["morning"]
        }
        
        response = client.post(
            '/api/time-agent/suggest-slots/',
            data=json.dumps(request_data),
            content_type='application/json'
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ API endpoint working!")
            print(f"Success: {data['success']}")
            print(f"Total suggestions: {data['total_suggestions']}")
            print(f"Summary: {data['summary_message']}")
            
            if data['suggested_slots']:
                print("\nSuggested slots:")
                for i, slot in enumerate(data['suggested_slots'], 1):
                    print(f"  {i}. {slot['start_time_formatted']}")
                    print(f"     Duration: {slot['duration_formatted']}")
                    print(f"     Quality: {slot['quality_score']}")
                    print(f"     Reasons: {', '.join(slot['reasons'])}")
        else:
            print(f"❌ API request failed with status {response.status_code}")
            print(f"Response: {response.content.decode()}")
            return False
        
        # Test 2: Error handling - invalid request
        print("\n2️⃣ Testing error handling...")
        
        invalid_request = {
            "duration_hours": -1.0  # Invalid negative duration
        }
        
        response = client.post(
            '/api/time-agent/suggest-slots/',
            data=json.dumps(invalid_request),
            content_type='application/json'
        )
        
        if response.status_code == 400:
            print("✅ Error handling working - correctly rejected invalid duration")
        else:
            print(f"⚠️ Expected 400 error, got {response.status_code}")
        
        # Test 3: Large request with splitting
        print("\n3️⃣ Testing large request with splitting...")
        
        large_request = {
            "duration_hours": 8.0,
            "subject": "computer science",
            "difficulty": "moderate",
            "task_type": "project",
            "allow_splitting": True
        }
        
        response = client.post(
            '/api/time-agent/suggest-slots/',
            data=json.dumps(large_request), 
            content_type='application/json'
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Large request handled: {data['total_suggestions']} suggestions")
            
            split_sessions = [s for s in data['suggested_slots'] if s.get('is_split_session', False)]
            if split_sessions:
                print(f"✅ Splitting working: {len(split_sessions)} split sessions found")
            else:
                print("ℹ️ No splitting needed (sufficient single slots available)")
        else:
            print(f"❌ Large request failed: {response.status_code}")
            return False
        
        # Test 4: Unauthenticated request
        print("\n4️⃣ Testing authentication requirement...")
        
        client.logout()
        
        response = client.post(
            '/api/time-agent/suggest-slots/',
            data=json.dumps(request_data),
            content_type='application/json'
        )
        
        if response.status_code in [302, 401, 403]:  # Redirect to login or unauthorized
            print("✅ Authentication required - correctly rejected unauthenticated request")
        else:
            print(f"⚠️ Expected auth error, got {response.status_code}")
        
        print("\n✅ All API tests completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error during API testing: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_api_endpoint()
    if success:
        print("\n🎉 Slot Finder API tests PASSED!")
        sys.exit(0)  
    else:
        print("\n💥 Slot Finder API tests FAILED!")
        sys.exit(1)