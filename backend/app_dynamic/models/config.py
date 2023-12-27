from ..apps import DYNAMIC_MODELS


def dynamic_models_app_label():
    return _settings().get('DEFAULT_USE_APP_LABLE')


def default_fields():
    return _settings().get('DEFAULT_FIELDS', {})


def default_charfield_max_length():
    return _settings().get('DEFAULT_CHARFIELD_MAX_LENGTH')


def cache_key_prefix():
    return _settings().get('CACHE_KEY_PREFIX')


def cache_timeout():
    return _settings().get('CACHE_TIMEOUT')


def _settings():
    return DYNAMIC_MODELS
