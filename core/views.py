from django.contrib.auth import authenticate
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from django.conf import settings
from rest_framework.permissions import AllowAny
from .serializers import *
from .models import User
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
import logging
from rest_framework.parsers import JSONParser
from django.contrib.auth import get_user_model
from rest_framework.parsers import MultiPartParser, FormParser
from django.core.exceptions import ValidationError
from django.utils.dateparse import parse_datetime
from django.db.models import Q
from django.utils.timezone import localdate, make_aware
from django.utils.timezone import now
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import datetime



class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            username = serializer.validated_data['username']  # Change to 'email' if your model uses email
            password = serializer.validated_data['password']
            key = serializer.validated_data['key']

            # Validate API key
            if key != settings.SECRET_KEY_API:
                return Response({"detail": "Invalid key"}, status=status.HTTP_400_BAD_REQUEST)

            # Authenticate user
            user = authenticate(request, username=username, password=password)

            if user is not None:
                # Generate JWT tokens for the authenticated user
                refresh = RefreshToken.for_user(user)
                return Response({
                    "detail": "Login successful",
                    "access_token": str(refresh.access_token),
                    "refresh_token": str(refresh),
                }, status=status.HTTP_200_OK)

            return Response({"detail": "Invalid credentials"}, status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)





# Configure logger
logger = logging.getLogger(__name__)

class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]  # Ensure the user is authenticated

    def get(self, request):
        # Debugging: Check if the token is coming in the headers
        logger.debug(f"Authorization Header: {request.headers.get('Authorization')}")

        # Using JWTAuthentication to authenticate the user
        authentication = JWTAuthentication()
        user, auth = authentication.authenticate(request)

        if user:
            user_data = {
                'username': user.username,
                'full_name': user.full_name,
                'email': user.email,
                'role': user.role,
                'department': user.department,
                'position': user.position,
                'phone_number': user.phone_number,
            }
            
            # Only add 'avatar' to the response if it exists
            if user.avatar:
                user_data['avatar'] = user.avatar.url

            return Response(user_data)

        else:
            return Response({"detail": "User not authenticated."}, status=401)





User = get_user_model()
class EditProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request):
        # Authenticate the user
        user = request.user

        # Parse request data
        data = JSONParser().parse(request)

        # Validate and update the fields
        full_name = data.get('full_name')
        email = data.get('email')
        phone_number = data.get('phone_number')

        errors = {}
        if not full_name:
            errors['full_name'] = "Full Name is required."
        if not email:
            errors['email'] = "Email is required."
        elif User.objects.filter(email=email).exclude(pk=user.pk).exists():
            errors['email'] = "This email is already in use."
        if not phone_number:
            errors['phone_number'] = "Phone Number is required."
        elif not phone_number.isdigit() or len(phone_number) != 10:
            errors['phone_number'] = "Phone Number must be exactly 10 digits."

        if errors:
            return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

        # Update the user instance
        user.full_name = full_name
        user.email = email
        user.phone_number = phone_number
        user.save()

        # Prepare the response data
        response_data = {
            'message': "Profile updated successfully",
            'data': {
                'phone_number': user.phone_number,
                'username': user.username,
                'full_name': user.full_name,
                'email': user.email,
                'role': user.role,
                'department': user.department,
                'position': user.position,
            }
        }

        # Only add 'avatar' to the response if it exists
        if user.avatar:
            response_data['data']['avatar'] = user.avatar.url

        return Response(response_data, status=status.HTTP_200_OK)




