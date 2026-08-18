from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


from accounts.models import Branch

class Command(BaseCommand):
    help = 'Create the initial admin superuser account for SecurePortal'

    def handle(self, *args, **options):
        self.stdout.write('\n' + '═' * 50)
        self.stdout.write('  SecurePortal – Create Admin Account')
        self.stdout.write('═' * 50)

        if User.objects.filter(role='super_admin').exists():
            self.stdout.write(self.style.WARNING('An admin account already exists:'))
            for u in User.objects.filter(role='super_admin'):
                self.stdout.write(f'  Username: {u.username}  |  Email: {u.email}')
            self.stdout.write('')
            ans = input('Create another admin? (y/N): ').strip().lower()
            if ans != 'y':
                self.stdout.write('Cancelled.')
                return

        username = input('Admin username [admin]: ').strip() or 'admin'
        email = input('Admin email: ').strip()
        full_name = input('Full name [System Administrator]: ').strip() or 'System Administrator'
        employee_id = input('Employee ID [ADMIN-001]: ').strip() or 'ADMIN-001'
        branch_name = input('Branch [HQ]: ').strip() or 'HQ'

        import getpass
        while True:
            password = getpass.getpass('Password (min 8 chars): ')
            confirm  = getpass.getpass('Confirm password: ')
            if password != confirm:
                self.stdout.write(self.style.ERROR('Passwords do not match. Try again.'))
            elif len(password) < 8:
                self.stdout.write(self.style.ERROR('Password must be at least 8 characters.'))
            else:
                break

        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.ERROR(f'Username "{username}" is already taken.'))
            return
        if User.objects.filter(email=email).exists():
            self.stdout.write(self.style.ERROR(f'Email "{email}" is already registered.'))
            return

        branch, _ = Branch.objects.get_or_create(name=branch_name)

        admin = User.objects.create_superuser(
            username=username,
            email=email,
            password=password,
            full_name=full_name,
            employee_id=employee_id,
            branch=branch,
            role='super_admin',
            must_change_password=False,
        )

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'✓ Admin account created successfully!'))
        self.stdout.write(f'  Username: {admin.username}')
        self.stdout.write(f'  Email:    {admin.email}')
        self.stdout.write(f'  Role:     Administrator')
        self.stdout.write('')
        self.stdout.write('Login at: http://127.0.0.1:8000/admin-login/')
        self.stdout.write('═' * 50 + '\n')
