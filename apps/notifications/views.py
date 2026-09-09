from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .device_tokens import register_device_token, unregister_device_token
from .models import DevicePlatform


class DeviceTokenSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=255)
    platform = serializers.ChoiceField(choices=DevicePlatform.choices, default=DevicePlatform.ANDROID)


class DeviceTokenRegisterView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = DeviceTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        register_device_token(user=request.user, **serializer.validated_data)
        return Response(status=status.HTTP_201_CREATED)


class DeviceTokenUnregisterView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        token = request.data.get("token")
        if not token:
            raise serializers.ValidationError({"token": "Обязательное поле."})
        unregister_device_token(user=request.user, token=token)
        return Response(status=status.HTTP_204_NO_CONTENT)
