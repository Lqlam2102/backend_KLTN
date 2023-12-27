from django.db import models

# Create your models here.
import uuid
from django.db import models


class MyBase(models.Model):
    class Meta:
        abstract = True

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
    created_date = models.DateTimeField(auto_now_add=True, verbose_name="Ngày khởi tạo")
    updated_date = models.DateTimeField(auto_now=True, verbose_name="Ngày cập nhật")
    is_active = models.BooleanField(default=True, verbose_name="Hoạt động",
                                    help_text="Chỉ định xem đối tượng này còn được coi là đang hoạt động. Bạn nên bỏ chọn này thay vì xóa đối tượng.")

    def delete(self, *args, **kwargs):
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