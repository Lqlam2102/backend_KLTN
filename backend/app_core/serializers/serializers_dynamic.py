from django.apps import apps
from rest_framework import serializers
from rest_framework.serializers import raise_errors_on_nested_writes
from app_core.models import ModelDynamicFolder, TemplateDynamicModel
from app_dynamic.models import ModelSchema, FieldSchema
from backend.config import default_name_field_dynamic


class ModelDynamicFolderSerializerOverView(serializers.ModelSerializer):
    class Meta:
        model = ModelDynamicFolder
        fields = ['id', 'name_display', 'model',
                  'public']


class ModelDynamicFolderSerializer(serializers.ModelSerializer):
    type = serializers.SerializerMethodField(required=False)
    data_model = serializers.SerializerMethodField()

    class Meta:
        model = ModelDynamicFolder
        fields = ['id', 'name_display', 'model', 'data_model', 'wms_info', 'type', 'created_date', 'updated_date',
                  'description', 'tags', 'alias', 'public']

    def get_type(self, obj):
        return "data-dynamic"

    def get_data_model(self, obj):
        return f"{obj.model.lower()}/"


class ModelDynamicFolderDetailSerializer(serializers.ModelSerializer):
    data_model = serializers.SerializerMethodField(required=False)

    class Meta:
        model = ModelDynamicFolder
        fields = ['id', 'name_display', 'model', 'path', 'data_model', 'construct',
                  'description', 'tags', 'alias',
                  'wms_info', 'created_date', 'updated_date', 'public']
        extra_kwargs = {
            'path': {'read_only': 'true'},
            'response_wms': {'read_only': 'true'}
        }


    def get_data_model(self, obj):
        return f"{obj.model.lower()}/"

    def update(self, instance, validated_data):
        raise_errors_on_nested_writes('update', self, validated_data)
        request = self.context["request"]
        model_name = request.data.get('model')
        construct = request.data.get('construct')
        model_schema = ModelSchema.objects.get(name=instance.model)
        if model_name and model_name != instance.model:
            model_check = [model.__name__.lower() for model in apps.get_app_config("app_dynamic").get_models()]
            if model_name.lower().strip() in model_check:
                raise serializers.ValidationError({"message": "Model đã tồn tại"})
            if not model_name.isalpha() or not model_name[0].istitle():
                raise serializers.ValidationError({
                    "message": 'Model không được phép đặt với ký tự, số modelname bắt buộc phải bắt đầu bằng chữ cái in hoa.'})
            model_schema.name = model_name
            instance.name = model_name
        if construct and isinstance(construct, dict):
            use_uuid = construct.get('use_uuid')
            use_object3d = construct.get('use_object3d')
            if use_uuid is not None and use_uuid != instance.construct.get('use_uuid'):
                # Kiểm tra xem dynamic đó có dữ liệu hay chưa. Nếu có rồi thì không được thay đổi trường này.
                check_data = model_schema.as_model().objects.all().exists()
                if check_data:
                    raise ValueError({"message": "Không thể thay đổi use_uuid khi mô hình đã có dữ liệu."})
                model_schema.use_uuid = use_uuid
            if use_object3d is not None and use_object3d != instance.construct.get('use_object3d'):
                model_schema.use_object3d = use_object3d
                name_default = default_name_field_dynamic.get('object3d')
                if use_object3d:
                    field_object3d = FieldSchema(
                        name=name_default,
                        data_type='character',
                        max_length=50,
                        model_schema=model_schema,
                        null=True,
                        blank=True,
                        unique=False,
                        verbose_name="Đối tượng 3D")
                    field_object3d.save()
                else:
                    try:
                        fields_schema = FieldSchema.objects.get(
                            model_schema=model_schema, name=name_default)
                        fields_schema.delete()
                    except Exception as e:
                        raise serializers.ValidationError({"message": str(e)})
        model_schema.save()
        public = request.data.get('public')
        if public is not None and public != instance.public:
            instance.public = public
        instance.updated_by = request.user

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class TemplateDynamicModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = TemplateDynamicModel
        fields = ["id", "name", "description", "construct"]
