from django.contrib.auth import authenticate
from rest_framework import generics
from rest_framework.exceptions import NotFound
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
                'id': user.id,
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





class CreateTaskManagerView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user  # Get the logged-in user


        # Log the parsed form data
        print("Parsed form data:", request.data['user'])

        to_user = request.data['user']

        # Check if the user's role is 'Staff'
        if user.role == 'Staff':
            return Response({
                "error": "Permission denied. Staff members are not allowed to create tasks."
            }, status=status.HTTP_403_FORBIDDEN)

        # Pass the context to include FILES (images) and request context
        serializer = TaskSerializerManager(data=request.data, context={'request': request, 'user': user, 'to_user': to_user})

        if serializer.is_valid():
            task = serializer.save()  # Save the task with the user data
            # Create a notification for the added user
            Notification.objects.create(
                user=task.user,
                message = f"{user.username} has assigned you a new task.",
                type='task',  # Notification type is 'project'
                task=task,  # Link the notification to the specific project
                created_by = user
            )
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
        
        
        # Current date (only date part)
        current_date = now().date()

        # Fetch tasks for the logged-in user with specified conditions
        tasks = Task.objects.filter(
            Q(user=user) & (
                # Tasks that are ongoing: start_date in the past and due_date in the future
                Q(start_date__date__lte=current_date, due_date__date__gte=current_date) |
                
                # Tasks that are overdue: due_date in the past and status is not 'approved'
                Q(due_date__date__lt=current_date)
            )
        )

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
            task = Task.objects.get(id=task_id)
            serializer = TaskSerializer(task)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Task.DoesNotExist:
            return Response(
                {"error": "Task not found or you do not have permission to view it."},
                status=status.HTTP_404_NOT_FOUND,
            )






class ChangeTaskStatusView(APIView):
    print("Comuing change task status")
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

        # notification___here
        managers = User.objects.filter(role = 'Manager')
        Admins = User.objects.filter(role = 'Admin')

        for x in managers:
            # Create a notification for the added user
            Notification.objects.create(
                user=x,
                message = f"{task.user.username} has been assigned a task to review.",
                type='task',  # Notification type is 'project'
                task=task,  # Link the notification to the specific task
                created_by = task.user
            )

        for x in Admins:
            # Create a notification for the added user
            Notification.objects.create(
                user=x,
                message = f"{task.user.username} has been assigned a task to review.",
                type='task',  # Notification type is 'task'
                task=task,  # Link the notification to the specific task
                created_by = task.user
            )

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







class ProjectListView(APIView):
    """
    View to list all projects with the percentage of completed tasks.
    """

    def get(self, request):
        projects = Project.objects.filter(
            Q(team_lead=request.user) | 
            Q(members__user=request.user) | 
            Q(created_by=request.user)
        ).distinct().order_by('due_date')

        # Iterate through each project and calculate the percentage of completed tasks
        project_data = []
        for project in projects:
            # Fetch the tasks that are tickets for this project
            tasks = Task.objects.filter(project=project, is_ticket=True)

            # Count the tasks with status 'completed', 'in_review', and 'approved'
            completed_tasks = tasks.filter( Q(status='in_review') | Q(status='approved')).count()
            pending_tasks = tasks.filter(status='pending').count()
            total_tasks = tasks.count()

            # Calculate the percentage of completed tasks
            percentage_completed = 0
            if total_tasks > 0:
                percentage_completed = (completed_tasks / total_tasks) * 100

            # Serialize the project data and add the calculated percentage
            project_serializer = ProjectSerializer(project)
            project_data.append({
                **project_serializer.data,
                'percentage': round(percentage_completed, 2)  # Add the calculated percentage to the response data
            })

        return Response({
            "message": "Projects fetched successfully!",
            "data": project_data
        }, status=status.HTTP_200_OK)





