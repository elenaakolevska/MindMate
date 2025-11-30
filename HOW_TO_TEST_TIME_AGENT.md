# Time Agent Chat Interface - How to Test

## 🚀 How to Access and Test the Time Agent

### 1. **Access the Application**
1. Make sure your Docker containers are running:
   ```bash
   cd /Users/jovanoskalj/Desktop/MindMate
   docker compose up -d
   ```

2. Open your web browser and go to: **http://localhost:8000**

### 2. **Login or Create Account**
- If you don't have an account, click "Register" and create one
- If you have an account, login with your credentials
- You'll be redirected to the dashboard after successful login

### 3. **Navigate to Calendar with Time Agent**
- From the dashboard, click on "**Calendar**" in the left sidebar
- OR go directly to: **http://localhost:8000/dashboard/calendar/**

### 4. **Test the Time Agent Chat**

You'll see a split-screen layout:
- **Left side**: Your calendar
- **Right side**: Time Agent chat interface

#### Try these example messages:

1. **Basic Task Estimation:**
   ```
   Колку време треба за учење за испит по математика?
   ```

2. **Reading Tasks:**
   ```
   Колку време треба за читање на 50 страници?
   ```

3. **Project Work:**
   ```
   Колку време треба за програмски проект?
   ```

4. **Specific Tasks:**
   ```
   Треба да направам домашна работа по биologija
   ```

5. **Complex Tasks:**
   ```
   Подготовка за финален испит по физика со 200 страници материјал
   ```

### 5. **Chat Features to Test:**

#### ✅ **Quick Suggestions**
- Click on the blue suggestion buttons below the chat input
- These provide common questions you can ask

#### ✅ **Time Estimation Results**
- When you ask for time estimation, you'll get:
  - **Estimated Hours**: How long the task will take
  - **Confidence Level**: How sure the AI is about the estimate
  - **Difficulty Assessment**: Easy, Medium, Hard, Very Hard
  - **Time Breakdown**: Preparation, Main Work, Review time
  - **Recommendations**: Study approach suggestions

#### ✅ **Calendar Integration**
- After getting an estimate, click "📅 **Додај во календар**"
- This will open the calendar event creation with pre-filled data
- You can adjust the time and save it to your calendar

#### ✅ **Interactive Features**
- Chat responds in real-time
- Typing indicator shows when Time Agent is "thinking"
- Message history is preserved during your session
- Responsive design works on mobile and desktop

### 6. **Testing Different Scenarios:**

#### **New Student (No History):**
- First-time estimates use general heuristics
- System provides reasonable defaults based on task type

#### **Student with History:**
- As you use the system more, it will learn from your patterns
- Estimates become more personalized over time

#### **API Testing:**
- The chat interface calls the same API endpoints we created
- You can also test the API directly using tools like Postman

### 7. **Expected Behavior:**

✅ **What Should Work:**
- Chat interface loads properly
- You can send messages by typing and pressing Enter
- Time Agent responds with estimations
- Results include time breakdowns and recommendations
- "Add to Calendar" button opens the event creation modal
- Calendar and chat work side-by-side

⚠️ **Fallback Mode:**
- If the API connection fails, the system provides intelligent fallback estimates
- This ensures the chat always works even during development

### 8. **Troubleshooting:**

If something doesn't work:

1. **Check Server Status:**
   ```bash
   docker compose ps
   ```

2. **Check Logs:**
   ```bash
   docker compose logs web --tail=20
   ```

3. **Restart if Needed:**
   ```bash
   docker compose restart web
   ```

4. **Browser Console:**
   - Press F12 to open developer tools
   - Check the Console tab for any JavaScript errors

### 9. **Demo Script:**

Here's a complete test sequence you can follow:

1. **Navigate to Calendar**: http://localhost:8000/dashboard/calendar/
2. **Send Message**: "Колку време треба за учење за испит по математика?"
3. **Review Response**: Check the time estimate and breakdown
4. **Add to Calendar**: Click the "Додај во календар" button
5. **Create Event**: Fill in details and save
6. **Ask Follow-up**: "Кои фактори влијаат на проценката?"
7. **Test Quick Suggestions**: Click on the suggestion buttons

### 🎯 **Success Indicators:**

- ✅ Chat interface loads without errors
- ✅ Messages send and receive properly  
- ✅ Time estimates are reasonable (1-5 hours for most tasks)
- ✅ Calendar integration works
- ✅ Responsive design adapts to screen size
- ✅ API endpoints respond correctly (check Network tab in browser)

The Time Agent is now fully integrated into your calendar page and ready for testing! 🚀