
from django.contrib import admin
from django.urls import path
from django.template.response import TemplateResponse
from .models import (
	Student, CalendarEvent, Progress, Streak, Accuracy, Badge, Quiz, QuizResult, Homework,
	ChatbotInteraction, ChatBot, ProgressAnalysis, EventPlanning, StudyPipeline, StudyAgent,
	StudyMaterial, StudySession, NextStudyTopic, QuizQuestion, StudentAnswer, Notification,
	StudentPreferences
)

# Custom admin dashboard view
class CustomAdminSite(admin.AdminSite):
	site_header = "MindMate Admin"
	site_title = "MindMate Admin Portal"
	index_title = "Welcome to MindMate Dashboard"

	def get_urls(self):
		urls = super().get_urls()
		from django.shortcuts import redirect
		from django.urls import path, re_path

		def index_redirect(request):
			return redirect('custom_admin:dashboard')

		def app_index_redirect(request, app_label):
			return redirect('custom_admin:dashboard')

		from django.contrib.auth import views as auth_views
		custom_urls = [
			path('', index_redirect, name='index'),
			path('dashboard/', self.admin_view(self.dashboard_view), name="dashboard"),
			path('login/', auth_views.LoginView.as_view(template_name='admin/login.html'), name='login'),
			path('logout/', auth_views.LogoutView.as_view(), name='logout'),
			path('password_change/', auth_views.PasswordChangeView.as_view(), name='password_change'),
			path('password_change/done/', auth_views.PasswordChangeDoneView.as_view(), name='password_change_done'),
			path('password_reset/', auth_views.PasswordResetView.as_view(), name='password_reset'),
			path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
			path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
			path('reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),
			re_path(r'^(?P<app_label>\w+)/$', app_index_redirect, name='app_list'),
		]
		return custom_urls + urls[1:]

	def dashboard_view(self, request):
		# Example stats (can be extended)
		context = dict(
			self.each_context(request),
			student_count=Student.objects.count(),
			quiz_count=Quiz.objects.count(),
			material_count=StudyMaterial.objects.count(),
			notification_count=Notification.objects.filter(is_read=False).count(),
			recent_students=Student.objects.order_by('-created_at')[:5],
			recent_quizzes=Quiz.objects.order_by('-created_at')[:5],
		)
		return TemplateResponse(request, "admin/dashboard.html", context)

custom_admin_site = CustomAdminSite(name='custom_admin')

# Inlines for better editing
class StudentPreferencesInline(admin.StackedInline):
	model = StudentPreferences
	extra = 0
	max_num = 1
	fields = (
		('major_field_of_study', 'current_courses'),
		('preferred_learning_style', 'daily_study_hours'),
		('learning_goals',),
		('key_interests', 'reminder_preferences'),
		('difficulty_preference', 'study_pace'),
		('ai_interaction_style', 'accessibility_needs')
	)

class QuizQuestionInline(admin.TabularInline):
	model = QuizQuestion
	extra = 1

class StudentAnswerInline(admin.TabularInline):
	model = StudentAnswer
	extra = 1

@admin.register(Student, site=custom_admin_site)
class StudentAdmin(admin.ModelAdmin):
	list_display = ("id", "full_name", "email", "study_level", "study_direction", "created_at")
	search_fields = ("full_name", "email", "study_direction", "interests")
	list_filter = ("study_level", "study_direction")
	inlines = [StudentPreferencesInline]

@admin.register(StudentPreferences, site=custom_admin_site)
class StudentPreferencesAdmin(admin.ModelAdmin):
	list_display = ("id", "student", "preferred_learning_style", "daily_study_hours", "reminder_preferences")
	search_fields = ("student__full_name", "major_field_of_study", "key_interests")
	list_filter = ("preferred_learning_style", "reminder_preferences", "difficulty_preference", "study_pace", "ai_interaction_style")
	fieldsets = (
		("Student", {
			"fields": ("student",)
		}),
		("Academic Information", {
			"fields": ("major_field_of_study", "current_courses")
		}),
		("Study Preferences", {
			"fields": ("preferred_learning_style", "daily_study_hours")
		}),
		("Goals", {
			"fields": ("learning_goals",)
		}),
		("Interests & Personalization", {
			"fields": ("key_interests", "reminder_preferences")
		}),
		("AI Personalization", {
			"fields": ("difficulty_preference", "study_pace", "ai_interaction_style")
		}),
		("Accessibility", {
			"fields": ("accessibility_needs",)
		})
	)

@admin.register(StudyMaterial, site=custom_admin_site)
class StudyMaterialAdmin(admin.ModelAdmin):
	list_display = ("id", "student", "type", "title", "subject", "upload_date")
	search_fields = ("title", "subject", "content")
	list_filter = ("type", "subject")

@admin.register(Quiz, site=custom_admin_site)
class QuizAdmin(admin.ModelAdmin):
	list_display = ("id", "quiz_type", "subject", "difficulty", "questions_count", "created_at")
	search_fields = ("subject",)
	list_filter = ("quiz_type", "difficulty")
	inlines = [QuizQuestionInline]

@admin.register(QuizResult, site=custom_admin_site)
class QuizResultAdmin(admin.ModelAdmin):
	list_display = ("id", "student", "quiz", "score", "accuracy_percentage", "taken_at")
	search_fields = ("student__full_name", "quiz__subject")
	list_filter = ("taken_at",)
	inlines = [StudentAnswerInline]

@admin.register(Badge, site=custom_admin_site)
class BadgeAdmin(admin.ModelAdmin):
	list_display = ("id", "student", "badge_name", "received_at")
	search_fields = ("badge_name", "description")
	list_filter = ("received_at",)

@admin.register(CalendarEvent, site=custom_admin_site)
class CalendarEventAdmin(admin.ModelAdmin):
	list_display = ("id", "student", "title", "date_time")
	search_fields = ("title", "description")
	list_filter = ("date_time",)

@admin.register(ChatbotInteraction, site=custom_admin_site)
class ChatbotInteractionAdmin(admin.ModelAdmin):
	list_display = ("id", "student", "bot_type", "event_action", "action_time")
	search_fields = ("event_action", "message_content", "response_content")
	list_filter = ("bot_type", "action_time")

@admin.register(Notification, site=custom_admin_site)
class NotificationAdmin(admin.ModelAdmin):
	list_display = ("id", "student", "title", "notification_type", "is_read", "created_at")
	search_fields = ("title", "message")
	list_filter = ("notification_type", "is_read")
	actions = ["mark_as_read"]

	def mark_as_read(self, request, queryset):
		updated = queryset.update(is_read=True)
		self.message_user(request, f"{updated} notifications marked as read.")
	mark_as_read.short_description = "Mark selected notifications as read"


# Group progress models for easier management
class ProgressInline(admin.TabularInline):
	model = Progress
	extra = 0

class StreakInline(admin.TabularInline):
	model = Streak
	extra = 0

class AccuracyInline(admin.TabularInline):
	model = Accuracy
	extra = 0

@admin.register(Progress, site=custom_admin_site)
class ProgressAdmin(admin.ModelAdmin):
	list_display = ("id", "student", "progress_bar", "completed_tasks")
	inlines = [StreakInline, AccuracyInline]
	search_fields = ("student__full_name",)
	list_filter = ("completed_tasks",)

# Register other models with default admin (no custom class)
for model in [Homework, ChatBot, ProgressAnalysis, EventPlanning, StudyPipeline, StudyAgent, StudySession, NextStudyTopic, QuizQuestion, StudentAnswer]:
	custom_admin_site.register(model)
