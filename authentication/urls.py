from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing, name='landing'),
    path('login/', views.login_choice, name='login_choice'),
    path('admin-login/', views.admin_login, name='admin_login'),
    path('admin-logout/', views.admin_logout, name='admin_logout'),
    path('user-login/', views.user_login, name='user_login'),
    path('change-password/', views.force_change_password, name='force_change_password'),
    path('verify-otp/', views.verify_otp, name='verify_otp'),
    path('resend-otp/', views.resend_otp, name='resend_otp'),
    path('verify-token/', views.verify_token, name='verify_token'),
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('reset-otp/', views.reset_otp_verify, name='reset_otp_verify'),
    path('set-password/', views.set_new_password, name='set_new_password'),
    path('logout/', views.user_logout, name='user_logout'),
]
