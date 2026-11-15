"""Django settings. Deployment-specific values come from the environment (see `.env.example`)."""

from datetime import timedelta
from pathlib import Path

import django_stubs_ext
from celery.schedules import crontab

from config.env import env_bool, env_int, env_list, env_str, env_time

# Lets classes that are generic only in the type stubs (ModelAdmin[Team]) be subscripted.
django_stubs_ext.monkeypatch()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = env_str("DJANGO_SECRET_KEY")
DEBUG = env_bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", default="localhost,127.0.0.1")
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS", default="")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "drf_spectacular",
    "apps.core",
    "apps.accounts",
    "apps.teams",
    "apps.notifications",
    "apps.tasks",
]

AUTH_USER_MODEL = "accounts.User"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env_str("POSTGRES_DB", "taskmanager"),
        "USER": env_str("POSTGRES_USER", "taskmanager"),
        "PASSWORD": env_str("POSTGRES_PASSWORD"),
        "HOST": env_str("POSTGRES_HOST", "localhost"),
        "PORT": env_int("POSTGRES_PORT", 5432),
    }
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
USE_I18N = False
USE_TZ = True
TIME_ZONE = env_str("TIME_ZONE", "America/Sao_Paulo")

# Redis backs the cache, which DRF uses to count requests for rate limiting. A shared store is
# needed: each gunicorn worker has its own memory, so a local cache would multiply every limit.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": env_str("REDIS_URL", "redis://localhost:6379/0"),
    }
}

# Celery: Redis is the broker. Jobs only write to the database, so no result backend is kept.
CELERY_BROKER_URL = env_str("REDIS_URL", "redis://localhost:6379/0")
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_TASK_IGNORE_RESULT = True
CELERY_TIMEZONE = TIME_ZONE
# Workers log through the LOGGING setting below, like the api, instead of Celery's own setup.
CELERY_WORKER_HIJACK_ROOT_LOGGER = False
_OVERDUE_JOB_TIME = env_time("OVERDUE_JOB_TIME", "08:00")
CELERY_BEAT_SCHEDULE = {
    "notify-overdue-tasks": {
        "task": "apps.tasks.tasks.notify_overdue_tasks",
        "schedule": crontab(hour=_OVERDUE_JOB_TIME.hour, minute=_OVERDUE_JOB_TIME.minute),
    },
}

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}

# Everything goes to stderr, so it shows in `docker compose logs`. Django's default would send
# request errors only to mail_admins when DEBUG is off, and their tracebacks would be lost.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "plain": {"format": "{asctime} {levelname} {name}: {message}", "style": "{"},
    },
    "handlers": {
        "stderr": {"class": "logging.StreamHandler", "formatter": "plain"},
    },
    "root": {"handlers": ["stderr"], "level": env_str("LOG_LEVEL", "INFO")},
    "loggers": {
        # Replaces Django's default handlers for its own loggers; records reach stderr through root.
        "django": {"handlers": [], "level": "INFO", "propagate": True},
    },
}

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "EXCEPTION_HANDLER": "apps.core.exception_handler.handle_exception",
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    # Per user (per client address when anonymous). The login endpoint has its own stricter scope.
    "DEFAULT_THROTTLE_CLASSES": ["rest_framework.throttling.UserRateThrottle"],
    "DEFAULT_THROTTLE_RATES": {
        "user": env_str("THROTTLE_USER_RATE", "300/min"),
        "login": env_str("THROTTLE_LOGIN_RATE", "5/min"),
    },
    # Proxies in front of the API. 0: the client address is the socket peer (REMOTE_ADDR), and
    # X-Forwarded-For is ignored, so a client cannot fake its address to dodge the login limit.
    "NUM_PROXIES": env_int("DRF_NUM_PROXIES", 0),
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Task manager API",
    "DESCRIPTION": "Teams, roles, task assignment and notifications. Authenticate with a Bearer "
    "access token from `POST /api/v1/auth/token`.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=env_int("JWT_REFRESH_DAYS", 7)),
    # Each refresh returns a new refresh token; the used one is blacklisted, and so is the one
    # sent to logout.
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    # Tokens carry a hash of the password: changing it invalidates every access token issued before.
    "CHECK_REVOKE_TOKEN": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}
