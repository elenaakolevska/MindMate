
from django.db import models
from django.contrib.auth.models import User
from datetime import timedelta

class Student(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)  # Link to Django User
    full_name = models.CharField(max_length=128)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128)  # Keep for backward compatibility, but use Django auth
    study_level = models.CharField(max_length=32, choices=[('high_school', 'High School'), ('college', 'College')])
    study_direction = models.CharField(max_length=128)  # Major/field of study
    interests = models.TextField(blank=True)  # Personal interests for personalization
    created_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

class CalendarEvent(models.Model):
    EVENT_TYPE_CHOICES = [
        ('study_session', 'Study Session'),
        ('exam', 'Exam'),
        ('homework_deadline', 'Homework Deadline'),
        ('personal', 'Personal Event'),
    ]
    
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    title = models.CharField(max_length=128)
    date_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)  # Optional end time for events
    event_type = models.CharField(max_length=20, choices=EVENT_TYPE_CHOICES, default='personal')
    color = models.CharField(max_length=7, default='#4285f4')  # Hex color code
    description = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    
    def save(self, *args, **kwargs):
        # Auto-assign color based on event type if not set
        if not self.color or self.color == '#4285f4':
            color_mapping = {
                'study_session': '#4285f4',  # Blue
                'exam': '#ea4335',           # Red
                'homework_deadline': '#ff9800',  # Orange
                'personal': '#34a853',       # Green
            }
            self.color = color_mapping.get(self.event_type, '#4285f4')
        super().save(*args, **kwargs)

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
    PROCESSING_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('partial', 'Partially Completed')
    ]
    
    pipeline = models.ForeignKey(StudyPipeline, on_delete=models.SET_NULL, null=True, blank=True)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)  # Associate material with student
    type = models.CharField(max_length=64, choices=[('pdf', 'PDF'), ('image', 'Image'), ('word', 'Word Document'), ('text', 'Text')])
    title = models.CharField(max_length=256, blank=True)  # Document title
    original_filename = models.CharField(max_length=256, blank=True)  # Original file name
    file_path = models.CharField(max_length=512, blank=True)  # Path to uploaded file
    content = models.TextField(blank=True)  # OCR extracted text
    upload_date = models.DateTimeField(auto_now_add=True)
    subject = models.CharField(max_length=128, blank=True)  # Subject/topic for organization
    
    # OCR Processing fields
    processing_status = models.CharField(max_length=32, choices=PROCESSING_STATUS_CHOICES, default='pending')
    processing_error = models.TextField(blank=True)  # Store error messages
    processing_date = models.DateTimeField(null=True, blank=True)  # When OCR was completed
    
    # File metadata
    file_size = models.PositiveIntegerField(default=0)  # File size in bytes
    
    def __str__(self):
        return f"{self.title or self.original_filename} - {self.student.full_name}"

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

class StudentPreferences(models.Model):
    LEARNING_STYLE_CHOICES = [
        ('visual', 'Visual (learning through seeing)'),
        ('auditory', 'Auditory (learning through hearing)'),
        ('kinesthetic', 'Kinesthetic (learning through doing)'),
        ('reading_writing', 'Reading/Writing (learning through text)'),
    ]
    
    REMINDER_TYPE_CHOICES = [
        ('email', 'Email'),
        ('push_notifications', 'Push Notifications'),
        ('in_app_alerts', 'In-app alerts'),
        ('sms', 'SMS'),
        ('none', 'No reminders'),
    ]
    

    
    student = models.OneToOneField(Student, on_delete=models.CASCADE, related_name='preferences')
    
    # Academic Information
    major_field_of_study = models.CharField(max_length=256, blank=True, help_text="e.g., Computer Science, Biology")
    current_courses = models.TextField(blank=True, help_text="List of current courses, separated by commas")
    
    # Study Preferences
    preferred_learning_style = models.CharField(max_length=20, choices=LEARNING_STYLE_CHOICES, blank=True)
    daily_study_hours = models.FloatField(default=4.0, help_text="Typical daily study hours")
    
    # Goals
    learning_goals = models.TextField(blank=True, help_text="e.g., Improve grades by 10%, learn a new coding language")
    
    # Interests & Personalization
    key_interests = models.TextField(blank=True, help_text="Comma-separated list of interests")
    reminder_preferences = models.CharField(max_length=20, choices=REMINDER_TYPE_CHOICES, default='in_app_alerts')
    
    # Additional preferences for AI personalization
    difficulty_preference = models.CharField(
        max_length=20, 
        choices=[('easy', 'Easy'), ('medium', 'Medium'), ('hard', 'Hard'), ('adaptive', 'Adaptive')],
        default='adaptive',
        help_text="Preferred difficulty level for generated content"
    )
    
    study_pace = models.CharField(
        max_length=20,
        choices=[('slow', 'Slow and steady'), ('moderate', 'Moderate pace'), ('fast', 'Fast-paced'), ('intensive', 'Intensive')],
        default='moderate',
        help_text="Preferred learning pace"
    )
    
    # AI interaction preferences
    ai_interaction_style = models.CharField(
        max_length=20,
        choices=[
            ('formal', 'Formal and professional'), 
            ('friendly', 'Friendly and conversational'), 
            ('motivational', 'Motivational and encouraging'),
            ('direct', 'Direct and to the point')
        ],
        default='friendly',
        help_text="Preferred AI interaction style"
    )
    
    # Accessibility and special needs
    accessibility_needs = models.TextField(blank=True, help_text="Any special accessibility requirements")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.student.full_name}'s Preferences"
    
    class Meta:
        verbose_name = "Student Preference"
        verbose_name_plural = "Student Preferences"

