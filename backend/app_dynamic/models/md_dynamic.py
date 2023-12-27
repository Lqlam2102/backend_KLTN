import datetime

from django.db import models

from django.core.exceptions import FieldDoesNotExist
from django.db import models
from django.utils import timezone
from django.utils.text import slugify
from django.utils.functional import cached_property

from . import config
from .factory import ModelFactory, FieldFactory
from .exceptions import NullFieldChangedError, InvalidFieldNameError
from .schema import ModelSchemaEditor, FieldSchemaEditor
from .utils import LastModifiedCache, ModelRegistry


class ModelSchema(models.Model):
    name = models.CharField(max_length=32, unique=True)
    use_uuid = models.BooleanField(default=False, editable=False)
    use_object3d = models.BooleanField(default=False, editable=False)
    # alias = models.CharField(max_length=200, default="", null=True, blank=True)
    _modified = models.DateTimeField(auto_now=True)
    _cache = LastModifiedCache()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._registry = ModelRegistry(self.app_label)
        self._initial_name = self.name
        initial_model = self.get_registered_model()
        self._schema_editor = ModelSchemaEditor(initial_model)

    def save(self, **kwargs):
        super().save(**kwargs)
        self.last_modified = self._modified
        self._schema_editor.update_table(self._factory.make_model())

    def delete(self, **kwargs):
        self._schema_editor.drop_table(self.as_model())
        self._factory.destroy_model()
        del self.last_modified
        super().delete(**kwargs)

    @property
    def last_modified(self):
        return self._cache.get(self)

    @last_modified.setter
    def last_modified(self, timestamp):
        self._cache.set(self, timestamp)

    @last_modified.deleter
    def last_modified(self):
        self._cache.delete(self)

    def get_registered_model(self):
        return self._registry.get_model(self.model_name)

    def is_current_schema(self):
        return self._modified >= self.last_modified

    def is_current_model(self, model):
        if model._schema.pk != self.pk:
            raise ValueError("Can only be called on a model of this schema")
        return model._declared >= self.last_modified

    @property
    def _factory(self):
        return ModelFactory(self)

    @property
    def app_label(self):
        return config.dynamic_models_app_label()

    @property
    def model_name(self):
        return self.get_model_name(self.name)

    @property
    def initial_model_name(self):
        return self.get_model_name(self._initial_name)

    @classmethod
    def get_model_name(cls, name):
        return name

    @property
    def db_table(self):
        parts = (self.app_label, slugify(self.name).replace('-', '_'))
        return '_'.join(parts)

    def as_model(self):
        return self._factory.get_model()

    class Meta:
        db_table = 'tb_core_models_schema'
        verbose_name = 'Mô hình dữ liệu'
        verbose_name_plural = 'Các mô hình dữ liệu'


class FieldSchema(models.Model):
    _PROHIBITED_NAMES = ('__module__', '_schema', '_declared')
    _MAX_LENGTH_DATA_TYPES = ('character',)

    name = models.CharField(max_length=63)
    model_schema = models.ForeignKey(
        ModelSchema,
        on_delete=models.CASCADE,
        related_name='fields'
    )
    data_type = models.CharField(
        max_length=16,
        choices=FieldFactory.data_type_choices(),
        editable=False
    )
    null = models.BooleanField(default=False)
    blank = models.BooleanField(default=False)
    unique = models.BooleanField(default=False)
    max_length = models.PositiveIntegerField(null=True)
    verbose_name = models.CharField(max_length=255, null=True, blank=True)
    model_foreign = models.CharField(max_length=255, null=True, blank=True)
    default = models.CharField(max_length=255, null=True, blank=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._initial_name = self.name
        self._initial_null = self.null
        self._initial_field = self.get_registered_model_field()
        self._schema_editor = FieldSchemaEditor(self._initial_field)

    def save(self, **kwargs):
        self.validate()
        super().save(**kwargs)
        self.update_last_modified()
        model, field = self._get_model_with_field()
        self._schema_editor.update_column(model, field)

    def delete(self, **kwargs):
        model, field = self._get_model_with_field()
        self._schema_editor.drop_column(model, field)
        self.update_last_modified()
        super().delete(**kwargs)

    def validate(self):
        if self._initial_null and not self.null:
            raise NullFieldChangedError(f"Cannot change NULL field '{self.name}' to NOT NULL")

        if self.name in self.get_prohibited_names():
            raise InvalidFieldNameError(f'{self.name} is not a valid field name')

    def get_registered_model_field(self):
        latest_model = self.model_schema.get_registered_model()
        if latest_model and self.name:
            try:
                return latest_model._meta.get_field(self.name)
            except FieldDoesNotExist:
                pass

    @classmethod
    def get_prohibited_names(cls):
        # TODO: return prohbited names based on backend
        return cls._PROHIBITED_NAMES

    @classmethod
    def get_data_types(cls):
        return FieldFactory.get_data_types()

    @property
    def db_column(self):
        return slugify(self.name).replace('-', '_')

    def requires_max_length(self):
        return self.data_type in self.__class__._MAX_LENGTH_DATA_TYPES

    def update_last_modified(self):
        self.model_schema.last_modified = timezone.now()

    def get_options(self):
        """
        Get a dictionary of kwargs to be passed to the Django field constructor
        """
        options = {'null': self.null, 'unique': self.unique, 'blank': self.blank}
        if self.verbose_name:
            options['verbose_name'] = self.verbose_name
        if self.default:
            if self.data_type == 'date' and self.default == 'now':
                options['default'] = datetime.datetime.now()
            else:
                options['default'] = self.default
        if self.data_type in ['float', 'integer']:
            self.max_length = None

        if self.max_length:
            options['max_length'] = self.max_length
        if self.requires_max_length():
            options['max_length'] = self.max_length or config.default_charfield_max_length()
        if self.data_type in ['multipolygon', 'polygon', 'linestring', 'point', 'geometry']:
            options['srid'] = 4326
        if self.data_type in ['foreignkey']:
            # TODO: Check
            options['to'] = ModelSchema.objects.get(name=self.model_foreign).as_model()
            options['on_delete'] = models.CASCADE
        return options

    def _get_model_with_field(self):
        model = self.model_schema.as_model()
        try:
            field = model._meta.get_field(self.db_column)
        except FieldDoesNotExist:
            field = None
        return model, field

    class Meta:
        db_table = 'tb_core_fields_schema'
        verbose_name = 'Trường trong mô hình dữ liệu'
        verbose_name_plural = 'Các trường trong mô hình dữ liệu'
