from django.urls import path
from . import views, time_agent_views

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
    
    # Time Agent API URLs
    path('api/time-agent/estimate/', time_agent_views.estimate_task_time, name='time_agent_estimate'),
    path('api/time-agent/estimate/<int:estimation_id>/complete/', time_agent_views.record_task_completion, name='time_agent_complete'),
    path('api/time-agent/history/', time_agent_views.get_estimation_history, name='time_agent_history'),
    path('api/time-agent/analytics/', time_agent_views.get_performance_analytics, name='time_agent_analytics'),
    path('api/time-agent/schedule/', time_agent_views.suggest_study_schedule, name='time_agent_schedule'),
]
