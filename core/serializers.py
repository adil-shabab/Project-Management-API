# serializers.py
from rest_framework import serializers
from .models import *
import re
from django.db import transaction
import logging

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True)
    key = serializers.CharField(max_length=255)



class AttendanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attendance
        fields = '__all__'


class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = ['id', 'title']


class TaskImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskImage
        fields = ['image']

class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for the User model to include user details.
    """
    password = serializers.CharField(write_only=True, required=False)  # Password is write-only

    class Meta:
        model = User
        fields = [
            'id', 'username', 'full_name', 'avatar', 'email', 'user_id',
            'position', 'role', 'phone_number', 'department', 'password'
        ]

    def to_representation(self, instance):
        """Customize response to hide the hashed password"""
        data = super().to_representation(instance)
        data['password'] = "********"  # here i wan to pass exact password in text format
        return data
        


class LeaveSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)  # To display task owner info

    class Meta:
        model = Leave
        fields = '__all__'



class TaskSerializerManager(serializers.ModelSerializer):
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
        to_user = self.context['to_user']  # Access the user from context

        
        to_user = User.objects.get(id=int(to_user))
        print(to_user)

        # Manually assign user and assigned_by fields
        validated_data['assigned_by'] = user
        validated_data['user'] = to_user

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
        
        
        
class ProjectSerializer(serializers.ModelSerializer):
    members = ProjectMemberSerializer(many=True)
    images = ProjectImageSerializer(many=True)
    team_lead = UserSerializer()  # Nested serializer to get team lead details


    class Meta:
        model = Project
        fields = ['id', 'title', 'description', 'department', 'client_name', 'due_date', 'start_date', 
                  'status', 'priority', 'team_lead', 'created_by', 'created_at', 'members', 'images']


class ProjectSerializerCreate(serializers.ModelSerializer):
    team_lead = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())  # Expecting an ID, not a full object

    class Meta:
        model = Project
        fields = ['id', 'title', 'description', 'department', 'client_name', 'due_date', 'start_date', 
                  'status', 'priority', 'team_lead', 'created_by', 'created_at']








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

class TaskSerializerNew(serializers.ModelSerializer):
    images = TaskImageSerializer(many=True, required=False)
    assigned_by = UserSerializer(read_only=True)
    user = UserSerializer(read_only=True)
    project = ProjectSerializer(read_only=True)
    client = serializers.PrimaryKeyRelatedField(queryset=Client.objects.all(), required=True)
    client_title = serializers.CharField(source='client.title', read_only=True)

    class Meta:
        model = Task
        fields = [
            'id', 'title', 'approved_date', 'review_date', 'description', 
            'due_date', 'start_date', 'priority', 'user', 'assigned_by', 
            'is_ticket', 'status', 'images', 'project', 'client', 'client_title'
        ]
        extra_kwargs = {
            'title': {'required': True},
            'description': {'required': True},
            'priority': {'required': True},
            'assigned_by': {'required': True},
            'client': {'required': True},
            'user': {'required': True},
        }

    def create(self, validated_data):
        images_data = self.context['request'].FILES.getlist('images', [])
        user = self.context['user']
        
        # Validate required fields
        required_fields = ['title', 'description', 'priority', 'client']
        for field in required_fields:
            if field not in validated_data or validated_data[field] is None:
                raise serializers.ValidationError({field: f"{field.capitalize()} is required."})
        
        # Extract user data from request data for creation
        user_data = self.context['request'].data.get('user')
        if not user_data:
            raise serializers.ValidationError({'user': 'User is required.'})
        
        try:
            assigned_to_user = User.objects.get(id=user_data)
        except User.DoesNotExist:
            raise serializers.ValidationError({'user': 'User not found'})
        
        validated_data['assigned_by'] = user
        validated_data['user'] = assigned_to_user
        
        # Create task
        task = Task.objects.create(**validated_data)
        
        # Add images
        for image in images_data:
            TaskImage.objects.create(task=task, image=image)
            
        return task





class TaskSerializer(serializers.ModelSerializer):
    images = TaskImageSerializer(many=True, required=False)
    assigned_by = UserSerializer(read_only=True)  # To display assigned user info
    user = UserSerializer(read_only=True)  # To display task owner info
    project = ProjectSerializer(read_only=True) # To display
    client = serializers.PrimaryKeyRelatedField(queryset=Client.objects.all(), required=True)
    client_title = serializers.CharField(source='client.title', read_only=True)

    class Meta:
        model = Task
        fields = ['id', 'title', 'client', 'client_title', 'approved_date', 'review_date', 'description', 'due_date', 'start_date', 'priority', 'user', 'assigned_by', 'is_ticket', 'status', 'images', 'project']

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




# Set up logging
logger = logging.getLogger(__name__)

class UserSerializerComment(serializers.ModelSerializer):
    avatar = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'full_name', 'avatar']

    def get_avatar(self, obj):
        if hasattr(obj, 'profile') and obj.profile.avatar:
            return obj.profile.avatar.url if obj.profile.avatar else None
        return None


class CommentSerializer(serializers.ModelSerializer):
    commented_by = UserSerializer(read_only=True)
    mentions = UserSerializerComment(many=True, read_only=True)
    content = serializers.CharField(max_length=1000, trim_whitespace=True)

    class Meta:
        model = Comment
        fields = ['id', 'content', 'commented_by', 'created_at', 'task', 'mentions']
        read_only_fields = ['id', 'created_at', 'commented_by']
        extra_kwargs = {'task': {'write_only': True}}

    def create(self, validated_data):
        # Simplified create method, as logic is now in the view
        return Comment.objects.create(
            content=validated_data['content'],
            commented_by=self.context['request'].user,
            task=validated_data['task']
        )






        


class TaskStatusChangeSerializer(serializers.ModelSerializer):
    task_title = serializers.CharField(source='task.title', read_only=True)
    changed_by_username = serializers.CharField(source='changed_by.full_name', read_only=True)

    class Meta:
        model = TaskStatusChange
        fields = [
            'id', 'task', 'task_title', 'due_date', 'start_date', 'priority', 
            'created_at', 'status', 'reason', 'changed_by', 'changed_by_username'
        ]
        read_only_fields = ['id', 'created_at']

class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    

    class Meta:
        model = User
        fields = ['username', 'user_id', 'password', 'full_name', 'email', 'phone_number', 'position', 'role', 'department']

    def create(self, validated_data):
        # Use `create_user` method from UserManager for password hashing
        password = validated_data.pop('password')
        user = User.objects.create(**validated_data)
        user.set_password(password)  # Hash the password
        user.save()
        return user

        



class NotificationSerializer(serializers.ModelSerializer):
    created_by = UserSerializer(read_only=True)  # The logged-in user who assigns the task

    class Meta:
        model = Notification
        fields = ['id', 'message', 'created_by', 'created_at', 'read_status', 'type', 'project', 'task', 'leave']



class TaskHistorySerializer(serializers.ModelSerializer):
    changed_by = UserSerializer(read_only=True)  # To display task owner info
    class Meta:
        model = TaskHistory
        fields = ['id', 'task', 'status', 'changed_by', 'changed_at', 'notes', 'reason']




        