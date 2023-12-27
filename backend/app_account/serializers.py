from rest_framework import serializers

from app_account.models import User
from backend.settings import BASE_URL


class UserCustomOverviewSerializer(serializers.ModelSerializer):
    # organization = serializers.SerializerMethodField()
    # user_role = serializers.SerializerMethodField()
    photo = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'photo', 'date_joined']

    def get_photo(self, obj):
        request = self.context['request']
        if obj.photo:
            return request.build_absolute_uri(obj.photo.url)
        else:
            return None

class UserCustomSerializer(serializers.ModelSerializer):
    photo = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'gender', 'photo', 'date_joined', 'password']
        extra_kwargs = {
            'password': {'write_only': 'true', 'required': False},
            'email': {'required': True},
        }

    def get_photo(self, obj):
        request = self.context['request']
        if obj.photo:
            return request.build_absolute_uri(obj.photo.url)
        else:
            return None


    def create(self, validated_data):
        request = self.context.get('request')
        avatar = request.data.get('photo')
        password = request.data.get('password')
        validated_data["photo"] = avatar
        user = User(**validated_data)
        user.set_password(password)
        user.is_active = True
        user.save()
        return user

    def update(self, instance, validated_data):
        request = self.context.get('request')
        password = request.data.get('password')
        avatar = request.data.get('photo')
        if avatar:
            if not isinstance(avatar, str):
                validated_data["photo"] = avatar
            else:
                validated_data["photo"] = instance.photo
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance
