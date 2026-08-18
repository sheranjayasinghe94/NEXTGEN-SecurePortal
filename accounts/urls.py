from django.urls import path
from . import views

urlpatterns = [
    path('', views.admin_dashboard, name='admin_dashboard'),
    path('users/', views.user_list, name='user_list'),
    path('create-user/', views.create_user, name='create_user'),
    path('users/<uuid:user_id>/toggle/', views.toggle_user, name='toggle_user'),
    path('users/<uuid:user_id>/reset-password/', views.reset_user_password, name='reset_user_password'),
    path('audit/', views.audit_log_view, name='audit_log'),
]
