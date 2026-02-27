from pathlib import Path
import os
import dj_database_url

# Base directory del progetto
BASE_DIR = Path(__file__).resolve().parent.parent

# Sicurezza (Usa variabili d'ambiente su Render)
SECRET_KEY = os.environ.get("SECRET_KEY", "django-insecure-dev-only-change-me")
DEBUG = os.environ.get("DEBUG", "False") == "True" 

ALLOWED_HOSTS = ['cedolini-web.onrender.com', 'localhost', '127.0.0.1']

# Applicazioni
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "portal", 
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # Per i file statici
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, 'templates')],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Database (PostgreSQL su Render, SQLite in locale)
DATABASES = {
    'default': dj_database_url.config(
        default=os.environ.get('DATABASE_URL'),
        conn_max_age=600
    )
}

if not DATABASES['default']:
    DATABASES['default'] = {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }

# Validazione password (disabilitata per semplificare i test iniziali)
AUTH_PASSWORD_VALIDATORS = []

# Internazionalizzazione
LANGUAGE_CODE = "it-it"
TIME_ZONE = "Europe/Rome"
USE_I18N = True
USE_TZ = True

# File Statici (Grafica)
STATIC_URL = "static/"
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# File Media (Documenti PDF)
MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# --- CONFIGURAZIONE LOGIN/LOGOUT ---
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "admin_dashboard"  # Cambiato da 'home' a 'admin_dashboard'
LOGOUT_REDIRECT_URL = "login"

# --- CONFIGURAZIONE EMAIL ---
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtps.aruba.it"
EMAIL_PORT = 465
EMAIL_USE_SSL = True
EMAIL_USE_TLS = False
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', 'antimo.digiovanni@sanvincenzosrl.com')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD') 
DEFAULT_FROM_EMAIL = f"San Vincenzo SRL <{EMAIL_HOST_USER}>"

# Parametri per i link nelle email
DEFAULT_DOMAIN = "cedolini-web.onrender.com"
DEFAULT_PROTOCOL = "https"

# --- SICUREZZA E PROXY ---
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
PENDING_UPLOAD_DIR = os.path.join(MEDIA_ROOT, "pending")

CSRF_TRUSTED_ORIGINS = ['https://cedolini-web.onrender.com']
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')