class ProjectListView(APIView):
    """
    View to list all projects with the percentage of completed tasks.
    """

    def get(self, request):
        if request.user.role == 'Admin':
            # Admins can view all projects
            projects = Project.objects.all().distinct().order_by('due_date')
        else:
            # Non-admin users are filtered by specific conditions
            projects = Project.objects.filter(
                Q(team_lead=request.user) |
                Q(members__user=request.user) |
                Q(created_by=request.user)
            ).distinct().order_by('due_date')

        # Iterate through each project and calculate the percentage of completed tasks
        project_data = []
        for project in projects:
            # Fetch the tasks that are tickets for this project
            tasks = Task.objects.filter(project=project, is_ticket=True)

            # Count the tasks with status 'completed', 'in_review', and 'approved'
            completed_tasks = tasks.filter( Q(status='in_review') | Q(status='approved')).count()
            pending_tasks = tasks.filter(status='pending').count()
            total_tasks = tasks.count()

            # Calculate the percentage of completed tasks
            percentage_completed = 0
            if total_tasks > 0:
                percentage_completed = (completed_tasks / total_tasks) * 100

            # Serialize the project data and add the calculated percentage
            project_serializer = ProjectSerializer(project)
            project_data.append({
                **project_serializer.data,
                'percentage': round(percentage_completed, 2)  # Add the calculated percentage to the response data
            })

        return Response({
            "message": "Projects fetched successfully!",
            "data": project_data
        }, status=status.HTTP_200_OK)







class ProjectListView(APIView):
    """
    View to list all projects with the percentage of completed tasks.
    """

    def get(self, request):
        if request.user.role == 'Admin':
            # Admins can view all projects
            projects = Project.objects.all().distinct().order_by('due_date')
        else:
            # Non-admin users are filtered by specific conditions
            projects = Project.objects.filter(
                Q(team_lead=request.user) |
                Q(members__user=request.user) |
                Q(created_by=request.user)
            ).distinct().order_by('due_date')

        # Iterate through each project and calculate the percentage of completed tasks
        project_data = []
        for project in projects:
            # Fetch the tasks that are tickets for this project
            tasks = Task.objects.filter(project=project, is_ticket=True)

            # Count the tasks with status 'completed', 'in_review', and 'approved'
            completed_tasks = tasks.filter( Q(status='in_review') | Q(status='approved')).count()
            pending_tasks = tasks.filter(status='pending').count()
            total_tasks = tasks.count()

            # Calculate the percentage of completed tasks
            percentage_completed = 0
            if total_tasks > 0:
                percentage_completed = (completed_tasks / total_tasks) * 100

            # Serialize the project data and add the calculated percentage
            project_serializer = ProjectSerializer(project)
            project_data.append({
                **project_serializer.data,
                'percentage': round(percentage_completed, 2)  # Add the calculated percentage to the response data
            })

        return Response({
            "message": "Projects fetched successfully!",
            "data": project_data
        }, status=status.HTTP_200_OK)






class ProjectDetailView(APIView):
    """
    View to get a specific project by its ID with the percentage of completed tasks.
    """

    def get(self, request, project_id):
        try:
            # Fetch the project by ID
            project = Project.objects.get(id=project_id)

            # Fetch the tasks that are tickets for this project
            tasks = Task.objects.filter(project=project, is_ticket=True)

            # Count the tasks with status 'completed', 'in_review', and 'approved'
            completed_tasks = tasks.filter(Q(status='in_review') | Q(status='approved')).count()
            pending_tasks = tasks.filter(status='pending').count()
            total_tasks = tasks.count()

            # Calculate the percentage of completed tasks
            percentage_completed = 0
            if total_tasks > 0:
                percentage_completed = (completed_tasks / total_tasks) * 100

            # Serialize the project data and add the calculated percentage
            project_serializer = ProjectSerializer(project)
            project_data = {
                **project_serializer.data,
                'percentage': round(percentage_completed, 2)  # Add the calculated percentage to the response data
            }

            return Response({
                "message": "Project fetched successfully!",
                "data": project_data
            }, status=status.HTTP_200_OK)

        except Project.DoesNotExist:
            return Response({
                "message": "Project not found."
            }, status=status.HTTP_404_NOT_FOUND)




