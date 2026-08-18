import random
import string
import secrets
from datetime import timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.views.decorators.http import require_http_methods
from django.contrib.auth import get_user_model

from authentication.models import (
    AuthenticationFlow, OTPRecord, TokenRecord,
    PasswordResetRecord, AuditLog
)

User = get_user_model()


def get_client_ip(request):
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded:
        return x_forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def log_event(user, action, description, ip, success=True, auth_flow=None):
    AuditLog.objects.create(
        user=user,
        action_type=action,
        description=description,
        ip_address=ip,
        success=success,
        auth_flow=auth_flow,
    )


def generate_otp():
    return ''.join(random.choices(string.digits, k=6))


def generate_temp_password(length=12):
    alphabet = string.ascii_letters + string.digits + '!@#$%'
    return ''.join(secrets.choice(alphabet) for _ in range(length))


# ─── Landing Page ─────────────────────────────────────────────────────────────
def landing(request):
    return render(request, 'landing.html')


# ─── Login Choice ─────────────────────────────────────────────────────────────
def login_choice(request):
    return render(request, 'login_choice.html')


# ─── Admin Login ──────────────────────────────────────────────────────────────
@require_http_methods(['GET', 'POST'])
def admin_login(request):
    if request.method == 'GET':
        return render(request, 'admin_login.html')

    username = request.POST.get('username', '').strip()
    password = request.POST.get('password', '').strip()
    ip = get_client_ip(request)

    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        log_event(None, 'login_failed', f'Admin login: unknown username "{username}"', ip, False)
        messages.error(request, 'Invalid credentials.')
        return render(request, 'admin_login.html')

    if user.role != 'super_admin':
        log_event(user, 'login_failed', 'Non-admin tried admin login', ip, False)
        messages.error(request, 'Access denied.')
        return render(request, 'admin_login.html')

    if not user.is_active:
        messages.error(request, 'Account is disabled.')
        return render(request, 'admin_login.html')

    if user.is_account_locked():
        messages.error(request, 'Account is temporarily locked. Try again later.')
        return render(request, 'admin_login.html')

    if not user.check_password(password):
        user.failed_login_count += 1
        if user.failed_login_count >= 5:
            user.locked_until = timezone.now() + timedelta(minutes=15)
            log_event(user, 'account_locked', 'Admin account locked after 5 failed attempts', ip, False)
        user.save()
        log_event(user, 'login_failed', 'Admin wrong password', ip, False)
        messages.error(request, 'Invalid credentials.')
        return render(request, 'admin_login.html')

    # Success
    user.failed_login_count = 0
    user.locked_until = None
    user.save()
    request.session['admin_id'] = str(user.id)
    request.session['admin_username'] = user.username
    request.session['admin_role'] = user.role
    log_event(user, 'login_success', 'Admin login successful', ip)
    return redirect('admin_dashboard')


def admin_logout(request):
    if 'admin_id' in request.session:
        try:
            user = User.objects.get(id=request.session['admin_id'])
            log_event(user, 'logout', 'Admin logout', get_client_ip(request))
        except Exception:
            pass
    request.session.flush()
    return redirect('landing')


