import os
import json
from pathlib import Path
from urllib.parse import urlparse, unquote

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR.parent / '.env')
DEBUG = os.getenv('DEBUG', 'false').lower() == 'true'
SECRET_KEY = os.getenv('SECRET_KEY', '')
if not SECRET_KEY:
    if not DEBUG:
        raise RuntimeError('Defina SECRET_KEY no ambiente (copie .env.example).')
    SECRET_KEY = 'movi-local-development-only-never-use-in-production'
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')
INSTALLED_APPS = [
    'django.contrib.admin', 'django.contrib.auth', 'django.contrib.contenttypes',
    'django.contrib.sessions', 'django.contrib.messages', 'django.contrib.staticfiles',
    'rest_framework', 'django_filters', 'drf_spectacular', 'core', 'billing', 'academic',
]
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware', 'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware', 'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware', 'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware', 'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
ROOT_URLCONF = 'config.urls'
TEMPLATES = [{'BACKEND': 'django.template.backends.django.DjangoTemplates', 'DIRS': [],
    'APP_DIRS': True, 'OPTIONS': {'context_processors': [
        'django.template.context_processors.request', 'django.contrib.auth.context_processors.auth',
        'django.contrib.messages.context_processors.messages']}}]
WSGI_APPLICATION = 'config.wsgi.application'
if os.getenv('TEST_SQLITE') == '1':
    # Explicit isolated test fallback; application persistence defaults to PostgreSQL.
    DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': BASE_DIR / 'test.sqlite3'}}
else:
    db_url = urlparse(os.getenv('DATABASE_URL', 'postgresql://movi:movi@127.0.0.1:5432/movi'))
    DATABASES = {'default': {'ENGINE': 'django.db.backends.postgresql',
        'NAME': db_url.path.lstrip('/'), 'USER': unquote(db_url.username or ''),
        'PASSWORD': unquote(db_url.password or ''), 'HOST': db_url.hostname,
        'PORT': db_url.port or 5432, 'CONN_MAX_AGE': 60}}
AUTH_USER_MODEL = 'core.User'
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]
LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': ['rest_framework.authentication.SessionAuthentication'],
    'DEFAULT_PERMISSION_CLASSES': ['core.permissions.IsInternal'],
    'DEFAULT_PAGINATION_CLASS': 'config.pagination.StandardPagination',
    'PAGE_SIZE': 25,
    'DEFAULT_FILTER_BACKENDS': ['django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter', 'rest_framework.filters.OrderingFilter'],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_THROTTLE_RATES': {'login': '20/hour', 'register': '10/hour'},
}
SPECTACULAR_SETTINGS = {'TITLE': 'MOVI+ API', 'VERSION': '1.0.0', 'SERVE_INCLUDE_SCHEMA': False,
    'ENUM_NAME_OVERRIDES': {'UserRoleEnum':['communication','coordinator','instructor','secretary']}}
CSRF_TRUSTED_ORIGINS = os.getenv('CSRF_TRUSTED_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173').split(',')
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
BUSINESS_APPROVALS = [item.strip() for item in os.getenv('BUSINESS_APPROVALS', '').split(',') if item.strip()]
ATTENDANCE_POLICY = json.loads(os.getenv('ATTENDANCE_POLICY', 'null') or 'null')
DEMO_MODE = DEBUG and os.getenv('DEMO_MODE', 'false').lower() == 'true'
