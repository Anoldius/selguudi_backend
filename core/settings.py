# 2. Security & Environment Setup
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-ea66!!^77ts$v82)m-bfhqm#i2ea((&@^kz73gcyfwu1s$-5n@')

DEBUG = os.environ.get('DEBUG', 'False').lower() in ['true', '1', 't']

# ALLOWED HOSTS MPYA
ALLOWED_HOSTS = [
    'selguudi.co.tz',
    'www.selguudi.co.tz',
    'selguudi-backend.onrender.com',
    'localhost',
    '127.0.0.1',
    '*',
]

# Security Headers kwa Production Mode
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True