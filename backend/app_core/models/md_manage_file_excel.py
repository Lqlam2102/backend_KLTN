from django.db import models
from app_account.models import User


# Create your models here.


def upload_to(instance, filename):
    return f'file_excel/{filename}'


class ManageFileExcelModel(models.Model):
    class Meta:
        db_table = 'tb_manage_file_excel'
        verbose_name = 'Quản lý file excel'
        verbose_name_plural = 'Quản lý file excel'

    name = models.CharField(max_length=100, verbose_name="Tên hiển thị", null=True, blank=True)
    file = models.FileField(verbose_name="File excel", upload_to=upload_to, null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cre_excel', blank=True,
                                   null=True, verbose_name="Người khởi tạo")

    def __str__(self):
        return self.name
