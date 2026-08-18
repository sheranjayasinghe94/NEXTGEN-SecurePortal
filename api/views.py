import secrets
import string
from datetime import timedelta

from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json

from authentication.models import (
    AuthenticationFlow, OTPRecord, TokenRecord, AuditLog,
    RegisteredDevice, DeviceRegistrationCode
)
from accounts.models import CustomUser


def _get_ip(request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    return xff.split(',')[0].strip() if xff else request.META.get('REMOTE_ADDR')


def _generate_token(length=10):
    alphabet = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

@csrf_exempt
@require_http_methods(['POST'])
def register_device(request):
    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({'success': False, 'error': 'Invalid format.'}, status=400)

    username = data.get('username', '').strip()
    registration_code = data.get('registration_code', '').strip()
    device_id = data.get('device_id', '').strip()
    machine_guid = data.get('machine_guid', '').strip()
    device_name = data.get('device_name', '').strip()
    windows_username = data.get('windows_username', '').strip()
    mac_address_hash = data.get('mac_address_hash', '').strip()

    if not all([username, registration_code, device_id, machine_guid, mac_address_hash]):
        return JsonResponse({'success': False, 'error': 'Missing required fields.'}, status=400)

    try:
        user = CustomUser.objects.get(username=username)
    except CustomUser.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Invalid user.'}, status=404)

    try:
        code_record = DeviceRegistrationCode.objects.get(code=registration_code, user=user)
        if code_record.is_used:
            return JsonResponse({'success': False, 'error': 'Registration code already used.'}, status=400)
        if code_record.is_expired():
            return JsonResponse({'success': False, 'error': 'Registration code expired.'}, status=400)
    except DeviceRegistrationCode.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Invalid registration code.'}, status=400)

    # Check if device already registered
    if RegisteredDevice.objects.filter(device_id=device_id).exists():
        return JsonResponse({'success': False, 'error': 'Device already registered.'}, status=400)

    RegisteredDevice.objects.create(
        user=user,
        device_id=device_id,
        machine_guid=machine_guid,
        device_name=device_name,
        windows_username=windows_username,
        mac_address_hash=mac_address_hash
    )
    code_record.is_used = True
    code_record.save()

    AuditLog.objects.create(
        user=user,
        action_type='device_registered',
        description=f'Device {device_name} registered successfully',
        ip_address=_get_ip(request),
        success=True
    )
    return JsonResponse({'success': True, 'message': 'Device registered successfully.'})


@csrf_exempt
@require_http_methods(['POST'])
def generate_token(request):
    """
    Desktop app calls this endpoint.
    Request JSON: { "auth_flow_id": "UUID", "otp": "123456" }
    Response JSON: { "success": bool, "token": str|null, "error": str|null, "expires_in_seconds": int|null }
    """
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, Exception):
        return JsonResponse({'success': False, 'error': 'Invalid request format.'}, status=400)

    auth_flow_id = data.get('auth_flow_id', '').strip()
    otp_input = data.get('otp', '').strip()
    device_id = data.get('device_id', '').strip()
    user_id = data.get('user_id', '').strip()
    ip = _get_ip(request)

    if not auth_flow_id or not otp_input or not device_id or not user_id:
        return JsonResponse({'success': False, 'error': 'auth_flow_id, otp, user_id, and device_id are required.'}, status=400)

    # Lookup authentication flow
    try:
        flow = AuthenticationFlow.objects.get(auth_flow_id=auth_flow_id)
    except AuthenticationFlow.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Invalid or expired session. Please restart login.'}, status=404)

    if flow.is_expired() or flow.status == 'expired' or flow.invalidated_at is not None:
        flow.invalidate()
        return JsonResponse({'success': False, 'error': 'Login session has expired. Please restart login.'}, status=400)

    if flow.status not in ('otp_verified',):
        return JsonResponse({'success': False, 'error': 'OTP not yet verified on website. Complete website OTP step first.'}, status=400)

    if str(flow.user.id) != user_id and flow.user.username != user_id:
        return JsonResponse({'success': False, 'error': 'User ID mismatch.'}, status=400)

    try:
        device = RegisteredDevice.objects.get(device_id=device_id, user=flow.user, is_active=True)
        device.last_used_at = timezone.now()
        device.save()
    except RegisteredDevice.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Unregistered or inactive device.'}, status=400)

    # Check if token already generated for this flow
    try:
        existing = flow.token_record
        if existing.is_used:
            return JsonResponse({'success': False, 'error': 'Token already used. Please restart login.'}, status=400)
        # Token already generated — return error (one per flow)
        return JsonResponse({'success': False, 'error': 'Token already generated for this session.'}, status=400)
    except TokenRecord.DoesNotExist:
        pass

    # Get the verified OTP record for this flow
    otp_rec = OTPRecord.objects.filter(
        auth_flow=flow,
        otp_type='login',
        is_verified=True,
        is_used=False,
    ).order_by('-created_at').first()

    if not otp_rec:
        return JsonResponse({'success': False, 'error': 'No verified OTP found. Complete website OTP verification first.'}, status=400)

    # Check desktop generator lockout on OTP record
    if otp_rec.is_locked():
        remaining = int((otp_rec.locked_until - timezone.now()).total_seconds())
        return JsonResponse({
            'success': False,
            'error': f'Too many incorrect OTP attempts. Generator locked for {remaining} seconds.',
            'locked_seconds': remaining,
        }, status=429)

    # Check OTP expiry (OTP is valid 4 min from when it was created)
    if otp_rec.is_expired():
        flow.invalidate()
        return JsonResponse({'success': False, 'error': 'OTP has expired. Please restart login.'}, status=400)

    # Validate OTP
    # We track desktop attempts separately via a dedicated counter
    # We use a separate field: store desktop attempts in a new attribute on OTP
    # Since we don't have a separate desktop_attempts field, we use a session-less approach:
    # We store desktop attempt count in OTPRecord.attempts (already used for web verification).
    # Better: store in a separate way — let's track via a simple in-model bump
    # using the resend_count as desktop attempt counter (repurposed here).
    # Actually: let's add proper tracking. We'll create a new field via a workaround—
    # use a dedicated token-generation attempt model or simple JSON in description.
    # Simplest correct approach: store desktop_attempts on the OTP record.
    # We'll get the current desktop attempts from the otp_rec by checking attempts_desktop
    # Since we can't add a migration right now, we use a lightweight approach:
    # store desktop attempt info in OTPRecord notes via a dedicated separate record.
    
    # Track desktop attempts per flow using a simple counter stored in flow status extras
    # We'll use a helper OTPRecord queryset trick: all failed desktop attempts are logged
    desktop_failures = AuditLog.objects.filter(
        auth_flow=flow,
        action_type='token_failed',
        success=False,
    ).count()

    if desktop_failures >= 5:
        # Check if the 5-minute block is still in effect
        last_failure = AuditLog.objects.filter(
            auth_flow=flow,
            action_type='token_failed',
            success=False,
        ).order_by('-timestamp').first()

        if last_failure:
            block_until = last_failure.timestamp + timedelta(minutes=5)
            if timezone.now() < block_until:
                remaining = int((block_until - timezone.now()).total_seconds())
                return JsonResponse({
                    'success': False,
                    'error': f'Generator blocked. Too many wrong OTP attempts. Wait {remaining} seconds.',
                    'locked_seconds': remaining,
                }, status=429)

    # Verify OTP
    if not otp_rec.verify(otp_input):
        AuditLog.objects.create(
            user=flow.user,
            action_type='token_failed',
            description=f'Desktop: wrong OTP attempt (failure #{desktop_failures + 1})',
            ip_address=ip,
            success=False,
            auth_flow=flow,
        )
        failures_after = desktop_failures + 1
        if failures_after >= 5:
            return JsonResponse({
                'success': False,
                'error': 'Generator blocked for 5 minutes due to 5 incorrect OTP attempts.',
                'locked_seconds': 300,
            }, status=429)
        remaining_attempts = 5 - failures_after
        return JsonResponse({
            'success': False,
            'error': f'Incorrect OTP. {remaining_attempts} attempt(s) remaining before generator lock.',
        }, status=400)

    # OTP valid — generate token
    raw_token = _generate_token(10)
    token_expiry = timezone.now() + timedelta(minutes=4)
    TokenRecord.objects.create(
        auth_flow=flow,
        user=flow.user,
        token_hash=TokenRecord.hash_token(raw_token),
        expires_at=token_expiry,
    )

    # Mark OTP as used for desktop generation
    otp_rec.is_used = True
    otp_rec.save()

    flow.token_generated = True
    flow.status = 'token_generated'
    flow.save()

    AuditLog.objects.create(
        user=flow.user,
        action_type='token_generated',
        description='Login token generated via desktop app',
        ip_address=ip,
        success=True,
        auth_flow=flow,
    )

    return JsonResponse({
        'success': True,
        'token': raw_token,
        'expires_in_seconds': 240,
        'message': 'Token generated. Enter it on the SecurePortal website within 4 minutes.',
    })
