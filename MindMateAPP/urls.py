from django.urls import path
from . import views

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
]
