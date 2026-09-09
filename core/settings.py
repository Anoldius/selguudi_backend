import os
import dj_database_url
from pathlib import Path

# 1. Base Directory
BASE_DIR = Path(__file__).resolve().parent.parent

# 2. Security & Environment Setup
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-ea66!!^77ts$v82)m-bfhqm#i2ea((&@^kz73gcyfwu1s$-5n@')

DEBUG = os.environ.get('DEBUG', 'False').lower() in ['true', '1', 't']

# ALLOWED HOSTS MPYA (Orodha Rasmi Na Salama)
ALLOWED_HOSTS = [
    'selguudi.co.tz',
    'www.selguudi.co.tz',
    'selguudi-backend.onrender.com',
    'localhost',
    '127.0.0.1',
]

# Security Headers kwa Production Mode
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

# 3. Database Setup (Inasoma DATABASE_URL kutoka Render na SQLite kama Fallback)
DATABASES = {
    'default': dj_database_url.config(
        default=os.environ.get('DATABASE_URL', f"sqlite:///{BASE_DIR / 'db.sqlite3'}"),
        conn_max_age=600,
        conn_health_checks=True,
    )
}

# 4. Mipangilio ya Kutuma Email (Selguudi POS)
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'selguudipos@gmail.com'
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = 'Selguudi POS <selguudipos@gmail.com>'