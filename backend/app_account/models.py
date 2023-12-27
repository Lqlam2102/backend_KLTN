import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from rest_framework import serializers


# Create your models here.
class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
    MALE, FEMALE, OTHER = range(3)
    GENDER = [
        (MALE, 'Nam'),
        (FEMALE, 'Nữ'),
        (OTHER, 'Khác')
    ]
    gender = models.PositiveSmallIntegerField(choices=GENDER, default=MALE, verbose_name="Giới tính",
                                              help_text='1. Nam \n'
                                                        '2. Nữ \n'
                                                        '3. Khác \n')
    photo = models.ImageField(
        upload_to=f'avatar/%Y/%m/%d',
        blank=True,
        default='photos/avatar-1.jpg',
        null=True,
        verbose_name="Ảnh đại diện"
    )

    def save(self, *args, **kwargs):
        mail_check = User.objects.filter(email=self.email, is_active=True)
        if mail_check.exists() and self not in mail_check:
            raise serializers.ValidationError(
                {"message": "Email đã được liên kết với một tài khoản khác."})
        username_check = User.objects.filter(username=self.username, is_active=True)
        if username_check.exists() and self not in username_check:
            serializers.ValidationError(
                {"message": "Tên đăng nhập đã tồn tại."})
        super().save(*args, **kwargs)


    def __str__(self):
        return self.username
    class Meta:
        ordering = ['id']
        db_table = 'auth_user'
        verbose_name = 'Người dùng'
        verbose_name_plural = 'Tất cả người dùng'