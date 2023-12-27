from django.apps import AppConfig
DYNAMIC_MODELS = {
    'DEFAULT_CHARFIELD_MAX_LENGTH': 255,
    'DEFAULT_USE_APP_LABLE': "app_dynamic",
    'CACHE_KEY_PREFIX': "app_dynamic" + "_",
    'CACHE_TIMEOUT': 60 * 60 * 9999999999999999,  # *24  = 24hours
}

class AppDynamicConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app_dynamic'
