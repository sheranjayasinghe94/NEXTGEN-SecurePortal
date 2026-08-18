# SecurePortal – Secure Token-Based Multi-Factor Authentication System

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Django 6.0+](https://img.shields.io/badge/Django-6.0+-darkgreen.svg)](https://www.djangoproject.com/)
[![PostgreSQL 15+](https://img.shields.io/badge/PostgreSQL-15+-336791.svg)](https://www.postgresql.org/)

> A production-ready enterprise authentication system implementing three-tier security validation with hardware token support, real-time audit logging, and role-based access control (RBAC). Designed for corporate environments requiring high-security user authentication and access management.

## 🔒 Security Features

### Multi-Factor Authentication (MFA)
SecurePortal enforces a mandatory **three-stage authentication flow** for all high-privilege users:

1. **Credentials Validation** 🔑
   - Username + Password authentication
   - Passwords hashed with **Argon2** (NIST-recommended)
   - Configurable password complexity policies (min 8 chars, uppercase, numbers, special chars)

2. **Email-based OTP Verification** 📧
   - Time-limited 6-digit one-time password (OTP)
   - 4-minute validity window
   - Session-bound validation (tied to specific login attempt)
   - Rate-limited to prevent brute-force attacks

3. **Hardware/Desktop Token Validation** 🖥️
   - Single-use token generation via C# Desktop Token Generator app
   - Context-bound tokens (bound to session & IP)
   - Desktop app communicates via secure API endpoints

### Access Control & Auditing
- **Role-Based Access Control (RBAC)**: Super Admin, Branch Admin, High-Privilege User roles
- **Audit Logging**: Complete audit trail of all authentication attempts and user actions
- **Session Management**: Automatic session expiration (1 hour default)
- **Security Headers**: XSS protection, CSRF tokens, Clickjacking defense
- **Strike-Based Lockout Policies**: Automatic account lockout after failed attempts

## 📋 System Requirements

### Backend
- **Python**: 3.10 or higher
- **PostgreSQL**: 15 or higher
- **pip**: Python package manager

### Desktop Token Generator
- **.NET**: 6 or higher
- **Windows**: 7 or higher (for desktop app)

### Optional
- **Node.js**: For future SPA frontend extensions

## 🚀 Quick Start

### Step 1: Clone & Setup Repository

```bash
# Clone the repository
git clone https://github.com/yourusername/SecurePortal.git
cd SecurePortal

# Create Python virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On Linux/Mac:
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Configure Environment Variables

```bash
# Create .env file from template
copy .env.example .env
# On Linux/Mac: cp .env.example .env

# Edit .env with your configuration
# Replace placeholder values with your actual settings:
# - SECRET_KEY (generate new one: python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")
# - Database credentials
# - Email/SMTP settings
```

**Important**: Never commit `.env` to version control!

### Step 3: Database Setup

#### Option A: Automated Setup (Windows)
```cmd
# Run the database setup script
setup_db.bat
# When prompted, enter your PostgreSQL superuser password
```

#### Option B: Manual Setup
```sql
-- Connect to PostgreSQL as superuser
psql -U postgres

-- Create user and database
CREATE USER corp_user WITH PASSWORD 'your-secure-password';
CREATE DATABASE corp_portal_db OWNER corp_user;
GRANT ALL PRIVILEGES ON DATABASE corp_portal_db TO corp_user;
GRANT ALL PRIVILEGES ON SCHEMA public TO corp_portal_db TO corp_user;
```

### Step 4: Initialize Django Database

```bash
# Apply migrations
python manage.py migrate

# Create superuser (admin account)
python manage.py create_admin
# Follow the interactive prompts to set up your first admin account
```

### Step 5: Run Development Server

```bash
# Start Django development server
python manage.py runserver

# Server runs at: http://127.0.0.1:8000/
```

### Step 6: Setup Desktop Token Generator

```bash
# Navigate to Desktop Token Generator
cd DesktopTokenGenerator

# Run with .NET CLI
dotnet run

# Or open in Visual Studio and run directly
```

Visit `http://localhost:8000/` in your browser to access the portal.

---

## 🏗️ Project Architecture

### Directory Structure

```
SecurePortal/
├── accounts/              # User management & authentication
│   ├── models.py         # CustomUser, Branch models
│   ├── views.py          # User-related views
│   ├── management/       # Custom Django commands
│   │   └── commands/
│   │       └── create_admin.py
│   └── migrations/       # Database migrations
│
├── authentication/        # MFA & Token validation
│   ├── models.py         # OTP, DeviceRegistration models
│   ├── views.py          # OTP verification, Token validation
│   └── migrations/       # Database migrations
│
├── portal/               # Main portal dashboard & features
│   ├── models.py         # Portal-specific data models
│   ├── views.py          # Dashboard, profiles, security activity
│   └── migrations/       # Database migrations
│
├── api/                  # REST API for Desktop Token Generator
│   ├── views.py          # API endpoints
│   ├── urls.py           # API route definitions
│   └── serializers.py    # Data serialization
│
├── corp_portal/          # Django project settings
│   ├── settings.py       # Configuration (environment-based)
│   ├── urls.py           # URL routing
│   ├── wsgi.py           # WSGI application
│   └── asgi.py           # ASGI application
│
├── DesktopTokenGenerator/ # C# .NET 6 Desktop Application
│   ├── MainForm.cs       # UI implementation
│   ├── ApiService.cs     # Backend API communication
│   ├── DesktopTokenGenerator.csproj
│   └── bin/obj/          # Build output
│
├── templates/            # HTML templates
│   ├── admin/            # Admin portal templates
│   ├── portal/           # User portal templates
│   └── *.html            # Authentication templates
│
├── static/               # CSS, JS, images
│   ├── css/style.css
│   └── js/
│
├── .env.example          # Environment template (COPY THIS!)
├── .gitignore            # Git ignore rules
├── requirements.txt      # Python dependencies
├── setup_db.bat          # Database setup script
├── manage.py             # Django management script
└── README.md             # This file
```

### Technology Stack

**Backend**
- **Django 6.0+**: Web framework
- **PostgreSQL**: Database
- **Django REST Framework**: API framework
- **Argon2-cffi**: Password hashing
- **django-cors-headers**: CORS support

**Desktop App**
- **.NET 6**: Application framework
- **Windows Forms**: Desktop UI

**Frontend**
- **HTML5/CSS3**: Responsive design
- **Vanilla JavaScript**: Interactive features

---

## 🔐 Configuration Guide

### Email / SMTP Setup

#### Gmail with App Password
1. Enable 2-Step Verification in Google Account
2. Generate App Password at: https://myaccount.google.com/apppasswords
3. Add to `.env`:
   ```env
   EMAIL_HOST=smtp.gmail.com
   EMAIL_PORT=587
   EMAIL_USE_TLS=True
   EMAIL_HOST_USER=your-email@gmail.com
   EMAIL_HOST_PASSWORD=your-16-digit-app-password
   ```

#### Alternative Email Providers
- **Office 365**: smtp.office365.com (port 587)
- **SendGrid**: smtp.sendgrid.net (port 587)
- **AWS SES**: email-smtp.region.amazonaws.com (port 587)

### Production Deployment

**Before deploying to production:**

1. **Security Settings**
   ```env
   DEBUG=False
   ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
   SECRET_KEY=<generate-new-secure-key>
   SESSION_COOKIE_SECURE=True
   CSRF_COOKIE_SECURE=True
   ```

2. **Use HTTPS**
   - Install SSL certificate
   - Set `SESSION_COOKIE_SECURE=True`
   - Set `CSRF_COOKIE_SECURE=True`

3. **Database Security**
   - Use strong, random passwords
   - Restrict database access by IP
   - Enable PostgreSQL SSL connections

4. **Gunicorn + Nginx Setup**
   ```bash
   pip install gunicorn
   gunicorn corp_portal.wsgi:application --bind 0.0.0.0:8000
   ```

5. **Environment Management**
   - Use `.env` file (never commit to repo)
   - Consider using `.env` management tools: python-dotenv, django-environ
   - Store secrets securely (AWS Secrets Manager, HashiCorp Vault)

---

## 👥 User Roles & Permissions

| Role | Capabilities |
|------|-------------|
| **Super Admin** | Full system access, create users, manage branches, view audit logs |
| **Branch Admin** | Manage users in assigned branch, view branch-specific audit logs |
| **High-Privilege User** | Access portal features, view own security activity |

---

## 📊 Database Schema

### Core Models

**CustomUser**
- Unique username, email, employee ID
- Role-based access control
- Account status tracking
- Audit trail

**Branch**
- Organization branch/location
- User assignment

**OTP** (One-Time Password)
- Session-bound 6-digit codes
- Expiration timestamps
- Validation attempts

**DeviceRegistration**
- Desktop token generator registration
- Device identification
- Token history

**AuditLog**
- Complete authentication audit trail
- User actions logging
- IP address & timestamp tracking

---

## 🧪 Testing

### Run Tests
```bash
# Run all tests
python manage.py test

# Run specific app tests
python manage.py test accounts
python manage.py test authentication
python manage.py test portal
python manage.py test api

# Run with coverage
pip install coverage
coverage run --source='.' manage.py test
coverage report
```

### Manual Testing Checklist
- [ ] User registration (admin-provisioned only)
- [ ] Login flow with all three MFA stages
- [ ] OTP generation and validation
- [ ] Token generator app communication
- [ ] Audit log recording
- [ ] Session expiration
- [ ] Password reset flow
- [ ] Role-based access control

---

## 🛠️ Development & Contributing

### Install Development Dependencies
```bash
pip install -r requirements-dev.txt  # If provided
pip install black flake8 pytest django-debug-toolbar
```

### Code Style
- Follow PEP 8 conventions
- Use Black for code formatting
- Use Flake8 for linting

### Git Workflow
1. Create feature branch: `git checkout -b feature/your-feature`
2. Make changes and commit: `git commit -m "Add your feature"`
3. Push to remote: `git push origin feature/your-feature`
4. Create Pull Request

---

## 📝 API Documentation

### Token Generation Endpoint
**POST** `/api/v1/generate-token/`

Request:
```json
{
  "username": "user@example.com",
  "session_id": "abc123..."
}
```

Response:
```json
{
  "token": "ABC123XYZ",
  "expires_at": "2024-01-15T12:30:00Z",
  "device_id": "desktop-app-001"
}
```

### OTP Verification Endpoint
**POST** `/api/v1/verify-otp/`

Request:
```json
{
  "email": "user@example.com",
  "otp": "123456",
  "session_id": "abc123..."
}
```

Response:
```json
{
  "verified": true,
  "next_step": "token_validation"
}
```

---

## 🐛 Troubleshooting

### Common Issues

**"ModuleNotFoundError: No module named 'django'"**
```bash
# Ensure virtual environment is activated
# On Windows: venv\Scripts\activate
# Install requirements
pip install -r requirements.txt
```

**"PSYCOPG2 binary packages not found"**
```bash
# Install psycopg2-binary
pip install psycopg2-binary
# Or: pip install psycopg2 (requires PostgreSQL dev libraries)
```

**"Database connection refused"**
- Verify PostgreSQL is running: `pg_isready -h localhost -p 5432`
- Check database credentials in `.env`
- Ensure database user and database exist

**"Email not sending"**
- Verify SMTP credentials in `.env`
- For Gmail: Use App Password, not main password
- Check firewall allows port 587 (SMTP)
- Enable "Less secure app access" if using old Gmail accounts

**"Desktop Token Generator won't connect"**
- Ensure backend server is running: `python manage.py runserver`
- Check CORS settings allow desktop app origin
- Verify network connectivity between desktop and backend

---

## 📚 Additional Resources

- [Django Documentation](https://docs.djangoproject.com/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
- [NIST Password Guidelines](https://pages.nist.gov/800-63-3/sp800-63b.html)

---

## 📄 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

---

## 🤝 Support & Contact

For issues, bug reports, or feature requests, please open an [Issue](https://github.com/yourusername/SecurePortal/issues) on GitHub.

For security vulnerabilities, please **do NOT** open a public issue. Instead, follow responsible disclosure practices and contact the maintainers directly.

---

## ⚠️ Security Notice

This project handles sensitive authentication data. Before using in production:

✅ **Do:**
- Generate a new SECRET_KEY
- Use strong database passwords
- Enable HTTPS/SSL
- Run security audit
- Review all hardcoded values
- Keep dependencies updated
- Implement rate limiting
- Monitor audit logs

❌ **Don't:**
- Commit `.env` file to repository
- Use DEBUG=True in production
- Share SECRET_KEY publicly
- Use weak passwords
- Skip security headers
- Disable HTTPS in production
- Ignore security warnings

---

**Built with ❤️ for enterprise security**

Last Updated: 2024
