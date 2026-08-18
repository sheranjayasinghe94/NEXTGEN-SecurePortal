from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.user_dashboard, name='user_dashboard'),
    path('profile/', views.profile_view, name='user_profile'),
    path('security/', views.security_activity, name='security_activity'),
    path('module/<str:module_key>/', views.module_placeholder, name='portal_module'),
]