# ─── User Login Step 1: Credentials ──────────────────────────────────────────
@require_http_methods(['GET', 'POST'])
def user_login(request):
    if request.method == 'GET':
        return render(request, 'user_login.html')

    username = request.POST.get('username', '').strip()
    password = request.POST.get('password', '').strip()
    ip = get_client_ip(request)

    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        log_event(None, 'login_failed', f'Unknown username: {username}', ip, False)
        messages.error(request, 'Invalid credentials.')
        return render(request, 'user_login.html')

    if user.role == 'super_admin':
        messages.error(request, 'Please use Admin Login for administrator accounts.')
        return render(request, 'user_login.html')

    if not user.is_active:
        log_event(user, 'login_failed', 'Inactive account login attempt', ip, False)
        messages.error(request, 'Your account has been deactivated. Contact your administrator.')
        return render(request, 'user_login.html')

    if user.is_account_locked():
        remaining = int((user.locked_until - timezone.now()).total_seconds())
        messages.error(request, f'Account is locked. Try again in {remaining} seconds.')
        return render(request, 'user_login.html')

    if not user.check_password(password):
        user.failed_login_count += 1
        if user.failed_login_count >= 5:
            user.locked_until = timezone.now() + timedelta(minutes=15)
            log_event(user, 'account_locked', 'User locked after 5 failed logins', ip, False)
        user.save()
        log_event(user, 'login_failed', 'Wrong password', ip, False)
        messages.error(request, 'Invalid credentials.')
        return render(request, 'user_login.html')

    # Check if first login (must change password)
    if user.must_change_password:
        user.failed_login_count = 0
        user.locked_until = None
        user.save()
        request.session['force_change_user_id'] = str(user.id)
        return redirect('force_change_password')

    # Credentials valid – generate and send OTP
    user.failed_login_count = 0
    user.locked_until = None
    user.save()

    flow = AuthenticationFlow.objects.create(user=user, ip_address=ip)
    _send_otp(user, flow, ip)

    request.session['auth_flow_id'] = str(flow.auth_flow_id)
    log_event(user, 'login_attempt', 'Credentials accepted, OTP sent', ip, True, flow)
    return redirect('verify_otp')


def _send_otp(user, flow, ip, otp_type='login'):
    """Generate OTP, store hashed, send email."""
    # Invalidate any existing active OTPs for this flow
    OTPRecord.objects.filter(
        auth_flow=flow, otp_type=otp_type, is_verified=False, is_used=False
    ).update(is_used=True)

    otp = generate_otp()
    expiry = timezone.now() + timedelta(minutes=4)
    OTPRecord.objects.create(
        auth_flow=flow,
        user=user,
        otp_hash=OTPRecord.hash_otp(otp),
        otp_type=otp_type,
        expires_at=expiry,
    )
    flow.status = 'otp_sent'
    flow.save()

    subject = 'SecurePortal: Your OTP Verification Code'
    body = (
        f"Dear {user.full_name},\n\n"
        f"Your one-time password (OTP) for SecurePortal login is:\n\n"
        f"    {otp}\n\n"
        f"This code is valid for 4 minutes.\n"
        f"Do NOT share this code with anyone.\n\n"
        f"If you did not request this, contact IT Security immediately.\n\n"
        f"SecurePortal Security Team"
    )
    try:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [user.email])
        log_event(user, 'otp_sent', f'OTP sent to {user.email}', ip, True, flow)
    except Exception as e:
        log_event(user, 'otp_sent', f'OTP email failed: {e}', ip, False, flow)


# ─── Force Password Change ────────────────────────────────────────────────────
@require_http_methods(['GET', 'POST'])
def force_change_password(request):
    user_id = request.session.get('force_change_user_id')
    if not user_id:
        return redirect('user_login')

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return redirect('user_login')

    if request.method == 'GET':
        return render(request, 'force_change_password.html')

    pw1 = request.POST.get('new_password', '')
    pw2 = request.POST.get('confirm_password', '')
    ip = get_client_ip(request)

    if pw1 != pw2:
        messages.error(request, 'Passwords do not match.')
        return render(request, 'force_change_password.html')
    if len(pw1) < 8:
        messages.error(request, 'Password must be at least 8 characters.')
        return render(request, 'force_change_password.html')

    user.set_password(pw1)
    user.must_change_password = False
    user.save()
    del request.session['force_change_user_id']

    log_event(user, 'password_changed', 'First-login forced password change', ip)
    messages.success(request, 'Password updated. Please log in with your new password.')
    return redirect('user_login')


