from django.apps import apps

def handle_delete_layer(instance):
    model_name = instance.model
    model_object = apps.get_model(f'app_dynamic.ModelSchema').objects.get(name=model_name)
    foreign_check = apps.get_model(f'app_dynamic.FieldSchema').objects.filter(model_foreign=model_object.name)
    if foreign_check.exists():
        raise Exception(
            "Không thể xóa do mô hình đang được phụ thuộc khóa ngoại với mô hình {}".format(
                foreign_check.first().model_schema.name))
    # model_object._factory.unregister_model()
    model_object.delete()


