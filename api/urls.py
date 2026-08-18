from django.urls import path
from . import views

urlpatterns = [
    path('generate-token/', views.generate_token, name='api_generate_token'),
    path('register-device/', views.register_device, name='api_register_device'),
]
