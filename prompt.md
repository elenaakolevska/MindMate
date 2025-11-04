## You are a Software Engineer specialized in Machine Learning and AI.
Below is the project documentation for the MVP phase of the Learning Assistant App — an intelligent study and organization platform designed for high school and college students.

Carefully read the entire documentation to understand the current architecture, core features, AI components (OCR, LangChain, GPT API), and user flows.

This document represents the current state of the project, and we will later provide additional implementation instructions and technical specifications (for example: database schema, API integration details, or frontend logic).

## Your task for now is to:

Fully understand the system’s structure and workflows (Study Agent, Time Agent, Calendar, Chatbot, etc.).

Note how OCR, LangChain, and GPT interact in the pipeline.

Prepare to propose the best way to extend or optimize this MVP later when new guidance is provided.

Read carefully — do not make assumptions or changes yet.
Wait for further instructions after reviewing the documentation below.

## Learning Assistant App – Project Documentation:
Learning Assistant App – Project Documentation
This application is intended for high school and college students, with the aim of helping them study more organized and efficient. While most educational apps focus on younger students, our MVP is specifically designed for older users who need advanced learning tools, quizzes, progress tracking, and time management.
Main Features
Study Agent
The Study Agent receives documents in various formats (PDF, images, Word) and processes them using Tesseract OCR to extract text. The extracted text is stored in a PostgreSQL database and is used to:
Search through uploaded materials for relevant information
Generate custom quizzes based on the content
Provide explanations of the learning material
Student progress is tracked through quiz results and learning history.
Calendar
FullCalendar.js in Django templates for visual management of the learning schedule. The chatbot can suggest optimal study terms, and students can manually add, edit, or delete terms. All calendar data is stored in the PostgreSQL database.
Progress Tracker and Motivation System
The progress tracking system includes:
Visual Progress Bar – a graphical display of completed assignments and quizzes
Accuracy Percentages – how accurate the quiz answers are
Streaks system – tracking consecutive days of activity (e.g.: 7 days of studying in a row)
Awards and Badges – students receive virtual awards for achieving goals (e.g. "10 quizzes completed", "30 day streak")
Chat Bot
The chatbot is available throughout the application and helps students organize their time and responsibilities. It will work with initial prompts to easily start a conversation (e.g.: "Plan my day", "Add a task for tomorrow"). This is not a learning tool, but an activity management tool and is directly connected to the calendar for automatic addition of events.
User Profile
When registering, students enter:
Direction of study
Interests outside of academia
Based on this data, the app offers personalized recommendations for academic and extracurricular activities.
OCR Homework Helper
We use Tesseract OCR, a free open-source tool developed by Google. Tesseract works offline without the need for an internet connection or API key and supports multiple languages ​​including Macedonian, English, and German.
MVP Phase (first 2 months)
In the first phase of development we plan to implement:
User profiles with personalization
Study Agent with quizzes and homework support
FullCalendar.js integration
Chatbot with predefined prompts
Progress tracking through quizzes
Motivation system (streaks and rewards)
Technical Implementation
Architecture
Django – monolithic architecture (frontend and backend together)
PostgreSQL – storing users, learning tasks, OCR text, calendar events
FullCalendar.js – visual calendar and term management
Tesseract OCR – text extraction from documents
LangChain – semantic search through the database and text processing
OpenAI GPT API – generating answers, quizzes and explanations
Workflow (AI/OCR)
Student asks a question or uploads a document
Tesseract OCR extracts the text from the document
LangChain searches the database for relevant information
GPT API formulates an answer or quiz
The result is displayed to the student
Chatbot Integration
The chatbot uses rule-based logic via LangChain and is directly connected to the calendar for automatic addition and editing of appointments.
Deployment
We plan to use cloud platforms such as Render, Railway or AWS to host the application. The PostgreSQL database can be cloud-hosted or local depending on the needs.

Main Actors
Student (User)
A high school or college student who uses the application for learning and organization.
Study Agent (AI Study Bot)
An intelligent agent specialized in learning, generating quizzes and helping with homework.
Time Agent (AI Calendar Bot)
A time and obligation organization agent that works with the calendar.
System (Application Server)
Manages databases, documents, quiz results and OCR processing.
Use Cases
UC1 – Registration and profile setup
Actor: Student
Goal: Registration and academic orientation and interests
Basic flow:
Student selects "Register" option
Enters data (name, email, password, level of studies)
Selects major (e.g. "Computer Science") and personal interests (e.g. "Psychology", "Photography")
System creates profile and personalizes content
Postcondition: Profile is active and ready to use
UC2 – Sending document to Study Agent
Actor: Student
Goal: Sending document (homework, note, screenshot) for analysis
Basic flow:
Student opens Study Agent window
Attach document (PDF, image, text)
OCR module reads text (if image)
Study Agent answers question or explains task
Alternative flow: If OCR cannot recognize, student receives message to
does not enter text manually
Postcondition: The student receives an explanation, answer, or tips for solving
UC3 – Solving a learning quiz
Actor: Student
Goal: Testing knowledge through quizzes
Basic flow:
The student selects a topic or subject
Study Agent generates a quiz (e.g. 10 multiple choice questions)
The student answers the questions
Upon completion, the system displays the result and explains the errors
Postcondition: The result is saved in the Progress Tracker
UC4 – Progress Tracking
Actor: Student
Goal: Overview of learning progress
Basic flow:
The student opens the "My Progress" tab
The system displays quiz results and the number of completed homework
Graphic display (progress bar, percentages by topic)
Postcondition: The student can identify weak areas
UC5 – Interaction with Time Agent (Calendar Chatbot)
Actor: Student
Goal: Organization of obligations and study time
Basic flow:
Student writes to the chatbot (e.g. "I have an exam next week, help me organize my studying")
Time Agent suggests time slots in the calendar
Student accepts or changes times
Time Agent adds events automatically
Postcondition: Calendar is updated with planned activities
UC6 – Manually adding an obligation to the calendar
Actor: Student
Goal: Add a term for studying, quiz or lecture
Basic flow:
Student opens the calendar
Selects a date and time
Enters a description ("studying math")
System saves the event
Postcondition: Event is displayed in the calendar
UC7 – Organization chatbot
Actor: Student
Goal: Communicate with AI chatbot for motivation, productivity or advice
Basic flow:
Student selects one of the predefined prompts:
"How can I focus better?"
"Help me plan for today"
Chatbot returns customized advice
Postcondition: Student receives motivational or organizational guidance

Use Examples
Scenario 1: Doing Homework
Anna, an economics student, takes a screenshot of a section of her statistics homework. She uploads the document to Study Agent. OCR reads the assignment and Study Agent explains step-by-step how to do it. Anna then takes a quiz to test her knowledge. Her statistics score increases in Progress Tracker.
Scenario 2: Planning Study for an Exam
Marco has a computer science exam next week. He writes to Time Agent: "Plan my study for 2 hours every day." The agent adds 2-hour slots to FullCalendar.js. Marco accepts some and changes others. The next day, he gets a reminder for the next study slot.
Scenario 3: Tracking Progress
Elena wants to see how she is doing on her biology quizzes. She opens Progress Tracker. She sees that she has 85% accuracy and 5 completed quizzes. The app suggests an additional quiz for the topics where he makes the most mistakes.
Scenario 4: Balancing learning and interests
Nikola studies physics, but has an interest in history. When registering, he enters both areas. The app offers him quizzes and articles for both, to encourage full development.
