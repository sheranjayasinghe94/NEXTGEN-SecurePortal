from django.contrib import admin
from .models import AuthenticationFlow, OTPRecord, TokenRecord, PasswordResetRecord, AuditLog

@admin.register(AuthenticationFlow)
class AuthenticationFlowAdmin(admin.ModelAdmin):
    list_display = ['auth_flow_id', 'user', 'status', 'otp_verified', 'token_verified', 'started_at']
    list_filter = ['status', 'otp_verified', 'token_verified']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['auth_flow_id', 'started_at']

@admin.register(OTPRecord)
class OTPRecordAdmin(admin.ModelAdmin):
    list_display = ['user', 'otp_type', 'is_verified', 'is_used', 'attempts', 'expires_at', 'created_at']
    list_filter = ['otp_type', 'is_verified', 'is_used']
    search_fields = ['user__username']
    readonly_fields = ['otp_hash', 'created_at']

@admin.register(TokenRecord)
class TokenRecordAdmin(admin.ModelAdmin):
    list_display = ['user', 'is_used', 'attempts', 'expires_at', 'created_at']
    list_filter = ['is_used']
    readonly_fields = ['token_hash', 'created_at']

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'user', 'action_type', 'ip_address', 'success']
    list_filter = ['action_type', 'success']
    search_fields = ['user__username', 'ip_address', 'description']
    readonly_fields = ['timestamp']
    ordering = ['-timestamp']