# ─── OTP Verification ────────────────────────────────────────────────────────
@require_http_methods(['GET', 'POST'])
def verify_otp(request):
    flow_id = request.session.get('auth_flow_id')
    if not flow_id:
        return redirect('user_login')

    try:
        flow = AuthenticationFlow.objects.get(auth_flow_id=flow_id)
    except AuthenticationFlow.DoesNotExist:
        return redirect('user_login')

    if flow.is_expired():
        messages.error(request, 'Session expired. Please log in again.')
        return redirect('user_login')

    ip = get_client_ip(request)

    otp_rec = OTPRecord.objects.filter(
        auth_flow=flow, otp_type='login', is_verified=False, is_used=False
    ).order_by('-created_at').first()

    if not otp_rec:
        messages.error(request, 'No active OTP found. Please resend.')
        return render(request, 'verify_otp.html', {'email_hint': _mask_email(flow.user.email)})

    remaining_seconds = int((otp_rec.expires_at - timezone.now()).total_seconds())
    otp_expired = otp_rec.is_expired() or remaining_seconds <= 0

    if request.method == 'GET':
        lockout_seconds = 0
        if otp_rec.is_locked():
            lockout_seconds = int((otp_rec.locked_until - timezone.now()).total_seconds())

        return render(request, 'verify_otp.html', {
            'email_hint': _mask_email(flow.user.email),
            'lockout_seconds': lockout_seconds,
            'otp_attempts_left': max(0, 3 - otp_rec.attempts),
            'remaining_seconds': max(0, remaining_seconds),
            'otp_expired': otp_expired,
        })

    # POST
    otp_input = request.POST.get('otp', '').strip()

    if otp_rec.is_locked():
        remaining = int((otp_rec.locked_until - timezone.now()).total_seconds())
        messages.error(request, f'Too many attempts. Locked for {remaining} seconds.')
        return redirect('user_login')

    if otp_expired:
        messages.error(request, 'OTP has expired. Please resend.')
        return render(request, 'verify_otp.html', {
            'email_hint': _mask_email(flow.user.email),
            'otp_expired': True,
            'remaining_seconds': 0,
        })

    otp_rec.attempts += 1

    if not otp_rec.verify(otp_input):
        if otp_rec.attempts >= 3:
            otp_rec.locked_until = timezone.now() + timedelta(minutes=2)
            otp_rec.save()
            log_event(flow.user, 'otp_failed', f'OTP locked after 3 failures', ip, False, flow)
            messages.error(request, 'Too many incorrect attempts. You must restart login.')
            return redirect('user_login')
        otp_rec.save()
        log_event(flow.user, 'otp_failed', f'Wrong OTP attempt {otp_rec.attempts}', ip, False, flow)
        remaining = 3 - otp_rec.attempts
        # Recalculate remaining seconds for the error page render
        remaining_seconds = int((otp_rec.expires_at - timezone.now()).total_seconds())
        messages.error(request, f'Incorrect OTP. {remaining} attempt(s) remaining.')
        return render(request, 'verify_otp.html', {
            'email_hint': _mask_email(flow.user.email),
            'otp_attempts_left': remaining,
            'remaining_seconds': max(0, remaining_seconds),
        })

    # OTP correct
    otp_rec.is_verified = True
    otp_rec.save()
    flow.otp_verified = True
    flow.status = 'otp_verified'
    flow.save()

    log_event(flow.user, 'otp_verified', 'OTP verified successfully', ip, True, flow)
    return redirect('verify_token')


def resend_otp(request):
    flow_id = request.session.get('auth_flow_id')
    if not flow_id:
        return redirect('user_login')
    try:
        flow = AuthenticationFlow.objects.get(auth_flow_id=flow_id)
    except AuthenticationFlow.DoesNotExist:
        return redirect('user_login')

    if flow.is_expired():
        messages.error(request, 'Session expired.')
        return redirect('user_login')

    # Invalidate old OTPs
    OTPRecord.objects.filter(auth_flow=flow, otp_type='login', is_verified=False).update(is_used=True)

    ip = get_client_ip(request)
    # Get latest resend count
    last = OTPRecord.objects.filter(auth_flow=flow, otp_type='login').order_by('-created_at').first()
    resend_count = (last.resend_count + 1) if last else 1

    otp = generate_otp()
    expiry = timezone.now() + timedelta(minutes=4)
    OTPRecord.objects.create(
        auth_flow=flow,
        user=flow.user,
        otp_hash=OTPRecord.hash_otp(otp),
        otp_type='login',
        expires_at=expiry,
        resend_count=resend_count,
    )

    subject = 'SecurePortal: New OTP Verification Code'
    body = (
        f"Dear {flow.user.full_name},\n\n"
        f"Your new OTP is:\n\n    {otp}\n\n"
        f"Valid for 4 minutes. The previous code is now invalid.\n\n"
        f"SecurePortal Security Team"
    )
    try:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [flow.user.email])
        log_event(flow.user, 'otp_resend', f'OTP resent (count={resend_count})', ip, True, flow)
        messages.success(request, 'A new OTP has been sent to your email.')
    except Exception as e:
        log_event(flow.user, 'otp_resend', f'Resend failed: {e}', ip, False, flow)
        messages.error(request, 'Failed to resend OTP. Please try again.')

    return redirect('verify_otp')


