"""
Views for user registration, login, and logout with Uzbek localization.
"""
from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib.auth import login, logout
from django.contrib import messages
from django.utils.http import url_has_allowed_host_and_scheme
from .forms import UserRegistrationForm, UserLoginForm

def register_view(request):
    if request.user.is_authenticated:
        if hasattr(request.user, 'student_profile') and not request.user.student_profile.onboarding_completed:
            return redirect('onboarding:step_1')
        return redirect('dashboard:index')

    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user, backend='apps.accounts.backends.PhoneAuthBackend')
            messages.success(request, "Ro'yxatdan muvaffaqiyatli o'tdingiz! Endi o'quv profilingizni sozlang.")
            return redirect('onboarding:step_1')
    else:
        form = UserRegistrationForm()

    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        if hasattr(request.user, 'student_profile') and not request.user.student_profile.onboarding_completed:
            return redirect('onboarding:step_1')
        return redirect('dashboard:index')

    if request.method == 'POST':
        form = UserLoginForm(request.POST, request=request)
        if form.is_valid():
            login(request, form.user, backend='apps.accounts.backends.PhoneAuthBackend')
            messages.success(request, "Xush kelibsiz!")
            
            next_url = request.GET.get('next') or request.POST.get('next')
            if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
                return redirect(next_url)
            
            if hasattr(form.user, 'student_profile') and not form.user.student_profile.onboarding_completed:
                return redirect('onboarding:step_1')
            return redirect('dashboard:index')
    else:
        form = UserLoginForm(request=request)

    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.info(request, "Tizimdan muvaffaqiyatli chiqdingiz.")
    return redirect('accounts:login')
