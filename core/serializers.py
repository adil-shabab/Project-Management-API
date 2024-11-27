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









# ProjectMember Serializer to include user role and details
class ProjectMemberSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    role = serializers.CharField()


    class Meta:
        model = ProjectMember
        fields = ['user', 'role']

# Project Image Serializer
class ProjectImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectImage
        fields = ['image']

# Project Serializer to include project details and project members
class ProjectSerializer(serializers.ModelSerializer):
    members = ProjectMemberSerializer(many=True)
    images = ProjectImageSerializer(many=True)
    team_lead = UserSerializer()  # Nested serializer to get team lead details


    class Meta:
        model = Project
        fields = ['id', 'title', 'description', 'department', 'client_name', 'due_date', 'start_date', 
                  'status', 'priority', 'team_lead', 'created_by', 'created_at', 'members', 'images']









class TicketTaskSerializer(serializers.ModelSerializer):
    images = TaskImageSerializer(many=True, required=False)
    assigned_by = UserSerializer(read_only=True)  # The logged-in user who assigns the task
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())  # The user the task is assigned to
    project = serializers.PrimaryKeyRelatedField(queryset=Project.objects.all())  # The project the task is associated with

    class Meta:
        model = Task
        fields = [
            'id', 'title', 'approved_date', 'review_date', 'description', 
            'due_date', 'start_date', 'priority', 'user', 'assigned_by', 
            'is_ticket', 'status', 'images', 'project'
        ]

    def create(self, validated_data):
        # Extract files from the context (if any)
        images_data = self.context['request'].FILES.getlist('images', [])
        user = self.context['user']  # The logged-in user making the request (assigned_by)

        # Ensure `assigned_by` is set to the logged-in user
        validated_data['assigned_by'] = user

        # Ensure `is_ticket` is set to True
        validated_data['is_ticket'] = True

        # Create the Task object
        task = Task.objects.create(**validated_data)

        # Save associated images if any
        for image in images_data:
            TaskImage.objects.create(task=task, image=image)

        return task








class NotificationSerializer(serializers.ModelSerializer):
    created_by = UserSerializer(read_only=True)  # The logged-in user who assigns the task

    class Meta:
        model = Notification
        fields = ['id', 'message', 'created_by', 'created_at', 'read_status', 'type', 'project', 'task']