def _mask_email(email):
    parts = email.split('@')
    name = parts[0]
    masked = name[:2] + '*' * (len(name) - 2) if len(name) > 2 else name
    return f"{masked}@{parts[1]}"


# ─── Token Verification ───────────────────────────────────────────────────────
@require_http_methods(['GET', 'POST'])
def verify_token(request):
    flow_id = request.session.get('auth_flow_id')
    if not flow_id:
        return redirect('user_login')

    try:
        flow = AuthenticationFlow.objects.get(auth_flow_id=flow_id)
    except AuthenticationFlow.DoesNotExist:
        return redirect('user_login')

    if not flow.otp_verified:
        return redirect('verify_otp')

    ip = get_client_ip(request)

    # Retrieve OTP record
    otp_rec = OTPRecord.objects.filter(
        auth_flow=flow, otp_type='login', is_verified=True
    ).order_by('-created_at').first()

    if not otp_rec:
        messages.error(request, 'Invalid authentication state. Please restart.')
        return redirect('user_login')

    token_rec = getattr(flow, 'token_record', None)

    # Reset attempts if lockout expired
    if token_rec and token_rec.locked_until and timezone.now() >= token_rec.locked_until:
        token_rec.attempts = 0
        token_rec.locked_until = None
        token_rec.save()

    # Session expiration check (synchronization check)
    is_session_expired = (
        flow.is_expired() or
        flow.status == 'expired' or
        flow.invalidated_at is not None or
        otp_rec.is_expired() or
        (token_rec and token_rec.is_expired())
    )

    if is_session_expired:
        flow.invalidate()
        request.session.pop('auth_flow_id', None)
        messages.error(request, 'Session expired. Please restart the login process.')
        return redirect('user_login')

    if request.method == 'GET':
        if token_rec and token_rec.is_locked():
            lockout_remaining = int((token_rec.locked_until - timezone.now()).total_seconds())
        else:
            lockout_remaining = 0

        # Calculate remaining seconds for the 4-minute verification window
        remaining_seconds = int((otp_rec.expires_at - timezone.now()).total_seconds())
        if token_rec:
            token_rem = int((token_rec.expires_at - timezone.now()).total_seconds())
            remaining_seconds = min(remaining_seconds, token_rem)
        remaining_seconds = max(0, remaining_seconds)

        attempts_left = max(0, 3 - token_rec.attempts) if token_rec else 3

        return render(request, 'verify_token.html', {
            'auth_flow_id': str(flow.auth_flow_id),
            'lockout_seconds': lockout_remaining,
            'remaining_seconds': remaining_seconds,
            'attempts_left': attempts_left,
        })

    # POST
    token_input = request.POST.get('token', '').strip()

    try:
        token_rec = flow.token_record
    except TokenRecord.DoesNotExist:
        # Calculate remaining seconds for the 4-minute verification window
        remaining_seconds = int((otp_rec.expires_at - timezone.now()).total_seconds())
        remaining_seconds = max(0, remaining_seconds)
        messages.error(request, 'No token has been generated yet. Please use the desktop app first.')
        return render(request, 'verify_token.html', {
            'auth_flow_id': str(flow.auth_flow_id),
            'remaining_seconds': remaining_seconds,
            'attempts_left': 3,
        })

    # Double check if lockout expired right before processing (in case user reloaded or waited)
    if token_rec.locked_until and timezone.now() >= token_rec.locked_until:
        token_rec.attempts = 0
        token_rec.locked_until = None
        token_rec.save()

    if token_rec.is_used:
        messages.error(request, 'This token has already been used.')
        return redirect('user_login')

    if token_rec.is_locked():
        remaining = int((token_rec.locked_until - timezone.now()).total_seconds())
        # Calculate remaining seconds for the 4-minute verification window
        remaining_seconds = int((otp_rec.expires_at - timezone.now()).total_seconds())
        if token_rec:
            token_rem = int((token_rec.expires_at - timezone.now()).total_seconds())
            remaining_seconds = min(remaining_seconds, token_rem)
        remaining_seconds = max(0, remaining_seconds)

        messages.error(request, f'Too many attempts. Wait {remaining} seconds.')
        return render(request, 'verify_token.html', {
            'auth_flow_id': str(flow.auth_flow_id),
            'lockout_seconds': remaining,
            'remaining_seconds': remaining_seconds,
        })

    token_rec.attempts += 1

    if not token_rec.verify(token_input):
        # Calculate remaining seconds for the 4-minute verification window
        remaining_seconds = int((otp_rec.expires_at - timezone.now()).total_seconds())
        if token_rec:
            token_rem = int((token_rec.expires_at - timezone.now()).total_seconds())
            remaining_seconds = min(remaining_seconds, token_rem)
        remaining_seconds = max(0, remaining_seconds)

        if token_rec.attempts >= 3:
            token_rec.locked_until = timezone.now() + timedelta(minutes=1)
            token_rec.save()
            log_event(flow.user, 'token_failed', 'Token locked after 3 failures', ip, False, flow)
            messages.error(request, 'Invalid Token. Too many incorrect attempts. Locked for 1 minute.')
            return render(request, 'verify_token.html', {
                'auth_flow_id': str(flow.auth_flow_id),
                'lockout_seconds': 60,
                'remaining_seconds': remaining_seconds,
            })

        token_rec.save()
        log_event(flow.user, 'token_failed', f'Wrong token attempt {token_rec.attempts}', ip, False, flow)
        remaining = 3 - token_rec.attempts
        messages.error(request, f'Invalid Token. {remaining} attempt(s) remaining.')
        return render(request, 'verify_token.html', {
            'auth_flow_id': str(flow.auth_flow_id),
            'attempts_left': remaining,
            'remaining_seconds': remaining_seconds,
        })

    # Token correct – login success
    token_rec.is_used = True
    token_rec.save()
    flow.token_verified = True
    flow.status = 'completed'
    flow.save()

    # Create user session
    user = flow.user
    request.session['user_id'] = str(user.id)
    request.session['user_username'] = user.username
    request.session['user_role'] = user.role
    request.session['user_full_name'] = user.full_name
    del request.session['auth_flow_id']

    log_event(user, 'login_success', 'Full layered auth completed', ip, True, flow)
    return redirect('user_dashboard')


