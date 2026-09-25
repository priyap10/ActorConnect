"""Settings shared by every environment. Environment specifics live in
development.py and production.py."""
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("DJANGO_SECRET_KEY", default="")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    # Local apps
    "apps.core",
    "apps.accounts",
    "apps.profiles",
    "apps.portfolio",
    "apps.feed",
    "apps.network",
    "apps.casting",
    "apps.messaging",
    "apps.notifications",
    "apps.search",
    "apps.moderation",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.core.middleware.SecurityHeadersMiddleware",
    "apps.core.middleware.RateLimitMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.core.context_processors.site",
                "apps.core.context_processors.counters",
            ],
        },
    },
]

# ---------------------------------------------------------------- Database
DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default="postgres://actorconnect:actorconnect@localhost:5432/actorconnect",
    )
}
DATABASES["default"]["ATOMIC_REQUESTS"] = True
DATABASES["default"]["CONN_MAX_AGE"] = 60
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ------------------------------------------------------------------- Cache
REDIS_URL = env("REDIS_URL", default="")
if REDIS_URL:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": REDIS_URL,
        }
    }
else:
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

# ------------------------------------------------------------------ Celery
CELERY_BROKER_URL = REDIS_URL or "redis://localhost:6379/0"
CELERY_RESULT_BACKEND = None
CELERY_TASK_ALWAYS_EAGER = env.bool("CELERY_EAGER", default=False)
CELERY_TASK_EAGER_PROPAGATES = False
CELERY_TASK_TIME_LIMIT = 30 * 60
CELERY_TASK_SOFT_TIME_LIMIT = 25 * 60
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True

# ---------------------------------------------------------------- Auth
AUTH_USER_MODEL = "accounts.User"
LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "feed:home"
LOGOUT_REDIRECT_URL = "core:landing"

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 10},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
PASSWORD_RESET_TIMEOUT = 60 * 60  # one hour
EMAIL_VERIFICATION_MAX_AGE = 60 * 60 * 72  # three days

SESSION_COOKIE_AGE = 60 * 60 * 24 * 14
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_FAILURE_VIEW = "apps.core.views.error_403_csrf"

# ------------------------------------------------------ Internationalisation
LANGUAGE_CODE = "en-gb"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

# ------------------------------------------------------------ Static / media
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

# Uploads: large files stream to temp files rather than sitting in memory.
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
FILE_UPLOAD_PERMISSIONS = 0o640
UPLOAD_LIMITS_MB = {"video": 200, "audio": 50, "image": 8}
AVATAR_MAX_MB = 5

# ------------------------------------------------------------------ Email
EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = env("EMAIL_HOST", default="")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="ActorConnect <no-reply@actorconnect.local>")

# ------------------------------------------------------------------- Site
SITE_NAME = "ActorConnect"
ADMIN_URL = env("ADMIN_URL", default="admin/")

# ---------------------------------------------------------------------- AI
ANTHROPIC_API_KEY = env("ANTHROPIC_API_KEY", default="")
ANTHROPIC_MODEL = env("ANTHROPIC_MODEL", default="claude-sonnet-5")
EMBEDDING_MODEL = env("EMBEDDING_MODEL", default="sentence-transformers/all-MiniLM-L6-v2")
EMBEDDING_DIMENSIONS = 384  # must match EMBEDDING_MODEL's output size
WHISPER_MODEL_SIZE = env("WHISPER_MODEL_SIZE", default="base")

# ------------------------------------------------------------ Rate limiting
RATE_LIMIT_TRUST_XFF = env.bool("RATE_LIMIT_TRUST_XFF", default=False)
RATE_LIMITS = [
    # name, path prefix, methods, requests allowed, window in seconds
    {"name": "login", "prefix": "/accounts/login/", "methods": ["POST"], "limit": 10, "window": 300},
    {"name": "register", "prefix": "/accounts/register/", "methods": ["POST"], "limit": 10, "window": 3600},
    {"name": "reset", "prefix": "/accounts/password-reset/", "methods": ["POST"], "limit": 5, "window": 3600},
    {"name": "resend", "prefix": "/accounts/verify/resend/", "methods": ["POST"], "limit": 5, "window": 3600},
    {"name": "messages", "prefix": "/messages/", "methods": ["POST"], "limit": 60, "window": 60},
    {"name": "ai_feedback", "prefix": "/portfolio/media/", "methods": ["POST"], "limit": 20, "window": 3600},
    {"name": "ai_brief", "prefix": "/casting/brief/", "methods": ["POST"], "limit": 15, "window": 3600},
    {"name": "ai_insights", "prefix": "/profiles/insights/", "methods": ["POST"], "limit": 10, "window": 3600},
    {"name": "search", "prefix": "/search/", "methods": ["GET"], "limit": 60, "window": 60},
    {"name": "posting", "prefix": "/feed/", "methods": ["POST"], "limit": 60, "window": 60},
]

# ---------------------------------------------------------------- Logging
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {"format": "%(asctime)s %(levelname)s %(name)s: %(message)s"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "standard"},
    },
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "django.security": {"handlers": ["console"], "level": "WARNING", "propagate": False},
        "apps": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}