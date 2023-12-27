import json
import re

from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from oauth2_provider.views.mixins import OAuthLibMixin
from django.views import View
from django.views.decorators.debug import sensitive_post_parameters
from django.contrib.auth import authenticate
from django.http import HttpResponse, JsonResponse
from oauth2_provider.models import get_access_token_model
from oauth2_provider.signals import app_authorized

# Create your views here.
# login
from rest_framework import permissions, viewsets, generics, status
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response

from app_account.models import User
from app_account.serializers import UserCustomOverviewSerializer, UserCustomSerializer
from app_api_gate_way.paginator import CustomPagination
from backend.config import OAUTH2_INFO
from backend.cores import no_accent_vietnamese


@method_decorator(csrf_exempt, name="dispatch")
class TokenView(OAuthLibMixin, View):
    """
    Implements an endpoint to provide access tokens

    The endpoint is used in the following flows:
    * Authorization code
    * Password
    * Client credentials
    """

    @method_decorator(sensitive_post_parameters("password"))
    def post(self, request, *args, **kwargs):
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = None
        if request.POST.get('grant_type') == 'refresh_token':
            post = request.POST.copy()
            post['client_id'] = OAUTH2_INFO['client_id']
            post['client_secret'] = OAUTH2_INFO['client_secret']
            request.POST = post
        else:
            post = request.POST.copy()
            post['client_id'] = OAUTH2_INFO['client_id']
            post['client_secret'] = OAUTH2_INFO['client_secret']
            post['grant_type'] = 'password'
            request.POST = post
            user = authenticate(username=username, password=password)
            if not user:
                # Thông tin tài khoản hoặc mật khẩu không chính xác
                return JsonResponse({
                    "message": "Username or password are incorrect!",
                }, status=400)
        url, headers, body, status = self.create_token_response(request)
        if status == 200:
            access_token = json.loads(body).get("access_token")
            if access_token is not None:
                body_json = json.loads(body)
                token = get_access_token_model().objects.get(token=access_token)
                body_json['id'] = str(token.user_id)
                # HCM GIS
                # url = 'https://khucongnghiep.hcmgis.vn/login-token/'
                # params = {'access_token': str(token)}
                # grequests.get(url, params=params)
                if request.POST.get('grant_type') == 'refresh_token':
                    user = User.objects.get(pk=token.user_id)
                body = json.dumps(body_json)
                app_authorized.send(sender=self, request=request, token=token)
                if request.POST.get('grant_type') != 'refresh_token':
                    user.save()
        response = HttpResponse(content=body, status=status)

        for k, v in headers.items():
            response[k] = v
        return response


class UserCustomAPIView(viewsets.ViewSet, generics.ListAPIView, generics.CreateAPIView, generics.RetrieveAPIView,
                        generics.UpdateAPIView, generics.DestroyAPIView):
    parser_classes = [MultiPartParser, FormParser]
    pagination_class = CustomPagination

    def get_serializer_class(self):
        if self.action == 'list':
            return UserCustomOverviewSerializer
        else:
            return UserCustomSerializer

    def get_permissions(self):
        if self.action in ['get_current_user', 'retrieve', 'get_diary_bookmark', 'action_change_password',
                           'get_application_system']:
            return [permissions.IsAuthenticated()]
        elif self.action in ['create', 'authentication_user', 'send_new_authentication_code', 'preload', 'list',
                             'export-excel']:
            return [permissions.AllowAny()]

    def get_queryset(self):
        list_obj = User.objects.filter(is_active=True)
        request = self.request
        email = request.query_params.get('email')
        if email is not None:
            list_search_email = [obj.id for obj in list_obj if
                                 re.search(no_accent_vietnamese(email).lower(),
                                           no_accent_vietnamese(obj.email).lower())]
            list_obj = list_obj.filter(id__in=list_search_email)
        return list_obj

    @action(methods=['get'], detail=False, url_path='current-user')
    def get_current_user(self, request):
        if not request.user.is_anonymous:
            return Response(self.get_serializer_class()(request.user, context={"request": request}).data,
                            status=status.HTTP_200_OK)
        else:
            return JsonResponse({'message': 'Error, not found user'}, status=400)