class Notification(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    title = models.CharField(max_length=256)
    message = models.TextField()
    notification_type = models.CharField(max_length=32, choices=[('reminder', 'Reminder'), ('achievement', 'Achievement'), ('suggestion', 'Suggestion')])
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)


# Time Agent Models for Task Estimation

class TaskEstimationRequest(models.Model):
    """Store task estimation requests for learning and improvement"""
    ESTIMATION_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('in_progress', 'In Progress'),
        ('cancelled', 'Cancelled'),
    ]
    
    TASK_TYPE_CHOICES = [
        ('study', 'Study Session'),
        ('exam', 'Exam Preparation'),
        ('quiz', 'Quiz Preparation'),
        ('homework', 'Homework'),
        ('assignment', 'Assignment'),
        ('project', 'Project Work'),
        ('reading', 'Reading'),
        ('research', 'Research'),
        ('writing', 'Writing'),
        ('practice', 'Practice'),
        ('other', 'Other'),
    ]
    
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='task_estimations')
    task_description = models.TextField(help_text="Natural language description of the task")
    task_type = models.CharField(max_length=32, choices=TASK_TYPE_CHOICES, default='study')
    subject_area = models.CharField(max_length=128, blank=True, help_text="e.g., Mathematics, Biology, Computer Science")
    
    # Estimation results
    estimated_hours = models.FloatField(help_text="Estimated completion time in hours")
    confidence_score = models.FloatField(default=0.5, help_text="Confidence level (0.0 to 1.0)")
    estimation_method = models.CharField(max_length=64, default='hybrid', help_text="Method used for estimation")
    
    # Context information
    difficulty_level = models.CharField(
        max_length=20,
        choices=[('easy', 'Easy'), ('moderate', 'Moderate'), ('challenging', 'Challenging'), ('very_challenging', 'Very Challenging')],
        default='moderate'
    )
    urgency_level = models.CharField(
        max_length=20,
        choices=[('low', 'Low'), ('normal', 'Normal'), ('high', 'High'), ('urgent', 'Urgent')],
        default='normal'
    )
    deadline = models.DateTimeField(null=True, blank=True, help_text="Task deadline if specified")
    
    # AI-generated insights
    reasoning = models.TextField(blank=True, help_text="AI-generated reasoning for the estimate")
    factors_considered = models.JSONField(default=list, help_text="List of factors considered in estimation")
    recommended_approach = models.TextField(blank=True, help_text="AI-recommended study approach")
    potential_obstacles = models.JSONField(default=list, help_text="Potential challenges identified")
    time_breakdown = models.JSONField(default=dict, help_text="Breakdown of time allocation")
    
    # Tracking and learning
    status = models.CharField(max_length=32, choices=ESTIMATION_STATUS_CHOICES, default='pending')
    actual_hours_spent = models.FloatField(null=True, blank=True, help_text="Actual time spent when completed")
    accuracy_score = models.FloatField(null=True, blank=True, help_text="Estimation accuracy (0.0 to 1.0)")
    student_feedback = models.TextField(blank=True, help_text="Student feedback on estimation quality")
    
    # Suggested scheduling
    suggested_start_time = models.DateTimeField(null=True, blank=True)
    suggested_end_time = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['student', 'task_type']),
            models.Index(fields=['student', 'subject_area']),
            models.Index(fields=['status', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.student.full_name}: {self.task_description[:50]}... ({self.estimated_hours}h)"
    
    def calculate_accuracy(self):
        """Calculate estimation accuracy when actual time is recorded"""
        if self.actual_hours_spent is not None and self.estimated_hours > 0:
            error = abs(self.estimated_hours - self.actual_hours_spent) / self.estimated_hours
            self.accuracy_score = max(0.0, 1.0 - error)  # Higher is better
            return self.accuracy_score
        return None
    
    def get_time_deviation_percentage(self):
        """Get percentage deviation from estimated time"""
        if self.actual_hours_spent is not None and self.estimated_hours > 0:
            return ((self.actual_hours_spent - self.estimated_hours) / self.estimated_hours) * 100
        return None


class TaskEstimationFeedback(models.Model):
    """Store detailed feedback for improving estimation algorithms"""
    FEEDBACK_TYPE_CHOICES = [
        ('accuracy', 'Estimation Accuracy'),
        ('difficulty', 'Task Difficulty Assessment'),
        ('obstacles', 'Unexpected Obstacles'),
        ('time_breakdown', 'Time Breakdown Accuracy'),
        ('general', 'General Feedback'),
    ]
    
    estimation = models.ForeignKey(TaskEstimationRequest, on_delete=models.CASCADE, related_name='feedback_entries')
    feedback_type = models.CharField(max_length=32, choices=FEEDBACK_TYPE_CHOICES, default='general')
    rating = models.IntegerField(help_text="Rating from 1-5 (5 being excellent)")
    comments = models.TextField(blank=True, help_text="Detailed feedback comments")
    
    # Specific feedback data
    was_too_optimistic = models.BooleanField(default=False, help_text="Was the estimate too optimistic?")
    was_too_pessimistic = models.BooleanField(default=False, help_text="Was the estimate too pessimistic?")
    unexpected_difficulties = models.JSONField(default=list, help_text="Unexpected challenges encountered")
    helpful_suggestions = models.JSONField(default=list, help_text="Which suggestions were most helpful")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Feedback for {self.estimation.task_description[:30]}... ({self.rating}/5)"


class StudentPerformanceProfile(models.Model):
    """Aggregated performance profile for personalized estimation"""
    student = models.OneToOneField(Student, on_delete=models.CASCADE, related_name='performance_profile')
    
    # Overall performance metrics
    total_estimations = models.IntegerField(default=0)
    average_accuracy_score = models.FloatField(default=0.5, help_text="Average estimation accuracy")
    estimation_improvement_trend = models.FloatField(default=0.0, help_text="Improvement trend over time")
    
    # Subject-specific performance
    subject_performance_data = models.JSONField(default=dict, help_text="Performance data by subject")
    task_type_performance = models.JSONField(default=dict, help_text="Performance data by task type")
    
    # Behavioral patterns
    typical_overestimation_factor = models.FloatField(default=1.0, help_text="How much student typically overestimates")
    typical_underestimation_factor = models.FloatField(default=1.0, help_text="How much student typically underestimates")
    consistency_score = models.FloatField(default=0.5, help_text="How consistent student's performance is")
    
    # Learning preferences impact
    learning_style_effectiveness = models.JSONField(default=dict, help_text="Effectiveness of different learning styles")
    difficulty_preference_accuracy = models.JSONField(default=dict, help_text="Accuracy by difficulty preference")
    
    # Time management patterns
    preferred_study_times = models.JSONField(default=list, help_text="Most productive study time slots")
    average_session_length = models.FloatField(default=2.0, help_text="Average effective study session length")
    break_frequency_optimal = models.FloatField(default=0.25, help_text="Optimal break frequency")
    
    # Recent performance (last 30 days)
    recent_accuracy_score = models.FloatField(default=0.5)
    recent_completion_rate = models.FloatField(default=0.8, help_text="Percentage of tasks completed as planned")
    recent_feedback_score = models.FloatField(default=3.0, help_text="Average feedback rating (1-5)")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_calculation = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Student Performance Profile"
        verbose_name_plural = "Student Performance Profiles"
    
    def __str__(self):
        return f"{self.student.full_name}'s Performance Profile (Accuracy: {self.average_accuracy_score:.2f})"
    
    def update_performance_metrics(self):
        """Update performance metrics based on recent estimations"""
        from django.db.models import Avg, Count
        from datetime import datetime, timedelta
        
        # Get recent estimations with actual completion data
        recent_estimations = TaskEstimationRequest.objects.filter(
            student=self.student,
            status='completed',
            actual_hours_spent__isnull=False,
            completed_at__gte=datetime.now() - timedelta(days=90)  # Last 3 months
        )
        
        if recent_estimations.exists():
            # Update accuracy metrics
            accuracies = [est.calculate_accuracy() for est in recent_estimations if est.calculate_accuracy() is not None]
            if accuracies:
                self.average_accuracy_score = sum(accuracies) / len(accuracies)
                
                # Calculate recent accuracy (last 30 days)
                recent_estimations_30d = recent_estimations.filter(
                    completed_at__gte=datetime.now() - timedelta(days=30)
                )
                if recent_estimations_30d.exists():
                    recent_accuracies = [est.calculate_accuracy() for est in recent_estimations_30d if est.calculate_accuracy() is not None]
                    if recent_accuracies:
                        self.recent_accuracy_score = sum(recent_accuracies) / len(recent_accuracies)
            
            # Update total estimations
            self.total_estimations = recent_estimations.count()
            
            # Update subject performance
            subject_performance = {}
            for estimation in recent_estimations:
                subject = estimation.subject_area or 'general'
                if subject not in subject_performance:
                    subject_performance[subject] = {'count': 0, 'accuracy_sum': 0.0}
                
                accuracy = estimation.calculate_accuracy()
                if accuracy is not None:
                    subject_performance[subject]['count'] += 1
                    subject_performance[subject]['accuracy_sum'] += accuracy
            
            # Calculate average accuracy per subject
            for subject, data in subject_performance.items():
                if data['count'] > 0:
                    data['average_accuracy'] = data['accuracy_sum'] / data['count']
            
            self.subject_performance_data = subject_performance
            
        self.last_calculation = datetime.now()
        self.save()


class TaskCompletionLog(models.Model):
    """Detailed log of task completion for learning patterns"""
    estimation = models.OneToOneField(TaskEstimationRequest, on_delete=models.CASCADE, related_name='completion_log')
    
    # Actual completion details
    actual_start_time = models.DateTimeField(null=True, blank=True)
    actual_end_time = models.DateTimeField(null=True, blank=True)
    total_breaks_taken = models.IntegerField(default=0)
    total_break_duration = models.DurationField(null=True, blank=True)
    
    # Effectiveness metrics
    focus_quality_rating = models.IntegerField(default=3, help_text="Self-rated focus quality (1-5)")
    energy_level_start = models.IntegerField(default=3, help_text="Energy level at start (1-5)")
    energy_level_end = models.IntegerField(default=3, help_text="Energy level at end (1-5)")
    satisfaction_rating = models.IntegerField(default=3, help_text="Satisfaction with work quality (1-5)")
    
    # Environmental factors
    study_location = models.CharField(max_length=128, blank=True, help_text="Where the study took place")
    distractions_encountered = models.JSONField(default=list, help_text="List of distractions")
    tools_used = models.JSONField(default=list, help_text="Study tools and resources used")
    
    # Learning outcomes
    concepts_mastered = models.JSONField(default=list, help_text="Key concepts learned/mastered")
    areas_needing_review = models.JSONField(default=list, help_text="Areas identified for further review")
    follow_up_tasks = models.JSONField(default=list, help_text="Additional tasks identified")
    
    # Notes
    student_notes = models.TextField(blank=True, help_text="Student's reflection on the session")
    completion_challenges = models.TextField(blank=True, help_text="Challenges faced during completion")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Completion log for {self.estimation.task_description[:30]}..."
    
    def get_effective_study_time(self):
        """Calculate effective study time (excluding breaks)"""
        if self.actual_start_time and self.actual_end_time:
            total_time = self.actual_end_time - self.actual_start_time
            break_duration = self.total_break_duration or timedelta(0)
            return total_time - break_duration
        return None
