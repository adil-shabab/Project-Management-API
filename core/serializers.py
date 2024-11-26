# serializers.py
from rest_framework import serializers
from .models import *

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True)
    key = serializers.CharField(max_length=255)




class TaskImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskImage
        fields = ['image']



class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for the User model to include user details.
    """
    class Meta:
        model = User
        fields = ['id', 'username', 'full_name', 'avatar']  # Add other fields if needed



class TaskSerializer(serializers.ModelSerializer):
    images = TaskImageSerializer(many=True, required=False)
    assigned_by = UserSerializer(read_only=True)  # To display assigned user info
    user = UserSerializer(read_only=True)  # To display task owner info

    class Meta:
        model = Task
        fields = ['id', 'title', 'approved_date', 'review_date', 'description', 'due_date', 'start_date', 'priority', 'user', 'assigned_by', 'is_ticket', 'status', 'images']

    def create(self, validated_data):
        # Extract files from the context
        images_data = self.context['request'].FILES.getlist('images', [])
        user = self.context['user']  # Access the user from context

        # Manually assign user and assigned_by fields
        validated_data['assigned_by'] = user
        validated_data['user'] = user

        # Create the Task object
        task = Task.objects.create(**validated_data)

        # Save images related to the task
        for image in images_data:
            TaskImage.objects.create(task=task, image=image)

        return task
