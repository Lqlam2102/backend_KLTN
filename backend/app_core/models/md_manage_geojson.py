from django.db import models
from app_account.models import User


# Create your models here.


def upload_to(instance, filename):
    return f'file_geojson/{filename}'


class ManageGeojsonModel(models.Model):
    class Meta:
        db_table = 'tb_manage_geojson_file'
        verbose_name = 'Quản lý file geojson'
        verbose_name_plural = 'Quản lý file geojson'

    name = models.CharField(max_length=100, verbose_name="Tên hiển thị", null=True, blank=True)
    file = models.FileField(verbose_name="File Geojson", upload_to=upload_to, null=True, blank=True)
    json = models.JSONField(verbose_name="Geojson", null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cre_geojson', blank=True,
                                   null=True, verbose_name="Người khởi tạo")

    def __str__(self):
        return self.name
