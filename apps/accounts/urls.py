from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('whatsapp-login/', views.whatsapp_login, name='whatsapp_login'),
]

# Add API endpoint for sending OTP
from django.urls import include
from django.urls import re_path

# Add this to your main urls.py or create separate api urls