# views.py
class CreateTicketTaskView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user  # Get the logged-in user

        # Initialize the serializer with request data and context
        serializer = TicketTaskSerializer(data=request.data, context={'request': request, 'user': user})

        if serializer.is_valid():
            task = serializer.save()  # Save the validated data

            Notification.objects.create(
                user=task.user,
                message = f"{user.username} has created a ticket for you under the {task.project.title} project.",
                type='task',  # Notification type is 'task'
                task=task,  # Link the notification to the specific task
                created_by = user
            )

            # notification___here
            return Response({
                "message": "Ticket created successfully!",
                "data": serializer.data,
            }, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)





class ProjectTicketsView(APIView):
    """
    View to get all tickets for a project sorted by status, priority, and due date.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, project_id):
        try:
            # Get the project
            project = Project.objects.get(id=project_id)
            
            # Get all tasks (tickets) for the project and sort
            tickets = Task.objects.filter(project=project, is_ticket=True).order_by(
                '-priority',  # High priority first
                'due_date',   # Closest due date first
            )

            # Group tasks by status
            pending = tickets.filter(status='pending')
            in_review = tickets.filter(status='in_review')
            approved = tickets.filter(status='approved')

            # Serialize tasks
            serializer = TaskSerializer(tickets, many=True)
            return Response({
                "message": "Tickets fetched successfully!",
                "data": {
                    "pending": TaskSerializer(pending, many=True).data,
                    "in_review": TaskSerializer(in_review, many=True).data,
                    "approved": TaskSerializer(approved, many=True).data,
                },
            }, status=status.HTTP_200_OK)
        except Project.DoesNotExist:
            return Response({"error": "Project not found"}, status=status.HTTP_404_NOT_FOUND)






class ChangeTicketStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, task_id):
        try:
            # Fetch the task by task_id
            task = get_object_or_404(Task, id=task_id)

            # Ensure the task belongs to the currently authenticated user
            if task.status == 'pending':
                if task.user != request.user:
                    return Response({"message": "You don't have permission to change this task's status."}, status=status.HTTP_403_FORBIDDEN)

            # Get the status from the request body and ensure it's not None or empty
            status_value = request.data.get('status', '').lower()

            # Check if status was provided
            if not status_value:
                return Response({"message": "Status is required."}, status=status.HTTP_400_BAD_REQUEST)

            # Validate if the status is one of the expected statuses
            if status_value not in ['pending', 'in_review', 'approved']:
                return Response({"message": "Invalid status provided."}, status=status.HTTP_400_BAD_REQUEST)


            # notification___here
            managers = User.objects.filter(role = 'Manager')
            Admins = User.objects.filter(role = 'Admin')
            
            # Check if the status change is allowed
            if task.status == 'pending' and status_value == 'in_review':
                task.status = 'in_review'
                task.review_date = timezone.now()

                for x in managers:
                    Notification.objects.create(
                        user=x,
                        message = f"{task.user.username} has been assigned a task to review.",
                        type='task',  # Notification type is 'task'
                        task=task,  # Link the notification to the specific task
                        created_by = task.user
                    )

                for x in Admins:
                    Notification.objects.create(
                        user=x,
                        message = f"{task.user.username} has been assigned a task to review.",
                        type='task',  # Notification type is 'task'
                        task=task,  # Link the notification to the specific task
                        created_by = task.user
                    )
                    
            elif task.status == 'in_review' and status_value == 'approved':
                task.status = 'approved'
                task.approved_date = timezone.now()
                Notification.objects.create(
                    user=task.user,
                    message = f"{request.user.username} has been approved your task",
                    type='task',  # Notification type is 'task'
                    task=task,  # Link the notification to the specific task
                    created_by = request.user
                )

                for x in Admins:
                    Notification.objects.create(
                        user=x,
                        message = f"{request.user.username} has been approved {task.user.username}'s task",
                        type='task',  # Notification type is 'task'
                        task=task,  # Link the notification to the specific task
                        created_by = request.user
                    )
                #notification___here

            elif task.status == 'in_review' and status_value == 'pending':
                task.status = 'pending'
                task.review_date = None
                
                Notification.objects.create(
                    user=task.user,
                    message = f"{request.user.username} has been rejected your task",
                    type='task',  # Notification type is 'task'
                    task=task,  # Link the notification to the specific task
                    created_by = request.user
                )

                for x in Admins:
                    Notification.objects.create(
                        user=x,
                        message = f"{request.user.username} has been rejected {task.user.username}'s task",
                        type='task',  # Notification type is 'task'
                        task=task,  # Link the notification to the specific task
                        created_by = request.user
                    )
                #notification___here
            else:
                return Response({"message": "Invalid status transition."}, status=status.HTTP_400_BAD_REQUEST)

            task.save()

            return Response({
                "message": f"Task status changed to {status_value} successfully.",
            }, status=status.HTTP_200_OK)

        except Exception as e:
            # Handle unexpected exceptions gracefully
            return Response({"message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)






class AddMemberToProjectView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, project_id):
        # Fetch the project by its ID
        project = get_object_or_404(Project, id=project_id)

        # Ensure the current user is a Team Lead, Manager, or Admin
        user_role = request.user.role
        if user_role not in ['Manager', 'Admin'] and request.user != project.team_lead:
            return Response({"message": "You do not have the required permissions to add a member."}, status=status.HTTP_403_FORBIDDEN)

        # Get the user to be added to the project from the request body
        user_id = request.data.get('user_id')
        if not user_id:
            return Response({"message": "User ID is required."}, status=status.HTTP_400_BAD_REQUEST)

        # Fetch the user to be added
        user_to_add = get_object_or_404(User, id=user_id)

        if user_to_add == project.team_lead:
            return Response({"message": "User is already a member of this project. "}, status=status.HTTP_400_BAD_REQUEST)


        # Ensure the user is not already a member of the project
        if ProjectMember.objects.filter(project=project, user=user_to_add).exists():
            return Response({"message": "User is already a member of this project."}, status=status.HTTP_400_BAD_REQUEST)

        # Add the user to the project members
        ProjectMember.objects.create(project=project, user=user_to_add, role='Staff')  # Default role is 'Staff', can be adjusted if needed

        # Create a notification for the added user
        Notification.objects.create(
            user=user_to_add,
            message = f"{request.user.username} has added you as a member to the '{project.title}' project.",
            type='project',  # Notification type is 'project'
            project=project,  # Link the notification to the specific project
            created_by = request.user
        )

        #notification___here
        return Response({
            "message": f"User {user_to_add.username} added to the project successfully."
        }, status=status.HTTP_200_OK)




class UserListView(generics.ListAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        # You can customize the queryset, for example, filter users based on their role or department if needed
        users = self.get_queryset()
        serializer = self.get_serializer(users, many=True)
        return Response(serializer.data)





class LatestHighPriorityProjectsView(APIView):
    """
    View to fetch the latest 3 projects with status 'pending' and priority 'high'.
    """

    def get(self, request):

        user = request.user

        # Query the projects with status 'pending' and priority 'high', ordered by `created_at`


        if request.user.role == 'Admin':
            # Admins can view all pending projects
            projects = Project.objects.filter(
                status='pending'
            ).order_by('due_date')[:3]
        else:
            # Non-admin users are filtered by specific conditions
            projects = Project.objects.filter(
                status='pending'
            ).filter(
                Q(team_lead=request.user) | 
                Q(members__user=request.user) | 
                Q(created_by=request.user)
            ).distinct().order_by('due_date')[:3]

        project_data = []

        for project in projects:
            # Fetch the tasks that are tickets for this project
            tasks = Task.objects.filter(project=project, is_ticket=True)

            # Count the tasks with status 'completed', 'in_review', and 'approved'
            completed_tasks = tasks.filter( Q(status='in_review') | Q(status='approved')).count()
            pending_tasks = tasks.filter(status='pending').count()
            total_tasks = tasks.count()

            # Calculate the percentage of completed tasks
            percentage_completed = 0
            if total_tasks > 0:
                percentage_completed = (completed_tasks / total_tasks) * 100

            # Serialize the project data and add the calculated percentage
            project_serializer = ProjectSerializer(project)
            project_data.append({
                **project_serializer.data,
                'percentage': round(percentage_completed, 2)  # Add the calculated percentage to the response data
            })

        # Serialize the projects
        project_serializer = ProjectSerializer(projects, many=True)

        return Response({
            "message": "Latest high-priority pending projects fetched successfully!",
            "data": project_data
        }, status=status.HTTP_200_OK)






class GetUserNotificationsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Get the current authenticated user
        user = request.user

        # Fetch all notifications related to the user, ordered by creation date
        notifications = Notification.objects.filter(user=user).order_by('-created_at')

        # Serialize the notifications
        serializer = NotificationSerializer(notifications, many=True)

        # Return the notifications as a response
        return Response({
            "message": "Notifications fetched successfully!",
            "data": serializer.data
        }, status=status.HTTP_200_OK)






class MarkNotificationAsReadView(APIView):
    permission_classes = [IsAuthenticated]  # Ensure only authenticated users can mark notifications as read

    def post(self, request):
        # Get the notification ID(s) from the request data
        notification_ids = request.data.get('notification_ids', [])

        if not notification_ids:
            return Response({"message": "No notification IDs provided."}, status=400)

        # Ensure the notifications belong to the current user
        notifications = Notification.objects.filter(id__in=notification_ids, user=request.user)

        if notifications.exists():
            # Update the read status of the selected notifications
            notifications.update(read_status=True)
            return Response({"message": "Notifications marked as read."}, status=200)
        else:
            return Response({"message": "No notifications found."}, status=404)







class UnreadNotificationAPIView(APIView):
    """
    API view to check if the authenticated user has any unread notifications.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Get unread notifications for the currently authenticated user
        unread_notifications = Notification.objects.filter(user=request.user, read_status=False)

        # Return true if there are unread notifications, otherwise false
        has_unread = unread_notifications.exists()

        return Response({'has_unread': has_unread})







