from .base import *  

DEBUG = True
SECRET_KEY = SECRET_KEY or "dev-only-insecure-key-do-not-use-in-production"  # noqa: F405
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0", "web", "testserver"]

WHITENOISE_USE_FINDERS = True
WHITENOISE_AUTOREFRESH = True

import sys 

if "test" in sys.argv:
    PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
    CELERY_TASK_ALWAYS_EAGER = True
    CELERY_TASK_EAGER_PROPAGATES = False