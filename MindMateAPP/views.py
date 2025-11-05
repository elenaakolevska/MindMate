
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user

# Create your views here.

def home(request):
	if request.user.is_authenticated:
		return redirect('dashboard')  # Change 'dashboard' to your logged-in landing page name
	return render(request, 'home.html')