class CreateProjectView(APIView):
    permission_classes = [IsAuthenticated]  # Only authenticated users can create projects

    def post(self, request):
        # Check if the user is a staff member and prevent access if they are
        if request.user.role == 'staff':  # Assuming 'role' is a custom field in your User model
            return Response({"detail": "You don't have permission to create a project."}, status=status.HTTP_403_FORBIDDEN)

        # Extract data from the request
        data = request.data
        print("Received Data:", data)

        members_data = data.get('members', [])
        images_data = request.FILES.getlist('images')  # Get list of uploaded files (images)

        # Remove 'members' and 'images' from the data before further processing
        data_to_serializer = {key: value for key, value in data.items() if key not in ['members', 'images']}

        # Validate that 'team_lead' is passed as a valid user ID
        try:
            team_lead = User.objects.get(id=int(data_to_serializer['team_lead']))
        except User.DoesNotExist:
            return Response({"detail": "Invalid team lead ID."}, status=status.HTTP_400_BAD_REQUEST)

        # Ensure that 'created_by' is the logged-in user
        data_to_serializer['created_by'] = request.user.id
        data_to_serializer['team_lead'] = team_lead.id  # Store team_lead as an ID

        # Create project serializer with the provided data
        serializer = ProjectSerializerCreate(data=data_to_serializer)
        
        if serializer.is_valid():
            # Save the project object
            project = serializer.save()

            # Add project members (if any)
            for member in members_data:
                try:
                    user = User.objects.get(id=int(member))
                    ProjectMember.objects.create(project=project, user=user)
                    Notification.objects.create(
                        user=user,
                        message = f"{request.user.username} has added you as a member to the '{project.title}' project.",
                        type='project',  # Notification type is 'task'
                        task=project,  # Link the notification to the specific task
                        created_by = request.user
                    )
                except User.DoesNotExist:
                    return Response({"detail": f"Member with ID {member} does not exist."}, status=status.HTTP_400_BAD_REQUEST)

            # Add project images (if any)
            for image in images_data:
                ProjectImage.objects.create(project=project, image=image)

            return Response({"message": "Project created successfully", "project_id": project.id}, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)




