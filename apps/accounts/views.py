from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
import json
import requests
from django.conf import settings

def login_view(request):
    if request.user.is_authenticated:
        return redirect('core:index')
    
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Selamat datang kembali, {username}!')
                next_url = request.GET.get('next', 'core:index')
                return redirect(next_url)
        messages.error(request, 'Username atau password salah.')
    
    form = AuthenticationForm()
    return render(request, 'accounts/login.html', {'form': form})

def register_view(request):
    if request.user.is_authenticated:
        return redirect('core:index')
    
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Save phone number if provided
            phone = request.POST.get('phone', '')
            if phone:
                user.profile.phone = phone  # You need to create a Profile model
            login(request, user)
            messages.success(request, 'Akun berhasil dibuat! Selamat bergabung.')
            return redirect('core:index')
        else:
            for error in form.errors.values():
                messages.error(request, error)
    
    form = UserCreationForm()
    return render(request, 'accounts/login.html', {'form': form})

def logout_view(request):
    logout(request)
    messages.success(request, 'Anda telah logout.')
    return redirect('core:index')

@csrf_exempt
def send_wa_otp(request):
    """API endpoint to send OTP via Fonnte"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            phone_number = data.get('phone_number')
            message = data.get('message')
            
            # Format phone number
            if phone_number.startswith('0'):
                phone_number = '62' + phone_number[1:]
            elif not phone_number.startswith('62'):
                phone_number = '62' + phone_number
            
            # Send via Fonnte API
            headers = {
                'Authorization': settings.FONNTE_API_KEY,
                'Content-Type': 'application/json'
            }
            
            payload = {
                'target': phone_number,
                'message': message,
                'countryCode': '62'
            }
            
            response = requests.post(
                f"{settings.FONNTE_BASE_URL}/send",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                return JsonResponse({'success': True})
            else:
                return JsonResponse({'success': False, 'error': response.text})
                
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Method not allowed'})

@csrf_exempt
def whatsapp_login(request):
    """Handle WhatsApp login"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            phone_number = data.get('phone_number')
            
            # Check if user exists with this phone number
            # You need to add phone field to User model or create Profile model
            # For now, create or get user by phone
            username = f"wa_{phone_number[-8:]}"
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': f"{username}@whatsapp.user"
                }
            )
            
            if created:
                user.set_unusable_password()
                user.save()
            
            login(request, user)
            return JsonResponse({'success': True})
            
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    
    return JsonResponse({'success': False, 'message': 'Method not allowed'})
