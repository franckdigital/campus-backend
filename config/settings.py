"""
Django settings for Campus Management System.
"""
import os
from pathlib import Path
from datetime import timedelta
from decouple import config
from celery.schedules import crontab

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('SECRET_KEY', default='django-insecure-dev-key')

DEBUG = config('DEBUG', default=True, cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1,10.0.2.2,*').split(',')

# In production this app sits behind an HTTPS-terminating reverse proxy
# (nginx) that forwards to Gunicorn/Daphne over plain HTTP — without this,
# request.is_secure()/build_absolute_uri() can't tell the original request
# was HTTPS and emit http:// URLs for every absolute link the API builds
# (file/image fields via request.build_absolute_uri, the teacher fiche link,
# etc). Android blocks that cleartext traffic by default, so anything built
# from those URLs (e.g. exam webcam snapshot images) silently fails to load
# on mobile while still "working" in a browser, which just warns instead of
# blocking. Relies on nginx setting X-Forwarded-Proto, which is the standard
# convention.
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Application definition
DJANGO_APPS = [
    'daphne',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'django_filters',
    'channels',
    'django_celery_beat',
    'django_celery_results',
    'drf_spectacular',
]

LOCAL_APPS = [
    'apps.core',
    'apps.accounts',
    'apps.students',
    'apps.academic',
    'apps.attendance',
    'apps.finance',
    'apps.payments',
    'apps.accounting',
    'apps.documents',
    'apps.elearning',
    'apps.chat',
    'apps.notifications',
    'apps.reports',
    'apps.grades',
    'apps.staff',
    'apps.analytics',
    'apps.landing',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

# Database - MySQL
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': config('DB_NAME', default='campus'),
        'USER': config('DB_USER', default='root'),
        'PASSWORD': config('DB_PASSWORD', default='xamil@IFE2025'),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='3306'),
        'OPTIONS': {
            'charset': 'utf8mb4',
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    }
}

# Custom User Model
AUTH_USER_MODEL = 'accounts.User'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Africa/Abidjan'
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

# Media files
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
        'apps.students.permissions.IsRegistrationFeePaidOrExempt',
        'apps.elearning.permissions.IsTuitionUpToDateOrNotGated',
    ),
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ),
    'DEFAULT_PAGINATION_CLASS': 'apps.core.pagination.FlexiblePagination',
    'PAGE_SIZE': 20,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

# JWT Settings
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=12),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
}

# CORS
CORS_ALLOWED_ORIGINS = [
    'http://localhost:3000',
    'http://127.0.0.1:3000',
    'http://localhost:5173',
    'http://127.0.0.1:5173',
    'https://campus.numerix.digital',
]
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_ALL_ORIGINS = DEBUG  # autoriser toutes origines en développement
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]
CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]

# Channels (WebSocket)
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [config('REDIS_URL', default='redis://localhost:6379/0')],
        },
    },
}

# Celery Configuration
CELERY_BROKER_URL = config('REDIS_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = 'django-db'
CELERY_CACHE_BACKEND = 'django-cache'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'
CELERY_BEAT_SCHEDULE = {
    # Échéancier de scolarité : rappel étudiant + parents, à partir du 25 du
    # mois puis tous les 3 jours jusqu'à régularisation (voir apps.finance.tasks)
    'send-echeancier-reminders': {
        'task': 'finance.send_echeancier_reminders',
        'schedule': crontab(hour=8, minute=0),
    },
    # Rappels d'examens configurés depuis l'admin (Paramètres > Alertes &
    # Rappels) — voir apps.notifications.tasks.send_exam_reminders.
    'send-exam-reminders': {
        'task': 'notifications.send_exam_reminders',
        'schedule': crontab(hour=8, minute=15),
    },
    # Confirme le statut réel de livraison des push Expo (un ticket 'ok' ne
    # veut pas dire livré) et désactive les tokens morts — voir
    # apps.notifications.push.check_expo_receipts. Toutes les 30 min : Expo
    # a besoin de quelques minutes après l'envoi avant qu'un reçu soit prêt.
    'check-push-receipts': {
        'task': 'notifications.check_push_receipts',
        'schedule': crontab(minute='*/30'),
    },
    # Relance les envois EMAIL/SMS/WHATSAPP en échec (RETRYING) — existait
    # déjà comme tâche mais n'était jamais planifiée, donc ne tournait
    # jamais tant qu'on ne l'appelait pas manuellement.
    'retry-failed-notifications': {
        'task': 'notifications.retry_failed',
        'schedule': crontab(minute='*/15'),
    },
}

# CinetPay Configuration — API v1 "Aurora" (account_key/account_password
# exchanged for a bearer token via /v1/oauth/login, see apps.payments.services)
CINETPAY_ACCOUNT_KEY = config('CINETPAY_ACCOUNT_KEY', default='')
CINETPAY_ACCOUNT_PASSWORD = config('CINETPAY_ACCOUNT_PASSWORD', default='')
CINETPAY_NOTIFY_URL = config('CINETPAY_NOTIFY_URL', default='')
CINETPAY_SUCCESS_URL = config('CINETPAY_SUCCESS_URL', default='')
CINETPAY_FAILED_URL = config('CINETPAY_FAILED_URL', default='')
CINETPAY_BASE_URL = config('CINETPAY_BASE_URL', default='https://api.cinetpay.net')
CINETPAY_LOCAL_SANDBOX = config('CINETPAY_LOCAL_SANDBOX', default=False, cast=bool)

# Anthropic Claude API — used by apps.elearning.ai_service (tutor chat, content
# generation, auto-grading). Without this, ai_service falls back to a demo
# stub and none of those features actually run.
ANTHROPIC_API_KEY = config('ANTHROPIC_API_KEY', default='')

# Google Gemini API — used by apps.elearning.ai_service.analyze_exam_snapshot
# for exam webcam proctoring (free tier, no billing required — get a key at
# aistudio.google.com). Without this, snapshot analysis falls back to a
# neutral stub (no anomaly flags raised, description says AI is unconfigured).
GEMINI_API_KEY = config('GEMINI_API_KEY', default='')
GEMINI_VISION_MODEL = config('GEMINI_VISION_MODEL', default='gemini-flash-latest')

# Zoom Configuration
ZOOM_API_KEY = config('ZOOM_API_KEY', default='')
ZOOM_API_SECRET = config('ZOOM_API_SECRET', default='')
ZOOM_ACCOUNT_ID = config('ZOOM_ACCOUNT_ID', default='')

# Email Configuration
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER

# File Storage
USE_S3 = config('USE_S3', default=False, cast=bool)

if USE_S3:
    AWS_ACCESS_KEY_ID = config('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = config('AWS_SECRET_ACCESS_KEY')
    AWS_STORAGE_BUCKET_NAME = config('AWS_STORAGE_BUCKET_NAME')
    AWS_S3_REGION_NAME = config('AWS_S3_REGION_NAME', default='eu-west-1')
    AWS_DEFAULT_ACL = 'private'
    AWS_S3_OBJECT_PARAMETERS = {'CacheControl': 'max-age=86400'}
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'

# API Documentation
SPECTACULAR_SETTINGS = {
    'TITLE': 'Campus Management System API',
    'DESCRIPTION': 'API pour la gestion universitaire complète',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'campus.log',
            'formatter': 'verbose',
        },
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Create logs directory
LOGS_DIR = BASE_DIR / 'logs'
LOGS_DIR.mkdir(exist_ok=True)

# Frontend URL
FRONTEND_URL = config('FRONTEND_URL', default='http://localhost:3000')
