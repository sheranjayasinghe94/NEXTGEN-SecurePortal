@echo off
REM ════════════════════════════════════════════════════════════
REM  SecurePortal – PostgreSQL Database Setup Script
REM  Run this once before starting the Django server.
REM
REM  INSTRUCTIONS:
REM  1. Ensure PostgreSQL is installed and running on port 5432
REM  2. When prompted, enter your PostgreSQL superuser password
REM  3. Double-click this file or run it in Command Prompt
REM ════════════════════════════════════════════════════════════

setlocal enabledelayedexpansion

REM Detect PostgreSQL installation path
for /D %%D in ("C:\Program Files\PostgreSQL\*") do (
    set PSQL="%%D\bin\psql.exe"
    goto found
)

echo ERROR: PostgreSQL not found in C:\Program Files\PostgreSQL\
echo Please ensure PostgreSQL is installed.
pause
exit /b 1

:found
echo Found PostgreSQL at: !PSQL!
echo.
echo Enter your PostgreSQL superuser (postgres) password when prompted.
echo.

REM Use .env file for database credentials
if exist .env (
    echo Using database credentials from .env file
    for /f "tokens=1,2 delims==" %%A in (.env) do (
        if "%%A"=="DB_USER" set DB_USER=%%B
        if "%%A"=="DB_PASSWORD" set DB_PASSWORD=%%B
        if "%%A"=="DB_NAME" set DB_NAME=%%B
    )
) else (
    echo .env file not found. Using default credentials.
    set DB_USER=corp_user
    set DB_PASSWORD=change-me
    set DB_NAME=corp_portal_db
)

echo [1/3] Creating database user !DB_USER!...
set PGPASSWORD=
!PSQL! -U postgres -c "CREATE USER !DB_USER! WITH PASSWORD '!DB_PASSWORD!'; CREATE DATABASE !DB_NAME! OWNER !DB_USER!; GRANT ALL PRIVILEGES ON DATABASE !DB_NAME! TO !DB_USER!;" 2>NUL
echo Done (or already exists).

echo [2/3] Setting up database privileges...
set PGPASSWORD=
!PSQL! -U postgres -d !DB_NAME! -c "GRANT ALL PRIVILEGES ON SCHEMA public TO !DB_USER!;" 2>NUL
echo Done.

echo.
echo Database setup complete!
echo.
echo Next steps:
echo  1. Create a .env file with your database and email credentials
echo  2. Run: pip install -r requirements.txt
echo  3. Run: python manage.py migrate
echo  4. Run: python manage.py create_admin
echo.
pause
