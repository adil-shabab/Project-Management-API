# serializers.py
from rest_framework import serializers

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True)
    key = serializers.CharField(max_length=255)