# ─── Forgot Password ──────────────────────────────────────────────────────────
@require_http_methods(['GET', 'POST'])
def forgot_password(request):
    if request.method == 'GET':
        return render(request, 'forgot_password.html')

    email = request.POST.get('email', '').strip()
    ip = get_client_ip(request)

    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        # Don't reveal whether email exists
        messages.success(request, 'If that email is registered, a reset code has been sent.')
        return render(request, 'forgot_password.html')

    otp = generate_otp()
    expiry = timezone.now() + timedelta(minutes=1)
    PasswordResetRecord.objects.create(
        user=user,
        reset_otp_hash=PasswordResetRecord.hash_otp(otp),
        expires_at=expiry,
    )

    subject = 'SecurePortal: Password Reset Code'
    body = (
        f"Dear {user.full_name},\n\n"
        f"Your password reset code is:\n\n    {otp}\n\n"
        f"This code is valid for 1 minute only.\n"
        f"If you did not request this, contact IT Security.\n\n"
        f"SecurePortal Security Team"
    )
    try:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [user.email])
    except Exception:
        pass

    log_event(user, 'password_reset_request', 'Reset OTP sent', ip)
    request.session['reset_user_id'] = str(user.id)
    messages.success(request, 'A security code has been sent to your email.')
    return redirect('reset_otp_verify')


