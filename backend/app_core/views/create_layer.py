import json
import math
import ast
import geopandas as gpd
from django.apps import apps
from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from importlib import import_module, reload
from app_core.models import ModelDynamicFolder, ManageGeojsonModel
from app_core.models import ManageShapeFileModel
from app_core.serializers.serializers_dynamic import ModelDynamicFolderDetailSerializer
from backend.config import default_name_field_dynamic
from backend.cores import no_accent_vietnamese, set_name_model, import_data_from_geodataframe
from ..models import ModelSchema
from ..models import FieldSchema
from django.conf import settings
from django.urls import clear_url_caches
from django.contrib import admin
import zipfile
import fiona


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def api_create_models_from_shapefile(request):
    # Validation
    shape_file = request.data.get('shape_file')
    name_display = request.data.get('name_display')
    model_name = set_name_model(name_display)
    model_check = [model.__name__.lower() for model in apps.get_app_config("app_dynamic").get_models()]
    while model_name.lower().strip() in model_check:
        model_name = set_name_model(name_display)
    alias = request.data.get('alias')
    description = request.data.get('description')
    tags = request.data.get('tags')
    public = request.data.get('public', False)
    use_uuid = request.data.get('use_uuid', False)
    use_object3d = request.data.get('use_object3d', False)

    if isinstance(public, str):
        if public.lower() == 'on' or public.lower() == 'true':
            public = True
    if isinstance(use_uuid, str):
        if use_uuid.lower() == 'on' or use_uuid.lower() == 'true':
            use_uuid = True
    if isinstance(use_object3d, str):
        if use_object3d.lower() == 'on' or use_object3d.lower() == 'true':
            use_object3d = True

    if shape_file is None or not shape_file.name.endswith('.zip'):
        return Response({"message": "Sai định dạng. Định dạng yêu cầu *.zip"}, status=status.HTTP_400_BAD_REQUEST)
    # Đặt tạm field_dynamic = 1 để không trả ra lỗi
    valid_model = validate_model(name_display=name_display, field_dynamic=1)
    if valid_model.get('message') != "success":
        return Response(valid_model, status=status.HTTP_400_BAD_REQUEST)
    model_schema = None
    insert_to_folder = None
    m_shapefile = None
    try:
        m_shapefile = ManageShapeFileModel.objects.create(shape_file=shape_file,
                                                          created_by=request.user, name=name_display)
        zip_ref = zipfile.ZipFile(shape_file)
        path_unzip = f'{m_shapefile.shape_file.url[0:-4]}/'  # Tên file zip bỏ đuôi .zip
        zip_ref.extractall(path=path_unzip)
        filenames = [y for y in sorted(zip_ref.namelist()) for ending in ['dbf', 'prj', 'shp', 'shx'] if
                     y.endswith(ending)]
        dbf, prj, shp, shx = filenames
        shape = fiona.open(path_unzip + shp)
        schema = shape.schema
        type_geometry = schema.get('geometry')
        ordered_dict = schema["properties"]
        values = list(ordered_dict.values())
        keys = list(ordered_dict.keys())
        keys.insert(0, "geom")
        types = [type_geometry.lower()]
        max = [0]
        for value in values:
            try:
                t, m = value.split(":")
            except:
                t = value
                m = 0
            types.append(t)
            a = math.ceil(float(m))
            max.append(a)
        df = gpd.read_file(path_unzip + shp, encoding='utf8')
        # gdf = gpd.GeoDataFrame(df).set_crs(CRS.from_epsg(4326), allow_override=True).iterrows()
        # Create model
        model_schema = ModelSchema.objects.create(name=model_name, use_uuid=use_uuid, use_object3d=use_object3d)
        table_name = f'tb_dynamic_{model_name.lower()}'
        # Create fields
        for index in range(len(keys)):
            name_field = keys[index]
            type_field = types[index]
            if type_field == "str":
                type_field = "character"
            elif type_field == "int":
                type_field = "integer"
            FieldSchema.objects.create(
                name=no_accent_vietnamese(name_field).lower(),
                data_type=type_field,
                model_schema=model_schema,
                max_length=max[index],
                null=True,
                blank=True,
                unique=False)
        if use_object3d:
            name = default_name_field_dynamic.get('object3d')
            FieldSchema.objects.create(
                name=name,
                data_type='character',
                max_length=50,
                model_schema=model_schema,
                null=True,
                blank=True,
                unique=False,
                verbose_name="Đối tượng 3D")
        # get wms info
        # Đăng ký model
        reg_model = model_schema.as_model()
        admin.site.register(reg_model)
        reload(import_module(settings.ROOT_URLCONF))
        clear_url_caches()
        # insert dữ liệu
        MyModel = model_schema.as_model()
        import_data_from_geodataframe(df, MyModel)
        insert_to_folder = ModelDynamicFolder.objects.create(name_display=name_display, model=model_name,
                                                             updated_by=request.user,
                                                             created_by=request.user, public=public, use_geom=True,
                                                             description=description,
                                                             tags=tags, alias=alias)

        # recalculate_bbox()
        # insert_to_folder.save()
        return Response(ModelDynamicFolderDetailSerializer(insert_to_folder, context={"request": request}).data,
                        status=status.HTTP_201_CREATED)
    except Exception as e:
        if isinstance(m_shapefile, ManageShapeFileModel):
            m_shapefile.delete()
        if isinstance(insert_to_folder, ModelDynamicFolder):
            insert_to_folder.delete()
        if isinstance(model_schema, ModelSchema):
            model_schema.delete()
        if str(e) == "not enough values to unpack (expected 4, got 0)":
            return Response({"message": "Shapefile không hợp lệ"}, status=400)
        return Response({"message": str(e)}, status=400)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def api_create_models_from_geojson(request):
    geojson = request.data.get('geojson')
    fields_ignore = request.data.get('fields_ignore', [])
    if isinstance(fields_ignore, str):
        fields_ignore = ast.literal_eval(fields_ignore)
    use_file = False
    if request.FILES and geojson is not None:
        if geojson is None or not geojson.name.endswith('.geojson'):
            return Response({"message": "Sai định dạng. Định dạng yêu cầu *.geojson"},
                            status=status.HTTP_400_BAD_REQUEST)
        use_file = True
        data_json = json.load(geojson)
    elif geojson is not None:
        data_json = geojson
    else:
        return Response({"message": "Dữ liệu không hợp lệ."}, status=status.HTTP_400_BAD_REQUEST)
    name_display = request.data.get('name_display')
    model_name = set_name_model(name_display)
    model_check = [model.__name__.lower() for model in apps.get_app_config("app_dynamic").get_models()]
    while model_name.lower().strip() in model_check:
        model_name = set_name_model(name_display)
    alias = request.data.get('alias')
    description = request.data.get('description')
    tags = request.data.get('tags')
    public = request.data.get('public', True)
    use_uuid = request.data.get('use_uuid', False)
    use_object3d = request.data.get('use_object3d', False)
    if isinstance(public, str):
        if public.lower() == 'on' or public.lower() == 'true':
            public = True
    if isinstance(use_uuid, str):
        if use_uuid.lower() == 'on' or use_uuid.lower() == 'true':
            use_uuid = True
    if isinstance(use_object3d, str):
        if use_object3d.lower() == 'on' or use_object3d.lower() == 'true':
            use_object3d = True

    # Đặt tạm field_dynamic = 1 để không trả ra lỗi
    valid_model = validate_model(name_display=name_display, field_dynamic=1)
    if valid_model.get('message') != "success":
        return Response(valid_model, status=status.HTTP_400_BAD_REQUEST)
    model_schema = None
    insert_to_folder = None
    m_geojson = None
    try:
        # Tạm thời chưa lưu json nếu muốn lưu json thì truyền data_json vào
        m_geojson = ManageGeojsonModel.objects.create(json=data_json,
                                                      created_by=request.user, name=name_display)
        m_geojson.file = geojson if use_file else None
        m_geojson.save()

        # Create model
        model_schema = ModelSchema.objects.create(name=model_name, use_uuid=use_uuid, use_object3d=use_object3d)
        # Load fields để tạo model
        data_features = data_json.get("features")
        fields = data_features[0].get("properties")
        # list_key = []

        # ignored_fields
        full_fields = list(fields.keys())
        for field_ignore in fields_ignore:
            full_fields.remove(field_ignore)

        for key in full_fields:
            value = fields.get(key)
            type_field = "character"
            if isinstance(value, int):
                type_field = "integer"
            elif isinstance(value, float):
                type_field = "float"
            elif isinstance(value, bool):
                type_field = "boole"
            elif isinstance(value, dict):
                type_field = "json"
            FieldSchema.objects.create(
                name=no_accent_vietnamese(key).lower(),
                data_type=type_field,
                model_schema=model_schema,
                max_length=500,
                null=True,
                blank=True,
                unique=False)
            # list_key.append(key.lower())

        if use_object3d:
            name = default_name_field_dynamic.get('object3d')
            FieldSchema.objects.create(
                name=name,
                data_type='character',
                max_length=50,
                model_schema=model_schema,
                null=True,
                blank=True,
                unique=False,
                verbose_name="Đối tượng 3D")
        type_geom = data_features[0].get("geometry").get("type")
        FieldSchema.objects.create(
            name="geom",
            data_type=type_geom.lower(),
            model_schema=model_schema,
            null=True,
            blank=True,
            unique=False)
        # list_key.append("geom")
        # list_key.append("id")

        # get wms info

        MyModel = model_schema.as_model()
        gdf = gpd.GeoDataFrame.from_features(data_json['features'])
        for field_ignore in fields_ignore:
            gdf = gdf.drop(field_ignore, axis=1)
        import_data_from_geodataframe(gdf, MyModel)

        insert_to_folder = ModelDynamicFolder.objects.create(name_display=name_display, model=model_name,
                                                             updated_by=request.user,
                                                             created_by=request.user, public=public, use_geom=True,
                                                             description=description,
                                                             alias=alias, tags=tags)

        return Response(ModelDynamicFolderDetailSerializer(insert_to_folder, context={"request": request}).data,
                        status=status.HTTP_201_CREATED)
    except Exception as e:
        if isinstance(m_geojson, ManageGeojsonModel):
            m_geojson.delete()
        if isinstance(insert_to_folder, ModelDynamicFolder):
            insert_to_folder.delete()
        if isinstance(model_schema, ModelSchema):
            model_schema.delete()
        return Response({"message": str(e)}, status=400)


def validate_model(name_display: str, field_dynamic: any) -> dict:
    if not name_display:
        return {'message': 'Vui lòng nhập name_display - name_display is required'}
    if not field_dynamic:
        return {'message': 'fields is required and fields is array object'}
    return {'message': 'success'}
