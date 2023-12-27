from django.db import models
from app_account.models import User

# Create your models here.


def upload_to(instance, filename):
    return f'shapefile/{filename}'


class ManageShapeFileModel(models.Model):
    class Meta:
        db_table = 'tb_manage_shapefile'
        verbose_name = 'Quản lý shapefile'
        verbose_name_plural = 'Quản lý shapefile'

    name = models.CharField(max_length=100, verbose_name="Tên hiển thị", null=True, blank=True)
    shape_file = models.FileField(verbose_name="Shapefile", upload_to=upload_to)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cre_shape_file', blank=True,
                                   null=True, verbose_name="Người khởi tạo")

    def __str__(self):
        return self.shape_file.name

