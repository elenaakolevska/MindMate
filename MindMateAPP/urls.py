from django.urls import path
from . import views, time_agent_views, quiz_views
from . import study_agent_views 

app_name = 'mindmate'

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('login/', views.login, name='login'),
    path('logout/', views.logout, name='logout'),
    path('preferences/', views.student_preferences, name='student_preferences'),
    path('registration-success/', views.registration_success, name='registration_success'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('upload-document/', views.upload_document, name='upload_document'),
    
    # Calendar URLs
    path('dashboard/calendar/', views.calendar_view, name='calendar'),
    path('dashboard/api/events/', views.api_events, name='api_events'),
    path('dashboard/api/events/<int:event_id>/', views.api_event_detail, name='api_event_detail'),
    
    # Study Agent Chat Interface (main page)
    path('study-agent/', study_agent_views.study_agent_chat_view, name='study_agent_chat'),
    path('study-agent/chat/', study_agent_views.study_agent_chat_api, name='study_agent_chat_api'),
    path('study-agent/stream/', study_agent_views.study_agent_stream_api, name='study_agent_stream'),
    path('study-agent/history/', study_agent_views.chat_history_api, name='study_agent_history'),
    path('study-agent/clear/', study_agent_views.clear_chat_history_api, name='study_agent_clear'),
    path('study-agent/sessions/<str:session_id>/delete/', study_agent_views.delete_session_api, name='delete_session'),

    # Study Agent API URLs
    path('api/study-agent/recent-documents/', views.get_recent_documents, name='study_agent_recent_documents'),
    path('api/study-agent/documents/<int:document_id>/delete/', views.delete_document, name='delete_document'),

    # Time Agent API URLs
    path('api/time-agent/estimate/', time_agent_views.estimate_task_time, name='time_agent_estimate'),
    path('api/time-agent/estimate/<int:estimation_id>/complete/', time_agent_views.record_task_completion, name='time_agent_complete'),
    path('api/time-agent/history/', time_agent_views.get_estimation_history, name='time_agent_history'),
    path('api/time-agent/analytics/', time_agent_views.get_performance_analytics, name='time_agent_analytics'),
    path('api/time-agent/schedule/', time_agent_views.suggest_study_schedule, name='time_agent_schedule'),
    path('api/time-agent/suggest-slots/', time_agent_views.suggest_time_slots, name='time_agent_suggest_slots'),
    path('api/time-agent/chat/', time_agent_views.chat_with_agent, name='time_agent_chat'),
    path('api/time-agent/test-ollama/', time_agent_views.test_ollama_connection, name='test_ollama'),

    # Quiz Generation API URLs
    path('api/quiz/generate/', quiz_views.generate_quiz, name='quiz_generate'),
    path('api/quiz/<int:quiz_id>/', quiz_views.get_quiz, name='quiz_get'),
    path('api/quiz/<int:quiz_id>/submit/', quiz_views.submit_quiz, name='quiz_submit'),
    path('api/quiz/results/<int:quiz_result_id>/', quiz_views.get_quiz_results, name='quiz_results'),
    path('api/quiz/student/', quiz_views.list_student_quizzes, name='quiz_student_list'),
    path('api/quiz/generation-status/', quiz_views.quiz_generation_status, name='quiz_generation_status'),
    
    # Quiz Interface URLs
    path('quiz/dashboard/', quiz_views.quiz_dashboard, name='quiz_dashboard'),
    path('quiz/<int:quiz_id>/take/', quiz_views.quiz_interface, name='quiz_take'),
    path('quiz/results/<int:quiz_result_id>/', quiz_views.quiz_results_view, name='quiz_results_view'),

    path('profile/', views.profile_view, name='profile'),
]
