from django.contrib.gis.db.models import MultiPolygonField, PointField, LineStringField, PolygonField, GeometryField
from django.db import models
from django.utils import timezone
import uuid

from . import config
from .exceptions import OutdatedModelError
from .utils import ModelRegistry


class ModelFactory:

    def __init__(self, model_schema):
        self.schema = model_schema
        self.registry = ModelRegistry(model_schema.app_label)

    # Dang ki model khong can luu ra file
    def get_model(self):
        registered = self.get_registered_model()
        if registered and self.schema.is_current_model(registered):
            return registered
        return self.make_model()

    def make_model(self):
        self.unregister_model()
        model = type(
            self.schema.model_name,
            (models.Model,),
            self.get_properties()
        )
        _connect_schema_checker(model)
        return model

    def destroy_model(self):
        last_model = self.get_registered_model()
        if last_model:
            _disconnect_schema_checker(last_model)
            self.unregister_model()

    def get_registered_model(self):
        return self.registry.get_model(self.schema.initial_model_name)

    def unregister_model(self):
        try:
            self.registry.unregister_model(self.schema.initial_model_name)
        except LookupError:
            pass

    def get_properties(self):
        result = {
            **self._base_properties(),
            **config.default_fields(),
            **self._custom_fields()
        }
        if self.schema.use_uuid:
            result |= {
                'id': models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
            }
        return result

    def _base_properties(self):
        return {
            '__module__': '{}.models'.format(self.schema.app_label),
            '_declared': timezone.now(),
            '_schema': self.schema,
            'Meta': self._model_meta(),
        }

    def _custom_fields(self):
        fields = {}
        for field_schema in self.schema.fields.all():
            model_field = FieldFactory(field_schema).make_field()
            fields[field_schema.db_column] = model_field
        return fields

    # TODO: thay đổi meta của dynamic model tại đây
    def _model_meta(self):
        class Meta:
            app_label = self.schema.app_label
            # db_table = self.schema.db_table
            db_table = f'tb_dynamic_{self.schema.model_name.lower()}'
            verbose_name = self.schema.name

        return Meta


class FieldFactory:
    DATA_TYPES = {
        'image': models.ImageField,
        'file': models.FileField,
        'character': models.CharField,
        'text': models.TextField,
        'integer': models.IntegerField,
        'float': models.FloatField,
        'boolean': models.BooleanField,
        'date': models.DateTimeField,
        'point': PointField,
        'linestring': LineStringField,
        'polygon': PolygonField,
        'geometry': GeometryField,
        'multipolygon': MultiPolygonField,
        'json': models.JSONField,
        'foreignkey': models.ForeignKey,
    }

    def __init__(self, field_schema):
        self.schema = field_schema

    def make_field(self):
        options = self.schema.get_options()
        constructor = self.get_constructor()
        return constructor(**options)

    def get_constructor(self):
        return self.DATA_TYPES[self.schema.data_type]

    @classmethod
    def data_type_choices(cls):
        return [(dt, dt) for dt in cls.get_data_types()]

    @classmethod
    def get_data_types(cls):
        return cls.DATA_TYPES


def check_model_schema(sender, instance, **kwargs):  # pylint: disable=unused-argument
    """
    Check that the schema being used is the most up-to-date.

    Called on pre_save to guard against the possibility of a model schema change
    between instance instantiation and record save.
    """
    pass
    # if not sender._schema.is_current_model(sender):
    #     raise OutdatedModelError(
    #         "model {} has changed".format(sender.__name__)
    #     )


def _connect_schema_checker(model):
    models.signals.pre_save.connect(
        check_model_schema,
        sender=model,
        dispatch_uid=_get_signal_uid(model.__name__)
    )


def _disconnect_schema_checker(model):
    models.signals.pre_save.disconnect(
        check_model_schema,
        sender=model,
        dispatch_uid=_get_signal_uid(model.__name__)
    )


def _get_signal_uid(model_name):
    return '{}_model_schema'.format(model_name)
