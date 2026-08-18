<h1 align="center">DEPLOYMENT GUIDE FOR NEXTGEN-SECUREPORTAL</h1>
<p align="center">This guide provides step-by-step instructions for deploying SecurePortal to a production environment.</p>

## PRE-DEPLOYMENT CHECHLIST

### Security ✅
- [ ] Generated new `SECRET_KEY` (not the default)
- [ ] Updated all database credentials to strong, random values
- [ ] Enabled HTTPS/SSL certificate installed
- [ ] Set `DEBUG = False`
- [ ] Set `SESSION_COOKIE_SECURE = True`
- [ ] Set `CSRF_COOKIE_SECURE = True`
- [ ] Reviewed and tested all authentication flows
- [ ] Audit logging is working correctly
- [ ] Email configuration tested and working
- [ ] Run security audit: `python manage.py check --deploy`

### Database ✅
- [ ] PostgreSQL 15+ installed and running
- [ ] Database user with strong password created
- [ ] Database backups configured
- [ ] Replica/failover setup (if required)
- [ ] Migrations tested on staging environment
- [ ] Database logs are being collected

### Infrastructure ✅
- [ ] Web server (Gunicorn/uWSGI) configured
- [ ] Reverse proxy (Nginx/Apache) configured
- [ ] SSL certificate installed and valid
- [ ] Firewall rules configured
- [ ] Email server accessible and configured
- [ ] Monitoring and alerting set up
- [ ] Log aggregation configured

---

## DEPLOYMENT STEP

### Option 1: Linux/Ubuntu Server Deployment

#### 1. System Preparation

```bash
# Update system
sudo apt-get update
sudo apt-get upgrade -y

# Install system dependencies
sudo apt-get install -y python3.10 python3-pip python3-venv
sudo apt-get install -y postgresql postgresql-contrib
sudo apt-get install -y nginx
sudo apt-get install -y certbot python3-certbot-nginx
```

#### 2. Create Application User

```bash
# Create dedicated user for the application
sudo useradd -m -s /bin/bash secureportal
sudo su - secureportal
```

#### 3. Clone Repository

```bash
# Clone application
git clone https://github.com/yourusername/SecurePortal.git
cd SecurePortal

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn
```

#### 4. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit with production values
nano .env
```

**Key production values:**
```env
SECRET_KEY=<generate-new-key>
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
DB_HOST=localhost
DB_NAME=corp_portal_db
DB_USER=corp_user
DB_PASSWORD=<strong-random-password>
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=<app-password>
```

#### 5. PostgreSQL Setup

```bash
# Switch to postgres user
sudo su - postgres

# Create database and user
psql
CREATE USER corp_user WITH PASSWORD '<strong-password>';
CREATE DATABASE corp_portal_db OWNER corp_user;
GRANT ALL PRIVILEGES ON DATABASE corp_portal_db TO corp_user;
\q
exit
```

#### 6. Run Migrations

```bash
cd /home/secureportal/SecurePortal
source venv/bin/activate

# Apply migrations
python manage.py migrate

# Create superuser
python manage.py create_admin

# Collect static files
python manage.py collectstatic --noinput
```

#### 7. Configure Gunicorn

Create `/home/secureportal/SecurePortal/gunicorn_config.py`:
```python
bind = "127.0.0.1:8000"
workers = 4
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2
max_requests = 1000
max_requests_jitter = 50
errorlog = "/home/secureportal/SecurePortal/logs/gunicorn_error.log"
accesslog = "/home/secureportal/SecurePortal/logs/gunicorn_access.log"
loglevel = "info"
```

Create Systemd service `/etc/systemd/system/secureportal.service`:
```ini
[Unit]
Description=SecurePortal Django Application
After=network.target postgresql.service

[Service]
Type=notify
User=secureportal
Group=secureportal
WorkingDirectory=/home/secureportal/SecurePortal
ExecStart=/home/secureportal/SecurePortal/venv/bin/gunicorn -c gunicorn_config.py corp_portal.wsgi:application
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
KillSignal=SIGTERM
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
```

Enable and start service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable secureportal
sudo systemctl start secureportal
```

#### 8. Configure Nginx

