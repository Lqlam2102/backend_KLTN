import uuid

from django.apps import apps
from django.db import models
from app_account.models import User
from app_api_gate_way.models import MyBase
from app_core.cores import handle_delete_layer
from app_dynamic.models import ModelSchema, FieldSchema


class ModelDynamicFolder(MyBase):
    class Meta:
        db_table = 'tb_model_dynamic_folder'
        verbose_name = 'Model dynamic - thư mục'
        verbose_name_plural = 'Các liên kết giữa model và thư mục'
    name_display = models.CharField(max_length=255, verbose_name="Tên hiển thị")
    model = models.CharField(max_length=100)
    alias = models.CharField(max_length=200, default="", null=True, blank=True)
    tags = models.CharField(max_length=100, verbose_name="Thẻ tên", null=True, blank=True)
    description = models.TextField(verbose_name="Mô tả", null=True, blank=True)
    public = models.BooleanField(default=False, help_text="Chế độ công khai")
    construct = models.JSONField(editable=False, default=dict)
    pin = models.ManyToManyField(User, related_name='dynamic_pin', verbose_name="Ghim", through='PinDynamic')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cre_model_dynamic_folder',
                                   blank=True,
                                   null=True, verbose_name="Người khởi tạo")
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='edit_model_dynamic_folder',
                                   blank=True,
                                   null=True, verbose_name="Người cập nhật")
    use_geom = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        self.construct = self.get_construct()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        handle_delete_layer(self)
        self.is_active = False
        self.save()
        # Xóa tất cả các đối tượng liên quan
        for related_object in self._meta.related_objects:
            related_name = related_object.get_accessor_name()
            try:
                related_queryset = getattr(self, related_name).filter(is_active=True)
            except:
                related_queryset = getattr(self, related_name).all()
            for related_instance in related_queryset:
                related_instance.delete()


    def get_construct(self):
        try:
            model = ModelSchema.objects.get(name=self.model)
            fields = FieldSchema.objects.filter(
                model_schema=model).values('id',
                                           'name',
                                           'data_type',
                                           'null',
                                           'blank',
                                           'unique',
                                           'default',
                                           'max_length',
                                           'verbose_name',
                                           'model_foreign')
            return {
                "use_uuid": model.use_uuid,
                "use_object3d": model.use_object3d,
                "fields": [field for field in fields]
            }

        except Exception as e:
            return {'message': str(e)}

    def __str__(self):
        return self.model


class PinDynamic(models.Model):
    class Meta:
        db_table = 'tb_model_dynamic_pin'
        verbose_name = 'Model Dynamic được gim'
        unique_together = ('user', 'data')
        default_permissions = []  # no permissions created

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
    data = models.ForeignKey(ModelDynamicFolder, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    order = models.PositiveSmallIntegerField(default=0, verbose_name='Thứ tự')

    def save(self, *args, **kwargs):
        max_order = PinDynamic.objects.aggregate(models.Max('order'))['order__max']
        if int(self.order) == 0:
            # This is a new instance, so we need to set the order field.
            self.order = max_order + 1 if max_order is not None else 1
        else:
            old_order = args[0].get('old_order')
            if old_order > int(self.order):
                PinDynamic.objects.filter(order__gte=self.order, order__lt=old_order).update(
                    order=models.F('order') + 1)
            else:
                if int(self.order) > max_order:
                    self.order = max_order
                PinDynamic.objects.filter(order__lte=self.order, order__gt=old_order).update(
                    order=models.F('order') - 1)
        super().save(*(), **kwargs)

    def delete(self, *args, **kwargs):

        PinDynamic.objects.filter(order__gt=self.order).update(
            order=models.F('order') - 1)
        super().delete(*args, **kwargs)


class TemplateDynamicModel(MyBase):
    class Meta:
        db_table = 'tb_template_dynamic_model'
        verbose_name = 'Mẫu dữ liệu động (Template model dynamic)'
        verbose_name_plural = 'Các mẫu dữ liệu động)'

    name = models.CharField(max_length=100, verbose_name="Tên mẫu cấu trúc")
    construct = models.JSONField(default=dict)
    description = models.TextField(blank=True, null=True, verbose_name="Mô tả")
