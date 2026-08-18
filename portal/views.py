from django.shortcuts import render, redirect
from django.contrib.auth import get_user_model
from authentication.models import AuditLog

User = get_user_model()

ROLE_MODULES = {
    'super_admin': ['dashboard', 'admin_portal'],
    'branch_admin': ['dashboard', 'reports', 'approvals', 'team', 'notifications', 'documents', 'access_logs'],
    'high_privilege_user': ['dashboard', 'operations', 'finance', 'compliance', 'notifications', 'documents'],
}

MODULE_META = {
    'dashboard': {'label': 'Dashboard Home', 'icon': 'bi-house-fill', 'color': 'primary'},
    'reports': {'label': 'Internal Reports', 'icon': 'bi-file-earmark-bar-graph-fill', 'color': 'info'},
    'approvals': {'label': 'Approval Queue', 'icon': 'bi-check-circle-fill', 'color': 'warning'},
    'team': {'label': 'Team Access', 'icon': 'bi-people-fill', 'color': 'secondary'},
    'notifications': {'label': 'Notifications', 'icon': 'bi-bell-fill', 'color': 'danger'},
    'documents': {'label': 'Confidential Documents', 'icon': 'bi-folder-lock-fill', 'color': 'success'},
    'operations': {'label': 'Operational Summary', 'icon': 'bi-diagram-3-fill', 'color': 'info'},
    'compliance': {'label': 'Compliance Notices', 'icon': 'bi-shield-fill-check', 'color': 'warning'},
    'audit_trail': {'label': 'Audit Trail', 'icon': 'bi-journal-text', 'color': 'secondary'},
    'finance': {'label': 'Finance Reports', 'icon': 'bi-currency-exchange', 'color': 'success'},
    'hr_records': {'label': 'HR Records', 'icon': 'bi-person-vcard-fill', 'color': 'info'},
    'onboarding': {'label': 'Onboarding Documents', 'icon': 'bi-person-plus-fill', 'color': 'primary'},
    'access_logs': {'label': 'Access Logs', 'icon': 'bi-clock-history', 'color': 'danger'},
    'admin_portal': {'label': 'Admin Portal', 'icon': 'bi-gear-fill', 'color': 'danger'},
}


def user_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.session.get('user_id'):
            return redirect('user_login')
        return view_func(request, *args, **kwargs)
    return wrapper


def get_user_context(request):
    user = User.objects.get(id=request.session['user_id'])
    role = user.role
    modules = ROLE_MODULES.get(role, ['dashboard'])
    module_data = [{'key': m, **MODULE_META[m]} for m in modules if m in MODULE_META]
    return user, module_data


@user_required
def user_dashboard(request):
    user, modules = get_user_context(request)
    recent_logs = AuditLog.objects.filter(user=user).order_by('-timestamp')[:10]
    return render(request, 'portal/dashboard.html', {
        'user': user,
        'modules': modules,
        'recent_logs': recent_logs,
        'active_module': 'dashboard',
    })


@user_required
def profile_view(request):
    user, modules = get_user_context(request)
    return render(request, 'portal/profile.html', {
        'user': user,
        'modules': modules,
        'active_module': 'profile',
    })


@user_required
def security_activity(request):
    user, modules = get_user_context(request)
    logs = AuditLog.objects.filter(user=user).order_by('-timestamp')[:50]
    return render(request, 'portal/security_activity.html', {
        'user': user,
        'modules': modules,
        'logs': logs,
        'active_module': 'access_logs',
    })


@user_required
def module_placeholder(request, module_key):
    user, modules = get_user_context(request)
    meta = MODULE_META.get(module_key, {'label': module_key, 'icon': 'bi-grid', 'color': 'primary'})
    return render(request, 'portal/module_placeholder.html', {
        'user': user,
        'modules': modules,
        'active_module': module_key,
        'module_meta': meta,
    })