Create `/etc/nginx/sites-available/secureportal`:
```nginx
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    
    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;
    
    # SSL configuration
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # Logging
    access_log /var/log/nginx/secureportal_access.log;
    error_log /var/log/nginx/secureportal_error.log;
    
    # Static files
    location /static/ {
        alias /home/secureportal/SecurePortal/staticfiles/;
        expires 30d;
    }
    
    # Media files
    location /media/ {
        alias /home/secureportal/SecurePortal/media/;
        expires 7d;
    }
    
    # Proxy to Gunicorn
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
        proxy_read_timeout 30s;
    }
}
```

Enable site:
```bash
sudo ln -s /etc/nginx/sites-available/secureportal /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

#### 9. Setup SSL Certificate

```bash
# Get SSL certificate from Let's Encrypt
sudo certbot certonly --nginx -d yourdomain.com -d www.yourdomain.com

# Auto-renewal is typically set up by default
sudo systemctl enable certbot.timer
```

#### 10. Setup Monitoring

```bash
# Install monitoring tools
pip install django-health-check
pip install sentry-sdk  # Optional: Error tracking

# Configure in settings.py if using Sentry
# Set SENTRY_DSN in .env
```

#### 11. Setup Backups

Create `/home/secureportal/backup_db.sh`:
```bash
#!/bin/bash

BACKUP_DIR="/home/secureportal/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/corp_portal_db_$DATE.sql.gz"

mkdir -p "$BACKUP_DIR"

pg_dump -U corp_user -h localhost corp_portal_db | gzip > "$BACKUP_FILE"

# Keep only last 30 days of backups
find "$BACKUP_DIR" -name "*.sql.gz" -mtime +30 -delete

echo "Backup completed: $BACKUP_FILE"
```

Add to crontab:
```bash
crontab -e
# Add: 0 2 * * * /home/secureportal/backup_db.sh
```

---

### Option 2: Docker Deployment

Create `Dockerfile`:
```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Copy application
COPY . .

# Create non-root user
RUN useradd -m app && chown -R app:app /app
USER app

# Run Gunicorn
CMD ["gunicorn", "-b", "0.0.0.0:8000", "corp_portal.wsgi:application"]
```

Create `docker-compose.yml`:
```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: corp_user
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: corp_portal_db
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  web:
    build: .
    command: gunicorn corp_portal.wsgi:application --bind 0.0.0.0:8000
    environment:
      DEBUG: "False"
      SECRET_KEY: ${SECRET_KEY}
      DB_HOST: postgres
      DB_NAME: corp_portal_db
      DB_USER: corp_user
      DB_PASSWORD: ${DB_PASSWORD}
    ports:
      - "8000:8000"
    depends_on:
      - postgres
    volumes:
      - ./logs:/app/logs

  nginx:
    image: nginx:latest
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - web

volumes:
  postgres_data:
```

---

## POST-DEPLOYMENT

### 1. Verify Installation

```bash
# Check application status
sudo systemctl status secureportal

# Check Nginx status
sudo systemctl status nginx

# Check PostgreSQL
sudo -u postgres pg_isready

# Run security check
python manage.py check --deploy
```

### 2. Test Authentication Flows

- Test user login with all MFA stages
- Test email OTP
- Test desktop token generator
- Verify audit logs are recording

### 3. Setup Monitoring

- Configure application monitoring (New Relic, Datadog, etc.)
- Setup log aggregation (ELK Stack, Splunk, etc.)
- Configure alerts for errors and failures
- Monitor database performance

## TROUBLESHOOTING

### Application won't start
```bash
sudo journalctl -u secureportal -n 50
```

### Database connection issues
```bash
sudo -u postgres psql -c "SELECT version();"
```

### Nginx issues
```bash
sudo nginx -t  # Test configuration
sudo journalctl -u nginx
```

### Email not sending
- Check SMTP credentials in `.env`
- Verify firewall allows port 587
- Test: `python manage.py shell` then test email sending

---

## Security Hardening

- Keep systems updated: `sudo apt-get update && sudo apt-get upgrade`
- Configure firewall: `sudo ufw enable`
- Monitor failed login attempts
- Setup intrusion detection (AIDE, Tripwire)
- Regular security audits
- Keep audit logs for compliance

---

For more information:
- [Django Deployment Checklist](https://docs.djangoproject.com/en/stable/howto/deployment/checklist/)
- [Gunicorn Deployment](https://docs.gunicorn.org/)
- [Nginx Documentation](https://nginx.org/en/docs/)
- [PostgreSQL Security](https://www.postgresql.org/docs/current/sql-syntax.html)