class DeleteProjectView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, project_id):
        # Check if the project exists
        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            return Response({"detail": "Project not found."}, status=status.HTTP_404_NOT_FOUND)

        # Check if the logged-in user is the creator or the admin
        if project.created_by != request.user and not request.user.is_staff:
            return Response({"detail": "You do not have permission to delete this project."}, status=status.HTTP_403_FORBIDDEN)

        # Delete the project
        project.delete()
        return Response({"message": "Project deleted successfully."}, status=status.HTTP_204_NO_CONTENT)





class GetUserDetailsView(APIView):
    permission_classes = [IsAuthenticated]  # Ensure the user is authenticated

    def get(self, request, user_id):
        # Try to fetch the user with the given user_id
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        # Serialize the user data
        serializer = UserSerializer(user)

        return Response(serializer.data, status=status.HTTP_200_OK)





class ProjectListUserView(APIView):
    """
    View to list all projects where the specific user is either the team_lead or a member,
    and include the percentage of completed tasks.
    """

    def get(self, request):
        # Get the user_id parameter from the request query
        user_id = request.query_params.get('user_id', None)
        
        if not user_id:
            return Response({
                "detail": "user_id parameter is required"
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(id=user_id)  # Validate that the user exists
        except User.DoesNotExist:
            return Response({
                "detail": "User not found"
            }, status=status.HTTP_404_NOT_FOUND)

        # Query for projects where the user is either the team_lead or a member
        projects = Project.objects.filter(
            Q(team_lead=user) | Q(members__user=user)
        ).distinct().order_by('due_date')

        # Iterate through each project and calculate the percentage of completed tasks
        project_data = []
        for project in projects:
            # Fetch the tasks that are tickets for this project
            tasks = Task.objects.filter(project=project, is_ticket=True)

            # Count the tasks with status 'completed', 'in_review', and 'approved'
            completed_tasks = tasks.filter(Q(status='in_review') | Q(status='approved')).count()
            pending_tasks = tasks.filter(status='pending').count()
            total_tasks = tasks.count()

            # Calculate the percentage of completed tasks
            percentage_completed = 0
            if total_tasks > 0:
                percentage_completed = (completed_tasks / total_tasks) * 100

            # Serialize the project data and add the calculated percentage
            project_serializer = ProjectSerializer(project)
            project_data.append({
                **project_serializer.data,
                'percentage': round(percentage_completed, 2)  # Add the calculated percentage to the response data
            })

        return Response({
            "message": "Projects fetched successfully!",
            "data": project_data
        }, status=status.HTTP_200_OK)









class UserSpecificDateTasksUserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id, specific_date):
        # Ensure that the logged-in user is authorized to access the tasks of the given user
        if request.user.role == 'Staff':
            return Response({"message": "You don't have permission to view this user's tasks."}, status=status.HTTP_403_FORBIDDEN)

        # Convert the specific date (e.g., '25-11-2024') to a datetime object
        try:
            specific_date = datetime.strptime(specific_date, '%d-%m-%Y')  # Date format: 'dd-mm-yyyy'
            specific_date = make_aware(specific_date)  # Make it timezone-aware
        except ValueError:
            return Response({"message": "Invalid date format. Please use 'dd-mm-yyyy'."}, status=status.HTTP_400_BAD_REQUEST)

        # Fetch tasks for the specified user that match the criteria:
        # - Tasks where start_date's date part is less than or equal to the specific date
        # - Tasks where due_date's date part is greater than or equal to the specific date
        tasks = Task.objects.filter(
            user__id=user_id,  # Filter by user ID
            start_date__date__lte=specific_date.date(),  # Use only the date part of start_date
            due_date__date__gte=specific_date.date()     # Use only the date part of due_date
        )

        # Serialize the tasks
        serializer = TaskSerializer(tasks, many=True)

        return Response({
            "message": "Tasks for the specified date retrieved successfully!",
            "data": serializer.data
        }, status=status.HTTP_200_OK)





class UserSpecificDateRangeTasksUserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id, start_date, end_date):
        # Ensure that the logged-in user is authorized to access the tasks of the given user
        if request.user.role == 'Staff':
            return Response({"message": "You don't have permission to view this user's tasks."}, status=status.HTTP_403_FORBIDDEN)

        # Convert the start and end dates (e.g., '25-11-2024') to datetime objects
        try:
            start_date = datetime.strptime(start_date, '%d-%m-%Y')  # Date format: 'dd-mm-yyyy'
            start_date = make_aware(start_date)  # Make it timezone-aware
            end_date = datetime.strptime(end_date, '%d-%m-%Y')  # Date format: 'dd-mm-yyyy'
            end_date = make_aware(end_date)  # Make it timezone-aware
        except ValueError:
            return Response({"message": "Invalid date format. Please use 'dd-mm-yyyy'."}, status=status.HTTP_400_BAD_REQUEST)

        # Fetch tasks for the specified user within the date range
        tasks = Task.objects.filter(
            user__id=user_id,  # Filter by user ID
            start_date__date__gte=start_date.date(),  # Tasks that start after the start_date
            due_date__date__lte=end_date.date()       # Tasks that end before the end_date
        )

        # Serialize the tasks
        serializer = TaskSerializer(tasks, many=True)

        return Response({
            "message": "Tasks for the specified date range retrieved successfully!",
            "data": serializer.data
        }, status=status.HTTP_200_OK)