class EditAvatarView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def put(self, request):
        user = request.user  # Get the authenticated user

        # Check if there's a new avatar in the request
        avatar = request.FILES.get('avatar')
        if not avatar:
            return Response({'error': 'No avatar provided.'}, status=status.HTTP_400_BAD_REQUEST)

        # Validate that the avatar is an image file
        if not avatar.name.endswith(('jpg', 'jpeg', 'png', 'gif')):
            return Response({'error': 'File type not supported. Please upload a valid image file.'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Save the avatar
        try:
            user.avatar = avatar  # Set the avatar
            user.save()  # Save the user object with the new avatar

            return Response({
                'message': 'Avatar updated successfully.',
                'data': {
                    'avatar': user.avatar.url,
                    'phone_number': user.phone_number,
                    'username': user.username,
                    'full_name': user.full_name,
                    'email': user.email,
                    'role': user.role,
                    'department': user.department,
                    'position': user.position,
                }
            }, status=status.HTTP_200_OK)
        
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)












class CreateTaskForMeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user  # Get the logged-in user

        # Pass the context to include FILES (images) and request context
        serializer = TaskSerializer(data=request.data, context={'request': request, 'user': user})

        if serializer.is_valid():
            task = serializer.save()  # Save the task with the user data
            return Response({
                "message": "Task created successfully!",
                "data": serializer.data,
            }, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)




class UserTasksWithTodayStartDateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Get the logged-in user
        user = request.user

        # Get today's date
        today = localdate()

        # Fetch tasks for the logged-in user where start_date is today
        tasks = Task.objects.filter(
            Q(user=user) &
            Q(start_date__date=today)
        )

        # Serialize the tasks
        serializer = TaskSerializer(tasks, many=True)

        return Response({
            "message": "Tasks with today's start date retrieved successfully!",
            "data": serializer.data
        }, status=status.HTTP_200_OK)







class UserPendingTasksView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Get the logged-in user
        user = request.user

        # Current date and time
        current_time = now()

        # Fetch tasks for the logged-in user with specified conditions
        tasks = Task.objects.filter(
            Q(user=user) & (
                # Tasks that are ongoing: start_date in the past and due_date in the future
                Q(start_date__lt=current_time, due_date__gt=current_time) |  
                
                # Tasks that are overdue: due_date in the past and status is not 'approved'
                Q(due_date__lt=current_time)
            )
        ).exclude(status='approved')  # Exclude tasks with 'approved' status

        # Serialize the tasks
        serializer = TaskSerializer(tasks, many=True)

        return Response({
            "message": "Pending tasks retrieved successfully!",
            "data": serializer.data
        }, status=status.HTTP_200_OK)
        


class TaskDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, task_id):
        try:
            task = Task.objects.get(id=task_id, user=request.user)
            serializer = TaskSerializer(task)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Task.DoesNotExist:
            return Response(
                {"error": "Task not found or you do not have permission to view it."},
                status=status.HTTP_404_NOT_FOUND,
            )






class ChangeTaskStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, task_id):
        # Get the task by ID
        task = get_object_or_404(Task, id=task_id, user=request.user)

        # Check if the current status is 'pending'
        if task.status != 'pending':
            return Response(
                {"message": "The task status is not pending, cannot move to review."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Change the task status to 'in_review'
        task.status = 'in_review'
        task.review_date = timezone.now()
        task.save()

        # Serialize the updated task
        serializer = TaskSerializer(task)

        return Response(
            {
                "message": "Task status changed to 'In Review' successfully.",
                "data": serializer.data
            },
            status=status.HTTP_200_OK
        )







class UserSpecificDateTasksView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, specific_date):
        # Get the logged-in user
        user = request.user

        # Convert the specific date (e.g., '25-11-2024') to a datetime object
        try:
            specific_date = datetime.strptime(specific_date, '%d-%m-%Y')  # Date format: 'dd-mm-yyyy'
            specific_date = make_aware(specific_date)  # Make it timezone-aware
        except ValueError:
            return Response({"message": "Invalid date format. Please use 'dd-mm-yyyy'."}, status=status.HTTP_400_BAD_REQUEST)

        # Fetch tasks for the logged-in user that match the criteria:
        # - Tasks where start_date's date part is less than or equal to the specific date
        # - Tasks where due_date's date part is greater than or equal to the specific date
        tasks = Task.objects.filter(
            user=user,
            start_date__date__lte=specific_date.date(),  # Use only the date part of start_date
            due_date__date__gte=specific_date.date()     # Use only the date part of due_date
        )

        # Serialize the tasks
        serializer = TaskSerializer(tasks, many=True)

        return Response({
            "message": "Tasks for the specified date retrieved successfully!",
            "data": serializer.data
        }, status=status.HTTP_200_OK)










class UserSpecificDateRangeTasksView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, start_date, end_date):
        # Get the logged-in user
        user = request.user

        # Convert the start and end dates (e.g., '25-11-2024') to datetime objects
        try:
            start_date = datetime.strptime(start_date, '%d-%m-%Y')  # Date format: 'dd-mm-yyyy'
            start_date = make_aware(start_date)  # Make it timezone-aware
            end_date = datetime.strptime(end_date, '%d-%m-%Y')  # Date format: 'dd-mm-yyyy'
            end_date = make_aware(end_date)  # Make it timezone-aware
        except ValueError:
            return Response({"message": "Invalid date format. Please use 'dd-mm-yyyy'."}, status=status.HTTP_400_BAD_REQUEST)

        # Fetch tasks for the logged-in user that match the criteria:
        # - Tasks where the start_date's date part is on or after the start date
        # - Tasks where the due_date's date part is on or before the end date
        tasks = Task.objects.filter(
            user=user,
            start_date__date__gte=start_date.date(),  # Use only the date part of start_date
            due_date__date__lte=end_date.date()       # Use only the date part of due_date
        )

        # Serialize the tasks
        serializer = TaskSerializer(tasks, many=True)

        return Response({
            "message": "Tasks for the specified date range retrieved successfully!",
            "data": serializer.data
        }, status=status.HTTP_200_OK)