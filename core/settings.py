import os
import dj_database_url
from pathlib import Path

# 1. Base Directory
BASE_DIR = Path(__file__).resolve().parent.parent

# 2. Security & Environment Setup
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-ea66!!^77ts$v82)m-bfhqm#i2ea((&@^kz73gcyfwu1s$-5n@')

DEBUG = os.environ.get('DEBUG', 'False').lower() in ['true', '1', 't']

ALLOWED_HOSTS = [
    'selguudi.co.tz',
    'www.selguudi.co.tz',
    'selguudi-backend.onrender.com',
    'localhost',
    '127.0.0.1',
]

# 3. Installed Apps
INSTALLED_APPS = [
    'corsheaders',  # Lazima iwepo kwa ajili ya CORS
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third-party Apps
    'rest_framework',
    'rest_framework_simplejwt',
    'django_rest_passwordreset',
    'django_filters',
    
    # Local Apps (Zako)
    # Weka apps zako za mradi hapa kama zipo (mfano: 'authentication', 'pos_app', nk.)
]

# 4. Middleware Setup
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',  # Lazima iwe ya kwanza kabisa
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'selguudi_backend.urls'  # Badilisha iwe jina la mradi wako kama ni tofauti

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

WSGI_APPLICATION = 'selguudi_backend.wsgi.application'

# 5. Database Setup
DATABASES = {
    'default': dj_database_url.config(
        default=os.environ.get('DATABASE_URL', f"sqlite:///{BASE_DIR / 'db.sqlite3'}"),
        conn_max_age=600,
        conn_health_checks=True,
    )
}

# 6. Password Validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# 7. Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# 8. Static Files
STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# 9. Security Headers kwa Production
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

# 10. CORS & CSRF Mipangilio (Kutatua CORS / 500 Preflight Error)
CORS_ALLOWED_ORIGINS = [
    'https://selguudi.co.tz',
    'https://www.selguudi.co.tz',
    'http://localhost:3000',
    'http://localhost:5173',
]

CSRF_TRUSTED_ORIGINS = [
    'https://selguudi.co.tz',
    'https://www.selguudi.co.tz',
    'https://selguudi-backend.onrender.com',
]

CORS_ALLOW_CREDENTIALS = True

# 11. Mipangilio ya Kutuma Email (Selguudi POS)
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'selguudipos@gmail.com'
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = 'Selguudi POS <selguudipos@gmail.com>'