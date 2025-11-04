
from django.db import models

class Student(models.Model):
    full_name = models.CharField(max_length=128)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128)  # For authentication
    study_level = models.CharField(max_length=32, choices=[('high_school', 'High School'), ('college', 'College')])
    study_direction = models.CharField(max_length=128)  # Major/field of study
    interests = models.TextField(blank=True)  # Personal interests for personalization
    created_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

class CalendarEvent(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    title = models.CharField(max_length=128)
    date_time = models.DateTimeField()
    description = models.TextField(blank=True)
    notes = models.TextField(blank=True)

class Progress(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    progress_bar = models.FloatField()
    completed_tasks = models.IntegerField()
    notes = models.TextField(blank=True)

class Streak(models.Model):
    progress = models.OneToOneField(Progress, on_delete=models.CASCADE)
    days_count = models.IntegerField()
    last_day = models.DateField()

class Accuracy(models.Model):
    progress = models.ForeignKey(Progress, on_delete=models.CASCADE)
    percentage = models.FloatField()

class Badge(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    badge_name = models.CharField(max_length=128)
    description = models.TextField(blank=True)
    received_at = models.DateField()

class Quiz(models.Model):
    quiz_type = models.CharField(max_length=64, choices=[('multiple_choice', 'Multiple Choice'), ('true_false', 'True/False'), ('short_answer', 'Short Answer')])
    subject = models.CharField(max_length=128, blank=True)  # Subject/topic
    difficulty = models.CharField(max_length=32, choices=[('easy', 'Easy'), ('medium', 'Medium'), ('hard', 'Hard')], default='medium')
    questions_count = models.IntegerField(default=10)
    generated_from_material = models.ForeignKey('StudyMaterial', on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class QuizResult(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE)
    score = models.IntegerField()  # Points earned
    max_score = models.IntegerField()  # Total possible points
    accuracy_percentage = models.FloatField()  # Calculated accuracy
    time_taken = models.DurationField(null=True, blank=True)  # Time to complete
    taken_at = models.DateTimeField(auto_now_add=True)

class Homework(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    material = models.ForeignKey('StudyMaterial', on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=32)
    assigned_at = models.DateField()
    completed_at = models.DateField(null=True, blank=True)

class ChatbotInteraction(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    bot_type = models.CharField(max_length=32, choices=[('study_agent', 'Study Agent'), ('time_agent', 'Time Agent'), ('organization', 'Organization Bot')])
    event_action = models.CharField(max_length=128)
    message_content = models.TextField()
    response_content = models.TextField(blank=True)  # Bot's response
    action_time = models.DateTimeField(auto_now_add=True)

class ChatBot(models.Model):
    description = models.TextField(blank=True)
    capabilities = models.TextField(blank=True)

class ProgressAnalysis(models.Model):
    bot = models.ForeignKey(ChatBot, on_delete=models.CASCADE)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    analysis_time = models.DateTimeField()
    results = models.TextField()

class EventPlanning(models.Model):
    bot = models.ForeignKey(ChatBot, on_delete=models.CASCADE)
    event = models.ForeignKey(CalendarEvent, on_delete=models.CASCADE)
    planning_time = models.DateTimeField()
    rationale = models.TextField()

class StudyPipeline(models.Model):
    description = models.TextField(blank=True)

class StudyAgent(models.Model):
    name = models.CharField(max_length=128, default="Study Agent")
    ocr_tool = models.CharField(max_length=128, default="Tesseract")
    supported_formats = models.CharField(max_length=256, default="PDF,Image,Word")
    ai_model = models.CharField(max_length=128, default="OpenAI GPT")
    is_active = models.BooleanField(default=True)

class StudyMaterial(models.Model):
    pipeline = models.ForeignKey(StudyPipeline, on_delete=models.SET_NULL, null=True, blank=True)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)  # Associate material with student
    type = models.CharField(max_length=64, choices=[('pdf', 'PDF'), ('image', 'Image'), ('word', 'Word Document'), ('text', 'Text')])
    title = models.CharField(max_length=256, blank=True)  # Document title
    original_filename = models.CharField(max_length=256, blank=True)  # Original file name
    file_path = models.CharField(max_length=512, blank=True)  # Path to uploaded file
    content = models.TextField()  # OCR extracted text
    upload_date = models.DateTimeField(auto_now_add=True)
    subject = models.CharField(max_length=128, blank=True)  # Subject/topic for organization

class StudySession(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    material = models.ForeignKey(StudyMaterial, on_delete=models.SET_NULL, null=True, blank=True)
    session_date = models.DateField()
    notes = models.TextField(blank=True)

class NextStudyTopic(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    material = models.ForeignKey(StudyMaterial, on_delete=models.SET_NULL, null=True, blank=True)
    suggested_for = models.DateField()
    status = models.CharField(max_length=32, choices=[('pending', 'Pending'), ('in_progress', 'In Progress'), ('completed', 'Completed')])

class QuizQuestion(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField()
    question_type = models.CharField(max_length=32, choices=[('multiple_choice', 'Multiple Choice'), ('true_false', 'True/False'), ('short_answer', 'Short Answer')])
    correct_answer = models.TextField()
    options = models.JSONField(blank=True, null=True)  # For multiple choice options
    explanation = models.TextField(blank=True)

class StudentAnswer(models.Model):
    quiz_result = models.ForeignKey(QuizResult, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(QuizQuestion, on_delete=models.CASCADE)
    student_answer = models.TextField()
    is_correct = models.BooleanField()
    points_earned = models.IntegerField(default=0)

class Notification(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    title = models.CharField(max_length=256)
    message = models.TextField()
    notification_type = models.CharField(max_length=32, choices=[('reminder', 'Reminder'), ('achievement', 'Achievement'), ('suggestion', 'Suggestion')])
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
