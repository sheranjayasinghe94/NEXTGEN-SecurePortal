import secrets
import string
from datetime import timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import get_user_model

from authentication.models import AuditLog
from authentication.views import get_client_ip, generate_temp_password, log_event

from accounts.models import CustomUser, Branch
from authentication.models import AuditLog, DeviceRegistrationCode, RegisteredDevice
from authentication.views import get_client_ip, generate_temp_password, log_event

User = CustomUser


def admin_required(view_func):
    """Decorator: only allow logged-in admins."""
    def wrapper(request, *args, **kwargs):
        if not request.session.get('admin_id'):
            messages.error(request, 'Please log in as admin.')
            return redirect('admin_login')
        return view_func(request, *args, **kwargs)
    return wrapper


@admin_required
def admin_dashboard(request):
    total_users = User.objects.exclude(role='super_admin').count()
    active_users = User.objects.exclude(role='super_admin').filter(is_active=True).count()
    inactive_users = User.objects.exclude(role='super_admin').filter(is_active=False).count()
    recent_logs = AuditLog.objects.select_related('user').order_by('-timestamp')[:15]
    return render(request, 'admin/dashboard.html', {
        'total_users': total_users,
        'active_users': active_users,
        'inactive_users': inactive_users,
        'recent_logs': recent_logs,
    })


@admin_required
def user_list(request):
    users = User.objects.exclude(role='super_admin').order_by('-created_at')
    return render(request, 'admin/user_list.html', {'users': users})


@admin_required
def create_user(request):
    if request.method == 'GET':
        role_choices = User.ROLE_CHOICES
        branches = Branch.objects.all()
        return render(request, 'admin/create_user.html', {'role_choices': role_choices, 'branches': branches})

    ip = get_client_ip(request)
    admin_user = User.objects.get(id=request.session['admin_id'])

    # Collect form data
    full_name = request.POST.get('full_name', '').strip()
    employee_id = request.POST.get('employee_id', '').strip()
    email = request.POST.get('email', '').strip()
    phone_number = request.POST.get('phone_number', '').strip()
    branch_id = request.POST.get('branch', '').strip()
    role = request.POST.get('role', 'high_privilege_user').strip()
    username = request.POST.get('username', '').strip()

    # Validate
    errors = []
    if not full_name:
        errors.append('Full name is required.')
    if not employee_id:
        errors.append('Employee ID is required.')
    if not email:
        errors.append('Email is required.')
    if not username:
        errors.append('Username is required.')
    if User.objects.filter(username=username).exists():
        errors.append(f'Username "{username}" is already taken.')
    if User.objects.filter(email=email).exists():
        errors.append(f'Email "{email}" is already registered.')
    if User.objects.filter(employee_id=employee_id).exists():
        errors.append(f'Employee ID "{employee_id}" is already in use.')

    if errors:
        for e in errors:
            messages.error(request, e)
        return render(request, 'admin/create_user.html', {
            'role_choices': User.ROLE_CHOICES,
            'branches': Branch.objects.all(),
            'form_data': request.POST,
        })

    branch = Branch.objects.filter(id=branch_id).first() if branch_id else None

    temp_password = generate_temp_password()
    new_user = User.objects.create_user(
        username=username,
        email=email,
        password=temp_password,
        full_name=full_name,
        employee_id=employee_id,
        phone_number=phone_number,
        branch=branch,
        role=role,
        must_change_password=True,
        created_by=admin_user,
    )

    import uuid
    reg_code = "REG-" + str(uuid.uuid4()).upper()[:8]
    from datetime import timedelta
    DeviceRegistrationCode.objects.create(
        user=new_user,
        code=reg_code,
        created_by=admin_user,
        expires_at=timezone.now() + timedelta(days=7)
    )

    # Email credentials to new user
    subject = 'Welcome to SecurePortal – Your Account Credentials'
    body = (
        f"Dear {full_name},\n\n"
        f"Your account has been created on SecurePortal.\n\n"
        f"Login URL: http://127.0.0.1:8000/user-login/\n"
        f"Username: {username}\n"
        f"Temporary Password: {temp_password}\n"
        f"Device Registration Code: {reg_code}\n\n"
        f"You will be required to change your password on first login.\n"
        f"Keep these credentials confidential.\n\n"
        f"SecurePortal Administrator"
    )
    try:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [email])
    except Exception:
        pass

    log_event(admin_user, 'account_created', f'Created user {username} ({employee_id})', ip)
    messages.success(request, f'User account for {full_name} created successfully. Credentials sent to {email}.')
    return redirect('user_list')


@admin_required
def toggle_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    admin_user = User.objects.get(id=request.session['admin_id'])
    ip = get_client_ip(request)

    user.is_active = not user.is_active
    user.save()

    action = 'account_activated' if user.is_active else 'account_deactivated'
    log_event(admin_user, action, f'{"Activated" if user.is_active else "Deactivated"} {user.username}', ip)
    messages.success(request, f'User {user.username} has been {"activated" if user.is_active else "deactivated"}.')
    return redirect('user_list')


@admin_required
def reset_user_password(request, user_id):
    user = get_object_or_404(User, id=user_id)
    admin_user = User.objects.get(id=request.session['admin_id'])
    ip = get_client_ip(request)

    temp_password = generate_temp_password()
    user.set_password(temp_password)
    user.must_change_password = True
    user.failed_login_count = 0
    user.locked_until = None
    user.save()

    subject = 'SecurePortal: Your Password Has Been Reset'
    body = (
        f"Dear {user.full_name},\n\n"
        f"Your password has been reset by an administrator.\n\n"
        f"Username: {user.username}\n"
        f"New Temporary Password: {temp_password}\n\n"
        f"You will be required to set a new password on next login.\n\n"
        f"SecurePortal Administrator"
    )
    try:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [user.email])
    except Exception:
        pass

    log_event(admin_user, 'password_changed', f'Admin reset password for {user.username}', ip)
    messages.success(request, f'Password for {user.username} has been reset and sent to their email.')
    return redirect('user_list')


@admin_required
def audit_log_view(request):
    logs = AuditLog.objects.select_related('user').order_by('-timestamp')[:200]
    return render(request, 'admin/audit_log.html', {'logs': logs})