@require_http_methods(['GET', 'POST'])
def reset_otp_verify(request):
    user_id = request.session.get('reset_user_id')
    if not user_id:
        return redirect('forgot_password')

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return redirect('forgot_password')

    reset_rec = PasswordResetRecord.objects.filter(
        user=user, status='pending'
    ).order_by('-created_at').first()

    if not reset_rec:
        messages.error(request, 'No active reset request. Please try again.')
        return redirect('forgot_password')

    # Calculate remaining seconds for the OTP timeout
    remaining_seconds = int((reset_rec.expires_at - timezone.now()).total_seconds())

    if reset_rec.is_expired() or remaining_seconds <= 0:
        reset_rec.status = 'expired'
        reset_rec.save()
        messages.error(request, 'Reset code has expired. Please request a new one.')
        return redirect('forgot_password')

    if request.method == 'GET':
        return render(request, 'reset_otp_verify.html', {
            'email_hint': _mask_email(user.email),
            'remaining_seconds': max(0, remaining_seconds),
            'otp_attempts_left': max(0, 3 - reset_rec.attempts),
        })

    otp_input = request.POST.get('otp', '').strip()
    ip = get_client_ip(request)

    reset_rec.attempts += 1
    if not reset_rec.verify(otp_input):
        if reset_rec.attempts >= 3:
            reset_rec.status = 'failed'
            reset_rec.save()
            del request.session['reset_user_id']
            messages.error(request, 'Too many incorrect attempts. Please restart the reset process.')
            return redirect('forgot_password')
        reset_rec.save()
        remaining = 3 - reset_rec.attempts
        # Recalculate remaining seconds for the error page render
        remaining_seconds = int((reset_rec.expires_at - timezone.now()).total_seconds())
        messages.error(request, f'Incorrect code. {remaining} attempt(s) remaining.')
        return render(request, 'reset_otp_verify.html', {
            'email_hint': _mask_email(user.email),
            'remaining_seconds': max(0, remaining_seconds),
            'otp_attempts_left': remaining,
        })

    reset_rec.status = 'verified'
    reset_rec.save()
    request.session['reset_verified_user_id'] = str(user.id)
    return redirect('set_new_password')


@require_http_methods(['GET', 'POST'])
def set_new_password(request):
    user_id = request.session.get('reset_verified_user_id')
    if not user_id:
        return redirect('forgot_password')

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return redirect('forgot_password')

    if request.method == 'GET':
        return render(request, 'set_new_password.html')

    pw1 = request.POST.get('new_password', '')
    pw2 = request.POST.get('confirm_password', '')
    ip = get_client_ip(request)

    if pw1 != pw2:
        messages.error(request, 'Passwords do not match.')
        return render(request, 'set_new_password.html')
    if len(pw1) < 8:
        messages.error(request, 'Password must be at least 8 characters.')
        return render(request, 'set_new_password.html')

    user.set_password(pw1)
    user.must_change_password = False
    user.save()

    PasswordResetRecord.objects.filter(user=user, status='verified').update(status='completed')
    for key in ['reset_user_id', 'reset_verified_user_id']:
        request.session.pop(key, None)

    log_event(user, 'password_reset_complete', 'Password reset successful', ip)
    messages.success(request, 'Password reset successful. Please log in with your new password.')
    return redirect('user_login')


# ─── Logout ───────────────────────────────────────────────────────────────────
def user_logout(request):
    user_id = request.session.get('user_id')
    if user_id:
        try:
            user = User.objects.get(id=user_id)
            log_event(user, 'logout', 'User logout', get_client_ip(request))
        except Exception:
            pass
    request.session.flush()
    return redirect('landing')
