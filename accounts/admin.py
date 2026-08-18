from django.contrib import admin
from .models import CustomUser, Branch

@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ['name', 'location', 'created_at']

@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ['username', 'full_name', 'email', 'employee_id', 'role', 'is_active', 'created_at']
    list_filter = ['role', 'is_active', 'branch']
    search_fields = ['username', 'email', 'full_name', 'employee_id']
    readonly_fields = ['created_at', 'updated_at']