class CreateUserView(APIView):
    permission_classes = [IsAuthenticated]  # Restrict this view to admin users

    def post(self, request):
        if request.user.role == 'Staff':
            return Response({"message": "You don't have permission to create new user."}, status=status.HTTP_403_FORBIDDEN)

        if request.user.role == 'Manager':
            return Response({"message": "You don't have permission to create new user."}, status=status.HTTP_403_FORBIDDEN)


        serializer = UserCreateSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "User created successfully!", "data": serializer.data}, status=status.HTTP_201_CREATED)
        return Response({"message": "Failed to create user", "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)





class DeleteUserView(APIView):
    permission_classes = [IsAuthenticated]  # Ensure the user is authenticated

    def delete(self, request, user_id):
        # Check if the logged-in user is an admin (you can adjust this based on your needs)
        if request.user.role == 'Staff':
            return Response({"message": "You don't have permission to delete user."}, status=status.HTTP_403_FORBIDDEN)

        if request.user.role == 'Manager':
            return Response({"message": "You don't have permission to delete user."}, status=status.HTTP_403_FORBIDDEN)

        try:
            # Find the user by ID
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        # Delete the user
        user.delete()

        return Response({"detail": "User deleted successfully."}, status=status.HTTP_204_NO_CONTENT)





class EditUserView(APIView):
    permission_classes = [IsAuthenticated]  # Ensure the user is authenticated

    def put(self, request, user_id):
        try:
            # Get the user object based on the user ID passed
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise NotFound(detail="User not found.")


        if request.user.role == 'Staff':
            return Response({"message": "You don't have permission to Edit user."}, status=status.HTTP_403_FORBIDDEN)

        if request.user.role == 'Manager':
            return Response({"message": "You don't have permission to Edit user."}, status=status.HTTP_403_FORBIDDEN)



        # Update the fields if they are provided in the request data
        user.full_name = request.data.get("full_name", user.full_name)
        user.email = request.data.get("email", user.email)
        user.phone_number = request.data.get("phone_number", user.phone_number)
        user.position = request.data.get("position", user.position)
        user.role = request.data.get("role", user.role)
        user.department = request.data.get("department", user.department)

        # Save the updated user data
        user.save()

        return Response({"detail": "User updated successfully."}, status=status.HTTP_200_OK)