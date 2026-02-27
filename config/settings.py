from pathlib import Path
import os

# Base directory del progetto
BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = "django-insecure-dev-only-change-me"

# Durante il debug su Render è utile tenerlo a True, 
# ma una volta verificato che tutto funziona, impostalo a False.
DEBUG = True

# MODIFICA IMPORTANTE: Aggiunto '*' per accettare tutti gli host su Render
ALLOWED_HOSTS = ['cedolini-web.onrender.com', 'localhost', '127.0.0.1', '*']

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
    # WhiteNoise può essere aggiunto qui per gestire i file statici su Render
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
        "DIRS": [],
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

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = "it-it"
TIME_ZONE = "Europe/Rome"
USE_I18N = True
USE_TZ = True

# Configurazione file statici
STATIC_URL = "static/"
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Configurazione Login/Logout
LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/login/"

# Configurazione Email
ADMIN_NOTIFY_EMAIL = "antimo.digiovanni@sanvincenzosrl.com"
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtps.aruba.it"
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = "antimo.digiovanni@sanvincenzosrl.com"
EMAIL_HOST_PASSWORD = "Unilever_02"
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER

PASSWORD_CHANGE_REDIRECT_URL = "/"

# Dominio per email reset
DEFAULT_DOMAIN = "cedolini-web.onrender.com"
DEFAULT_PROTOCOL = "https"