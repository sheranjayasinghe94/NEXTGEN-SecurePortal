# Contributing to SecurePortal

We appreciate your interest in contributing to SecurePortal! This document provides guidelines for contributing to the project.

## Code of Conduct

Please be respectful, constructive, and professional in all interactions.

## Ways to Contribute

- **Report Bugs**: Found a bug? Open an issue with detailed reproduction steps
- **Suggest Features**: Have an idea? Discuss it first by opening an issue
- **Submit Code**: Fork the repository and submit pull requests
- **Improve Documentation**: Help us improve README, guides, and code comments
- **Security Audits**: Help identify security vulnerabilities (see SECURITY.md)

## Getting Started

### 1. Fork the Repository
```bash
# Click "Fork" on GitHub and clone your fork
git clone https://github.com/YOUR-USERNAME/SecurePortal.git
cd SecurePortal
```

### 2. Create a Feature Branch
```bash
git checkout -b feature/your-feature-name
# or for bug fixes:
git checkout -b bugfix/issue-description
```

### 3. Set Up Development Environment
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install black flake8 pytest django-debug-toolbar

# Copy environment template
cp .env.example .env
# Edit .env with your local settings
```

### 4. Make Changes
- Write clean, well-commented code
- Follow PEP 8 style guide
- Keep commits focused and atomic
- Write meaningful commit messages

### 5. Test Your Changes
```bash
# Run Django tests
python manage.py test

# Run linting
flake8 .

# Format code
black .
```

### 6. Commit & Push
```bash
git add .
git commit -m "Clear description of your changes"
git push origin feature/your-feature-name
```

### 7. Create Pull Request
- Go to GitHub and create a Pull Request
- Fill in the PR template with:
  - What your changes do
  - Why you're making them
  - Any related issues
  - Testing instructions

## Code Style Guidelines

### Python Code
- Follow [PEP 8](https://pep8.org/)
- Use 4 spaces for indentation
- Max line length: 88 characters (Black default)
- Use type hints where applicable

```python
# Good
def verify_otp(email: str, otp: str, session_id: str) -> bool:
    """Verify OTP for the given email and session."""
    pass

# Bad
def verify_otp(email, otp, session_id):
    pass
```

### Commit Messages
```
# Format: <type>(<scope>): <subject>

# Example:
feat(authentication): add rate limiting to OTP verification
fix(api): handle missing session ID in token endpoint
docs(readme): update setup instructions
test(accounts): add CustomUser model tests
```

**Types**: `feat`, `fix`, `docs`, `test`, `refactor`, `style`, `perf`

### Docstrings
```python
def create_otp(email: str, validity_minutes: int = 4) -> str:
    """
    Generate a time-limited OTP for email verification.
    
    Args:
        email: User email address
        validity_minutes: OTP validity period in minutes
        
    Returns:
        6-digit OTP code
        
    Raises:
        ValueError: If email is invalid
    """
    pass
```

## Security Guidelines

- Never hardcode secrets, API keys, or credentials
- Use environment variables for all sensitive data
- Never commit `.env` or secrets files
- Review SECURITY.md before making security-related changes
- Report security vulnerabilities responsibly

## Testing Requirements

- Add tests for all new features
- Update tests for modified functionality
- Maintain or improve code coverage
- All tests must pass before PR merge

```bash
# Run tests with coverage
coverage run --source='.' manage.py test
coverage report
```

## Documentation

- Update README.md if your changes affect setup or usage
- Add docstrings to all functions and classes
- Include type hints in function signatures
- Update CHANGELOG if keeping one

## Database Migrations

If your changes modify models:
```bash
python manage.py makemigrations
python manage.py migrate
```

Include migration files in your commit.

## Reporting Issues

### Bug Reports
Include:
- Clear description of the bug
- Steps to reproduce
- Expected behavior
- Actual behavior
- Environment (Python version, Django version, OS)
- Error messages/logs

### Feature Requests
Include:
- Clear description of the feature
- Use case/motivation
- Proposed implementation (optional)
- Alternative solutions (optional)

## Review Process

1. Code review by maintainers
2. Automated tests must pass
3. No merge conflicts
4. Documentation updated
5. At least one approval required

## Questions?

- Open a GitHub Discussion
- Check existing issues for similar questions
- Review existing documentation

---

**Thank you for contributing to SecurePortal!** 🎉
