#!/bin/bash

# Manual API Testing Script for Time Agent Slot Finder
# Run this after logging into the web interface first

echo "🧪 Testing Time Agent Slot Finder API"
echo "======================================"

# Base URL - adjust if running on different port
BASE_URL="http://localhost:8000"

echo ""
echo "📋 Step 1: First log into the web interface at $BASE_URL"
echo "   - Go to $BASE_URL in your browser"
echo "   - Create an account or login"
echo "   - Then come back here to test the API"
echo ""

read -p "Press Enter when you're logged in to continue..."

echo ""
echo "🔍 Testing Slot Finder API..."

# Test 1: Basic 2-hour math exam
echo ""
echo "Test 1: Finding slots for 2-hour hard math exam"
curl -X POST "$BASE_URL/api/time-agent/suggest-slots/" \
  -H "Content-Type: application/json" \
  -H "Cookie: sessionid=YOUR_SESSION_ID" \
  -d '{
    "duration_hours": 2.0,
    "subject": "mathematics",
    "difficulty": "hard",
    "task_type": "exam",
    "preferred_times": ["morning"]
  }' | jq '.'

echo ""
echo "Test 2: Finding slots for large project (8 hours with splitting)"
curl -X POST "$BASE_URL/api/time-agent/suggest-slots/" \
  -H "Content-Type: application/json" \
  -H "Cookie: sessionid=YOUR_SESSION_ID" \
  -d '{
    "duration_hours": 8.0,
    "subject": "computer science",
    "difficulty": "moderate", 
    "task_type": "project",
    "allow_splitting": true
  }' | jq '.'

echo ""
echo "Test 3: Easy task, any time preference"
curl -X POST "$BASE_URL/api/time-agent/suggest-slots/" \
  -H "Content-Type: application/json" \
  -H "Cookie: sessionid=YOUR_SESSION_ID" \
  -d '{
    "duration_hours": 1.0,
    "subject": "history",
    "difficulty": "easy",
    "task_type": "reading"
  }' | jq '.'

echo ""
echo "✅ API tests completed!"
echo "Note: Replace YOUR_SESSION_ID with your actual session ID from browser dev tools"