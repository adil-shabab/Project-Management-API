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
from .models import *
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
import logging
from rest_framework.parsers import JSONParser
from rest_framework.parsers import MultiPartParser, FormParser
from django.core.exceptions import ValidationError
from django.utils.dateparse import parse_datetime
from django.db.models import Q
from django.utils.timezone import localdate, make_aware
from django.utils.timezone import now
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import datetime
import face_recognition
import numpy as np
from rest_framework.response import Response
from rest_framework.decorators import api_view
from django.utils.timezone import now
from geopy.distance import geodesic
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
import base64
import face_recognition
from io import BytesIO
from PIL import Image
import numpy as np
from .models import Attendance, FaceEncoding
import pytz



# Office Location (latitude, longitude)

@csrf_exempt
def register_face(request):
    if request.method == "POST":
        try:
            print("Coming Here")
            # Parse JSON data from request
            data = request.POST if request.POST else request.body.decode('utf-8')
            if isinstance(data, str):
                import json
                data = json.loads(data)
            
            user_id = data.get("user_id")
            print(user_id)
            face_image = data.get("face_image")

            if not user_id or not face_image:
                return JsonResponse({"error": "Missing user_id or face_image"}, status=400)

            # Get user from database
            try:
                user = User.objects.get(id=user_id)
                print(user)
            except User.DoesNotExist:
                return JsonResponse({"error": "User not found"}, status=404)

            # Decode base64 image (remove "data:image/jpeg;base64," prefix if present)
            if "," in face_image:
                face_image = face_image.split(",")[1]
            image_data = base64.b64decode(face_image)
            image = Image.open(BytesIO(image_data)).convert("RGB")
            image_array = np.array(image)

            # Extract face encoding
            encodings = face_recognition.face_encodings(image_array)
            if not encodings:
                return JsonResponse({"error": "No face detected in the image"}, status=400)

            encoding = encodings[0]  # Assume one face per image

            # Store or update face encoding
            face_encoding, created = FaceEncoding.objects.get_or_create(user=user)
            face_encoding.set_encoding(encoding)
            face_encoding.save()

            return JsonResponse({"message": "Face registered successfully"})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    return JsonResponse({"error": "Invalid request method"}, status=405)






# Define office coordinates (Bangalore, India)
OFFICE_COORDINATES = (13.002685534417267, 77.6613268167425)  # Bangalore coordinates
OFFICE_RADIUS_KM = 1  # 1 kilometer radius

@csrf_exempt
def punch_in(request):
    if request.method == "POST":
        try:
            data = request.POST if request.POST else json.loads(request.body.decode('utf-8'))
            user_id = data.get("user_id")
            face_image = data.get("face_image")
            location = data.get("location", "Unknown")  # Default to "Unknown" if not provided
            reason = data.get("reason", "")  # Reason from frontend

            print(f"Received data: user_id={user_id}, face_image={face_image[:50] if face_image else 'None'}, location={location}, reason={reason}")

            if not user_id or not face_image:
                return JsonResponse({"error": "Missing user_id or face_image"}, status=400)

            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return JsonResponse({"error": "User not found"}, status=404)

            # Check if user has already punched in today
            ist = pytz.timezone("Asia/Kolkata")
            today = timezone.now().astimezone(ist).date()
            existing_attendance = Attendance.objects.filter(
                user=user,
                date=today,
                punch_in_time__isnull=False  # Already punched in
            ).first()

            if existing_attendance:
                # Return existing punch-in details with ISO format including timezone
                punch_in_time_ist = existing_attendance.punch_in_time.astimezone(ist)
                return JsonResponse({
                    "message": "Already punched in today",
                    "location": existing_attendance.punch_in_location,
                    "punch_in_time": punch_in_time_ist.isoformat(),  # ISO format with timezone (e.g., "2025-02-25T15:34:19+05:30")
                    "work_type": existing_attendance.work_type,
                    "status_punchin": existing_attendance.status_punchin,
                    "reason": existing_attendance.reason
                })

            if "," in face_image:
                face_image = face_image.split(",")[1]
            image_data = base64.b64decode(face_image)
            image = Image.open(BytesIO(image_data)).convert("RGB")
            image_array = np.array(image)

            punch_in_encodings = face_recognition.face_encodings(image_array)
            if not punch_in_encodings:
                return JsonResponse({"error": "No face detected in the image"}, status=400)
            punch_in_encoding = punch_in_encodings[0]

            try:
                stored_encoding = FaceEncoding.objects.get(user=user).get_encoding()
            except FaceEncoding.DoesNotExist:
                return JsonResponse({"error": "Face not registered for this user"}, status=400)

            matches = face_recognition.compare_faces([stored_encoding], punch_in_encoding)
            if not matches[0]:
                return JsonResponse({"error": "Face verification failed"}, status=403)

            work_type = "WFH"  # Default to WFH
            status_punchin = "On Time"
            status_punchout = "Absent"  # Default until punch-out occurs
            status = "On Time"

            if location != "Unknown" and location != "Location access denied":
                print(f"Processing location: {location}")
                try:
                    # Try splitting with and without space for robustness
                    lat_lon = location.split(",")
                    if len(lat_lon) != 2:
                        raise ValueError("Invalid location format")
                    lat, lon = map(float, [lat_lon[0].strip(), lat_lon[1].strip()])
                    user_location = (lat, lon)
                    print(f"User location (lat, lon): {user_location}")
                    print(f"Office coordinates: {OFFICE_COORDINATES}")
                    distance_km = geodesic(user_location, OFFICE_COORDINATES).kilometers
                    print(f"Calculated distance: {distance_km} km")

                    if distance_km <= OFFICE_RADIUS_KM:
                        work_type = "WFO"
                        print("Setting work_type to WFO because distance <= OFFICE_RADIUS_KM")
                    else:
                        work_type = "WFH"
                        print("Setting work_type to WFH because distance > OFFICE_RADIUS_KM")
                except ValueError as ve:
                    print(f"Error parsing location: {ve}")
                    return JsonResponse({"error": f"Invalid location format. Expected 'latitude,longitude'. Error: {str(ve)}"}, status=400)
            else:
                print(f"Location is 'Unknown' or 'Location access denied', defaulting to WFH")
                work_type = "WFH"

            print(f"Final work_type before saving: {work_type}")

            punch_in_time = timezone.now().astimezone(ist)
            print(f"Punch-in time (IST): {punch_in_time.strftime('%Y-%m-%d %H:%M:%S')}")

            punch_in_hour = punch_in_time.hour
            punch_in_minute = punch_in_time.minute
            if punch_in_hour > 9 or (punch_in_hour == 9 and punch_in_minute > 30):
                status_punchin = "Late"
                status = "Punched in Late"
            else:
                status_punchin = "On Time"
                status = "On Time"

            print(f"Status punchin: {status_punchin}")

            attendance, created = Attendance.objects.get_or_create(
                user=user,
                date=punch_in_time.date(),
                defaults={
                    "punch_in_time": punch_in_time,
                    "punch_in_location": location,
                    "work_type": work_type,
                    "face_verified": True,
                    "status_punchin": status_punchin,
                    "status_punchout": status_punchout,
                    "reason": reason if work_type == "WFH" else None,
                    "status": status
                }
            )

            if not created:
                attendance.punch_in_time = punch_in_time
                attendance.punch_in_location = location
                attendance.work_type = work_type
                attendance.face_verified = True
                attendance.status_punchin = status_punchin
                attendance.status_punchout = status_punchout
                attendance.reason = reason if work_type == "WFH" else None
                attendance.status = status
                attendance.save()

            print(f"Work type after saving: {attendance.work_type}")

            # Return punch-in details with ISO format including timezone
            punch_in_time_ist = attendance.punch_in_time.astimezone(ist)
            return JsonResponse({
                "message": "Punched in successfully",
                "location": attendance.punch_in_location,
                "punch_in_time": punch_in_time_ist.isoformat(),  # ISO format with timezone (e.g., "2025-02-25T15:34:19+05:30")
                "work_type": attendance.work_type,
                "status_punchin": attendance.status_punchin,
                "reason": attendance.reason
            })
        except Exception as e:
            print(f"Exception occurred: {str(e)}")
            return JsonResponse({"error": str(e)}, status=500)
    return JsonResponse({"error": "Invalid request method"}, status=405)


    




    
@csrf_exempt
def punch_out(request):
    if request.method == "POST":
        try:
            data = request.POST if request.POST else json.loads(request.body.decode('utf-8'))
            user_id = data.get("user_id")
            face_image = data.get("face_image")
            location = data.get("location")

            if not user_id or not face_image:
                return JsonResponse({"error": "Missing user_id or face_image"}, status=400)

            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return JsonResponse({"error": "User not found"}, status=404)

            # Get today's attendance record for the user
            ist = pytz.timezone("Asia/Kolkata")
            today = timezone.now().astimezone(ist).date()
            attendance = Attendance.objects.filter(
                user=user,
                date=today,
                punch_in_time__isnull=False  # Ensure user has punched in
            ).first()

            if not attendance:
                return JsonResponse({"error": "No punch-in record found for today"}, status=400)

            # Check if user has already punched out
            if attendance.punch_out_time:
                punch_out_time_ist = attendance.punch_out_time.astimezone(ist)
                return JsonResponse({
                    "message": "Already punched out today",
                    "location": attendance.punch_out_location,
                    "punch_out_time": punch_out_time_ist.isoformat(),  # ISO format with timezone (e.g., "2025-02-25T18:30:00+05:30")
                    "work_type": attendance.work_type,
                    "status_punchout": attendance.status_punchout
                })

            # Process face image for verification
            if "," in face_image:
                face_image = face_image.split(",")[1]
            image_data = base64.b64decode(face_image)
            image = Image.open(BytesIO(image_data)).convert("RGB")
            image_array = np.array(image)

            punch_out_encodings = face_recognition.face_encodings(image_array)
            if not punch_out_encodings:
                return JsonResponse({"error": "No face detected in the image"}, status=400)
            punch_out_encoding = punch_out_encodings[0]

            try:
                stored_encoding = FaceEncoding.objects.get(user=user).get_encoding()
            except FaceEncoding.DoesNotExist:
                return JsonResponse({"error": "Face not registered for this user"}, status=400)

            matches = face_recognition.compare_faces([stored_encoding], punch_out_encoding)
            if not matches[0]:
                return JsonResponse({"error": "Face verification failed"}, status=403)

            # Determine work type based on location (similar to punch-in)
            OFFICE_RADIUS_KM = 1  # 1 kilometer radius
            work_type = attendance.work_type  # Retain the work type from punch-in

            # Update punch-out time and determine status based on 6:30 PM IST
            punch_out_time = timezone.now().astimezone(ist)
            punch_out_hour = punch_out_time.hour
            punch_out_minute = punch_out_time.minute

            # Define 6:30 PM IST
            target_hour = 18  # 6 PM
            target_minute = 30  # 30 minutes

            if punch_out_hour < target_hour or (punch_out_hour == target_hour and punch_out_minute < target_minute):
                status_punchout = "Early Leaving"  # Before 6:30 PM
            elif punch_out_hour > target_hour or (punch_out_hour == target_hour and punch_out_minute > target_minute):
                status_punchout = "Late"  # After 6:30 PM
            else:
                status_punchout = "On Time"  # Exactly 6:30 PM

            # Check location for WFO punch-outs (optional additional validation)
            if location != "Unknown" and location != "Location access denied":
                lat, lon = map(float, location.split(", "))
                user_location = (lat, lon)
                distance_km = geodesic(user_location, OFFICE_COORDINATES).kilometers

                if distance_km > OFFICE_RADIUS_KM and work_type == "WFO":
                    status_punchout = "Early Leaving"  # If punching out far from office while WFO, mark as early

            # Update attendance with punch-out details
            attendance.punch_out_time = punch_out_time
            attendance.punch_out_location = location
            attendance.status_punchout = status_punchout
            attendance.save()

            # Return punch-out details with ISO format including timezone
            punch_out_time_ist = attendance.punch_out_time.astimezone(ist)
            return JsonResponse({
                "message": "Punched out successfully",
                "location": attendance.punch_out_location,
                "punch_out_time": punch_out_time_ist.isoformat(),  # ISO format with timezone (e.g., "2025-02-25T18:30:00+05:30")
                "work_type": attendance.work_type,
                "status_punchout": attendance.status_punchout
            })
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    return JsonResponse({"error": "Invalid request method"}, status=405)



@csrf_exempt
def is_punched_in(request):
    if request.method == "POST":
        try:
            data = request.POST if request.POST else json.loads(request.body.decode('utf-8'))
            user_id = data.get("user_id")

            if not user_id:
                return JsonResponse({"error": "Missing user_id"}, status=400)

            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return JsonResponse({"error": "User not found"}, status=404)

            # Check if user has punched in today but not punched out
            ist = pytz.timezone("Asia/Kolkata")
            today = timezone.now().astimezone(ist).date()
            attendance = Attendance.objects.filter(
                user=user,
                date=today,
                punch_in_time__isnull=False,  # Has punched in
                punch_out_time__isnull=True   # Has not punched out
            ).first()

            is_punched_in = bool(attendance)  # True if punched in and not out, False otherwise

            return JsonResponse({
                "is_punched_in": is_punched_in,
                "message": "Punch-in status checked successfully"
            })
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    return JsonResponse({"error": "Invalid request method"}, status=405)


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
                    "user_id": user.id,
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
                'user_id': user.user_id,
            }
            
            # Only add 'avatar' to the response if it exists
            if user.avatar:
                user_data['avatar'] = user.avatar.url

            return Response(user_data)

        else:
            return Response({"detail": "User not authenticated."}, status=401)





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

        TaskHistory.objects.create(
            task=task,
            status=task.status,
            changed_by=request.user,
            notes=f"Status changed to {task.status}."
        )


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

            # Ensure the task belongs to the currently authenticated user (if applicable)
            if task.status == 'pending' and task.user != request.user:
                return Response(
                    {"message": "You don't have permission to change this task's status."},
                    status=status.HTTP_403_FORBIDDEN
                )

            # Get the status from the request body and ensure it's not None or empty
            status_value = request.data.get('status', '').lower()

            # Check if status was provided
            if not status_value:
                return Response(
                    {"message": "Status is required."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Validate if the status is one of the expected statuses
            valid_statuses = ['pending', 'in_review', 'approved']
            if status_value not in valid_statuses:
                return Response(
                    {"message": "Invalid status provided."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Handle status transitions
            if task.status == 'pending' and status_value == 'in_review':
                # Transition from 'pending' to 'in_review'
                task.status = 'in_review'
                task.review_date = timezone.now()

                # Log the status change in TaskHistory
                TaskHistory.objects.create(
                    task=task,
                    status=task.status,
                    changed_by=request.user,
                    notes=f"Status changed to {task.status}."
                )


                # Notify managers and admins
                managers = User.objects.filter(role='Manager')
                admins = User.objects.filter(role='Admin')

                for user in managers.union(admins):
                    Notification.objects.create(
                        user=user,
                        message=f"{task.user.username} has submitted a task for review.",
                        type='task',
                        task=task,
                        created_by=task.user
                    )

            elif task.status == 'in_review' and status_value == 'approved':
                # Transition from 'in_review' to 'approved'
                task.status = 'approved'
                task.approved_date = timezone.now()

                # Log the status change in TaskHistory
                TaskHistory.objects.create(
                    task=task,
                    status=task.status,
                    changed_by=request.user,
                    notes=f"Status changed to {task.status}."
                )


                # Notify the task owner and admins
                Notification.objects.create(
                    user=task.user,
                    message=f"{request.user.username} has approved your task.",
                    type='task',
                    task=task,
                    created_by=request.user
                )

                admins = User.objects.filter(role='Admin')
                for admin in admins:
                    Notification.objects.create(
                        user=admin,
                        message=f"{request.user.username} has approved {task.user.username}'s task.",
                        type='task',
                        task=task,
                        created_by=request.user
                    )

            elif task.status == 'in_review' and status_value == 'pending':
                # Transition from 'in_review' to 'pending'
                if not request.user.role in ['Manager', 'Admin']:
                    return Response(
                        {"message": "Only managers and admins can reject tasks."},
                        status=status.HTTP_403_FORBIDDEN
                    )

                reason = request.data.get('reason')
                due_date = request.data.get('due_date')

                # if not reason or not due_date:
                #     return Response(
                #         {"message": "Reason and due date are required for rejection."},
                #         status=status.HTTP_400_BAD_REQUEST
                #     )

                task.status = 'pending'
                task.save()


                TaskHistory.objects.create(
                    task=task,
                    status=task.status,
                    reason=reason,
                    changed_by=request.user,
                    notes=f"Status changed to {task.status}."
                )


                # Notify the task owner and admins
                Notification.objects.create(
                    user=task.user,
                    message=f"{request.user.username} has rejected your task. Reason: {reason}",
                    type='task',
                    task=task,
                    created_by=request.user
                )

                admins = User.objects.filter(role='Admin')
                for admin in admins:
                    Notification.objects.create(
                        user=admin,
                        message=f"{request.user.username} has rejected {task.user.username}'s task. Reason: {reason}",
                        type='task',
                        task=task,
                        created_by=request.user
                    )


            elif task.status == 'approved' and status_value == 'pending':
                # Transition from 'in_review' to 'approved'

                reason = request.data.get('reason')
                due_date = request.data.get('due_date')

                # if not reason or not due_date:
                #     return Response(
                #         {"message": "Reason and due date are required for rejection."},
                #         status=status.HTTP_400_BAD_REQUEST
                #     )

                task.status = 'pending'
                task.approved_date = timezone.now()

                TaskHistory.objects.create(
                    task=task,
                    status=task.status,
                    reason=reason,
                    changed_by=request.user,
                    notes=f"Status changed to {task.status}."
                )



                # Notify the task owner and admins
                Notification.objects.create(
                    user=task.user,
                    message=f"{request.user.username} has reopened your task. Reason: {reason}",
                    type='task',
                    task=task,
                    created_by=request.user
                )

                admins = User.objects.filter(role='Admin')
                for admin in admins:
                    Notification.objects.create(
                        user=admin,
                        message=f"{request.user.username} has reopened {task.user.username}'s task. Reason: {reason}",
                        type='task',
                        task=task,
                        created_by=request.user
                    )
            else:
                return Response(
                    {"message": "Invalid status transition."},
                    status=status.HTTP_400_BAD_REQUEST
                )


            task.save()

            return Response(
                {"message": f"Task status changed to {status_value} successfully."},
                status=status.HTTP_200_OK
            )

        except Exception as e:
            # Handle unexpected exceptions gracefully
            return Response(
                {"message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )




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
                        project=project,  # Link the notification to the specific task
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



        # Print the old hashed password before updating
        print("Before update - Hashed Password:", user.password)



        # Update the fields if they are provided in the request data
        user.full_name = request.data.get("full_name", user.full_name)
        user.email = request.data.get("email", user.email)
        user.phone_number = request.data.get("phone_number", user.phone_number)
        user.position = request.data.get("position", user.position)
        user.role = request.data.get("role", user.role)
        user.department = request.data.get("department", user.department)
        user.username = request.data.get("username", user.username)

        # Handle password update (if provided)
        password = request.data.get("password")
        print("Password", password)


        if password:
            user.set_password(password)  # Hash the password before saving


        user.save()

        # Print the new hashed password
        print("After update - Hashed Password:", user.password)


        return Response({"detail": "User updated successfully."}, status=status.HTTP_200_OK)





class TaskHistoryView(APIView):
    def get(self, request, task_id):
        task_history = TaskHistory.objects.filter(task_id=task_id).order_by('-changed_at')
        serializer = TaskHistorySerializer(task_history, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)





class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]  # Only authenticated users can change their password

    def post(self, request):
        # Get the current user
        user = request.user

        # Get the new password from the request data
        new_password = request.data.get("new_password")

        if not new_password:
            return Response({"message": "New password is required."}, status=status.HTTP_400_BAD_REQUEST)

        # Set the new password
        user.set_password(new_password)  # Hash the new password before saving
        user.save()

        return Response({"message": "Password changed successfully."}, status=status.HTTP_200_OK)




@csrf_exempt
def create_holiday(request):

    from django.utils import timezone
    from datetime import time  # Import datetime.time for time.min

    if request.method == "POST":
        try:
            # Parse the JSON data from the request body
            data = json.loads(request.body.decode('utf-8'))
            date = data.get("date")
            name = data.get("name")
            user = data.get("user")
            description = data.get("description", "")  # Optional field

            # Get the current user
            user = User.objects.get(id = int(user))


            # Check if the user is an Admin or Manager
            if user.role not in ['Admin', 'Manager']:
                return JsonResponse({"error": "Permission denied. Only Admins and Managers can create holidays."}, status=403)

            # Validate input
            if not date or not name:
                return JsonResponse({"error": "Date and name are required fields"}, status=400)

            # Parse and validate the date
            try:
                holiday_date = timezone.datetime.strptime(date, "%Y-%m-%d").date()
            except ValueError:
                return JsonResponse({"error": "Invalid date format. Use YYYY-MM-DD."}, status=400)

            # Check if the date is unique (no duplicate holidays)
            if Holiday.objects.filter(date=holiday_date).exists():
                return JsonResponse({"error": "A holiday already exists on this date."}, status=400)

            # Create the holiday
            holiday = Holiday.objects.create(
                date=holiday_date,
                name=name,
                description=description
            )

            # Return success response with the created holiday details in IST
            ist = pytz.timezone("Asia/Kolkata")
            holiday_date_ist = timezone.make_aware(timezone.datetime.combine(holiday.date, time.min), ist)

            return JsonResponse({
                "message": "Holiday created successfully",
                "date": holiday_date_ist.isoformat(),
                "name": holiday.name,
                "description": holiday.description
            }, status=201)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    return JsonResponse({"error": "Invalid request method"}, status=405)






def list_holidays(request):
    if request.method == "GET":
        try:
            # Get the year from the query parameter, default to current year
            year = request.GET.get("year", timezone.now().year)
            try:
                year = int(year)
            except ValueError:
                return JsonResponse({"error": "Invalid year format. Use a numeric year (e.g., 2025)."}, status=400)

            # Fetch holidays for the specified year
            ist = pytz.timezone("Asia/Kolkata")
            start_date = timezone.datetime(year, 1, 1).astimezone(ist).date()
            end_date = timezone.datetime(year, 12, 31).astimezone(ist).date()

            holidays = Holiday.objects.filter(date__range=(start_date, end_date)).order_by('date')

            # Format holidays for the response
            holidays_list = [
                {
                    "date": holiday.date.isoformat(),
                    "name": holiday.name,
                    "description": holiday.description or ""
                }
                for holiday in holidays
            ]

            return JsonResponse({
                "message": f"Holidays for {year} listed successfully",
                "holidays": holidays_list,
                "year": year
            }, status=200)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    return JsonResponse({"error": "Invalid request method"}, status=405)







def leave_balances(request):
    if request.method == "GET":
        try:
            # Get the current user
            user_id = request.GET.get("user_id")

            user = User.objects.get(id= int(user_id))

            # Get the year from the query parameter, default to current year
            year = request.GET.get("year", timezone.now().year)
            try:
                year = int(year)
            except ValueError:
                return JsonResponse({"error": "Invalid year format. Use a numeric year (e.g., 2025)."}, status=400)

            # Calculate leave balances for the current year
            ist = pytz.timezone("Asia/Kolkata")
            start_date = timezone.datetime(year, 1, 1).astimezone(ist).date()
            end_date = timezone.datetime(year, 12, 31).astimezone(ist).date()

            used_leaves = Leave.objects.filter(
                user=user,
                date__range=(start_date, end_date),
                status__in=["Approved", "Pending"]  # Consider both pending and approved leaves
            ).exclude(leave_type="Lose of Pay")  # Exclude Lose of Pay from counting

            casual_leaves_used = used_leaves.filter(leave_type="Casual Leave").count()
            paid_leaves_used = used_leaves.filter(leave_type="Paid Leave").count()
            sick_leaves_used = used_leaves.filter(leave_type="Sick Leave").count()

            # Define leave limits per year
            CASUAL_LEAVE_LIMIT = 10
            PAID_LEAVE_LIMIT = 10
            SICK_LEAVE_LIMIT = 8

            balances = {
                "casual": CASUAL_LEAVE_LIMIT - casual_leaves_used,
                "paid": PAID_LEAVE_LIMIT - paid_leaves_used,
                "sick": SICK_LEAVE_LIMIT - sick_leaves_used,
            }

            return JsonResponse({
                "message": f"Leave balances for {year} retrieved successfully",
                "balances": balances,
                "year": year
            }, status=200)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    return JsonResponse({"error": "Invalid request method"}, status=405)






def view_attendance(request):
    from django.utils import timezone
    from datetime import timedelta
    if request.method == "GET":
        print("Coming Here")
        try:
            # Get user_id, year, and month from query parameters
            user_id = request.GET.get("user_id")
            year = request.GET.get("year", timezone.now().year)
            month = request.GET.get("month")  # Optional for monthly view

            try:
                year = int(year)
                month = int(month) if month else None
                if month and not (1 <= month <= 12):
                    return JsonResponse({"error": "Invalid month. Use 1-12."}, status=400)
            except ValueError:
                return JsonResponse({"error": "Invalid year or month format. Use numeric values."}, status=400)

            # Get the user (current user or specified user_id, with permission checks)
            if user_id:
                try:
                    user_id = int(user_id)  # Ensure user_id is an integer
                    user = User.objects.get(id=user_id)
                    # Check if the requesting user is authorized to view this user's attendance
                except (ValueError, User.DoesNotExist):
                    return JsonResponse({"error": "Invalid or non-existent user ID."}, status=400)
            else:
                user = request.user  # Default to current user if no user_id provided

            # Calculate date range for the current year or specified month (past days only)
            ist = pytz.timezone("Asia/Kolkata")
            current_date = timezone.now().astimezone(ist).date()
            if month:
                start_date = timezone.datetime(year, month, 1).astimezone(ist).date()
                end_date = (start_date + timedelta(days=31)).replace(day=1) - timedelta(days=1)
                end_date = min(end_date, current_date)  # Limit to past days
            else:
                start_date = timezone.datetime(year, 1, 1).astimezone(ist).date()
                end_date = min(current_date, timezone.datetime(year, 12, 31).astimezone(ist).date())

            if start_date > end_date:
                return JsonResponse({"error": "No past days available for this period."}, status=400)

            # Fetch attendance, leave, and holiday data for the user and period
            attendance_records = Attendance.objects.filter(
                user=user,
                date__range=(start_date, end_date)
            ).order_by('date')

            leave_records = Leave.objects.filter(
                user=user,
                date__range=(start_date, end_date),
                status__in=["Approved", "Pending"]  # Consider only approved or pending leaves
            ).order_by('date')

            holidays = Holiday.objects.filter(
                date__range=(start_date, end_date)
            ).order_by('date')

            # Prepare daily records for past days (yearly or monthly)
            daily_records = []
            for date in (start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1)):
                record = {
                    "date": date.strftime("%b %d"),  # Format as "Jan 1"
                    "status": "Absent",  # Default status
                    "punch_in_time": None,
                    "punch_out_time": None,
                    "work_type": None,
                    "leave_type": None,
                    "leave_reason": None,
                    "leave_status": None,  # Add leave status (Pending/Approved)
                    "is_holiday": False,
                    "holiday_name": None,
                    "punch_in_status": None,  # Early, Late, or On Time
                    "punch_out_status": None,  # Early, Late, or On Time
                    "special_day": None,  # For Sundays, Second/Fourth Saturdays
                    "half_day_option": None  # For half-day leaves
                }

                # Check for special days (Sunday, Second/Fourth Saturday)
                day_of_week = date.weekday()  # 0 = Monday, 6 = Sunday
                if day_of_week == 6:  # Sunday
                    record["status"] = "Sunday"
                    record["special_day"] = "Sunday"
                else:
                    # Check for Saturdays (weekday = 5)
                    if day_of_week == 5:  # Saturday
                        # Find the week number (1-based) of the Saturday
                        first_day_of_month = timezone.datetime(date.year, date.month, 1).astimezone(ist).date()
                        weeks_in_month = (date - first_day_of_month).days // 7 + 1
                        if weeks_in_month in [2, 4]:  # Second or Fourth Saturday
                            record["status"] = f"{weeks_in_month}th Saturday"
                            record["special_day"] = f"{weeks_in_month}th Saturday"

                # Check for attendance (overrides special days if present)
                attendance = attendance_records.filter(date=date).first()
                if attendance:
                    record["status"] = "Working"
                    record["punch_in_time"] = attendance.punch_in_time.astimezone(ist).strftime("%I:%M %p") if attendance.punch_in_time else None
                    record["punch_out_time"] = attendance.punch_out_time.astimezone(ist).strftime("%I:%M %p") if attendance.punch_out_time else None
                    record["work_type"] = attendance.work_type
                    # Determine punch-in status (before/after 9:30 AM IST)
                    if attendance.punch_in_time:
                        punch_in_time = attendance.punch_in_time.astimezone(ist)
                        if punch_in_time.hour < 9 or (punch_in_time.hour == 9 and punch_in_time.minute <= 30):
                            record["punch_in_status"] = "Early"
                        elif punch_in_time.hour > 9 or (punch_in_time.hour == 9 and punch_in_time.minute > 30):
                            record["punch_in_status"] = "Late"
                        else:
                            record["punch_in_status"] = "On Time"
                    # Determine punch-out status (before/after 6:30 PM IST)
                    if attendance.punch_out_time:
                        punch_out_time = attendance.punch_out_time.astimezone(ist)
                        if punch_out_time.hour < 18 or (punch_out_time.hour == 18 and punch_out_time.minute < 30):
                            record["punch_out_status"] = "Early"
                        elif punch_out_time.hour > 18 or (punch_out_time.hour == 18 and punch_out_time.minute > 30):
                            record["punch_out_status"] = "Late"
                        else:
                            record["punch_out_status"] = "On Time"

                # Check for leave (overrides attendance and special days if exists on the same day)
                leave = leave_records.filter(date=date).first()
                if leave:
                    record["status"] = "Leave"
                    record["leave_type"] = leave.leave_type
                    record["leave_reason"] = leave.reason
                    record["leave_status"] = leave.status  # Add leave status (Pending/Approved)
                    record["half_day_option"] = leave.half_day_option if leave.is_half_day() else None
                    # Only reclassify to Lose of Pay if no punch-in and the leave is Pending (not Approved)
                    if not attendance and leave.status == "Pending" and leave.leave_type in [
                        "Full Day - Casual Leave", "Full Day - Sick Leave", "Full Day - Paid Leave",
                        "Half Day - First Half - Casual Leave", "Half Day - Second Half - Casual Leave",
                        "Half Day - First Half - Sick Leave", "Half Day - Second Half - Sick Leave",
                        "Half Day - First Half - Paid Leave", "Half Day - Second Half - Paid Leave"
                    ]:
                        if "Half Day" in leave.leave_type:
                            new_leave_type = leave.leave_type.replace(leave.leave_type.split(" - ")[2], "Lose of Pay")
                            record["leave_type"] = new_leave_type
                            record["leave_reason"] = "Forgot to punch in" if not record["leave_reason"] else f"{record['leave_reason']}, Forgot to punch in"
                        else:
                            record["leave_type"] = "Full Day - Lose of Pay"
                            record["leave_reason"] = "Forgot to punch in" if not record["leave_reason"] else f"{record['leave_reason']}, Forgot to punch in"

                # Check for holiday (overrides all if exists on the same day)
                holiday = holidays.filter(date=date).first()
                if holiday:
                    record["status"] = "Holiday"
                    record["is_holiday"] = True
                    record["holiday_name"] = holiday.name

                # Format the record as requested (e.g., "Jan 1: Leave, Reason: forgot to punch in, Lose of Pay, Status: Pending")
                formatted_record = f"{record['date']}: {record['status']}"
                if record["special_day"]:
                    formatted_record = f"{record['date']}: {record['special_day']}"
                if record["status"] == "Working":
                    punch_info = []
                    if record["punch_in_time"]:
                        punch_info.append(f"Punch-in on {record['punch_in_time']} {record['punch_in_status'] or ''}")
                    if record["punch_out_time"]:
                        punch_info.append(f"Punch-out on {record['punch_out_time']} {record['punch_out_status'] or ''}")
                    if record["work_type"]:
                        punch_info.append(f"{record['work_type']}")
                    if punch_info:
                        formatted_record += ", " + ", ".join(punch_info)
                elif record["status"] == "Leave":
                    if record["leave_type"]:
                        formatted_record += f", {record['leave_type'].split(' - ')[-1]}"
                    if record["half_day_option"]:
                        formatted_record += f" ({record['half_day_option']})"
                    if record["leave_reason"]:
                        formatted_record += f", Reason: {record['leave_reason']}"
                    if record["leave_status"]:
                        formatted_record += f", Status: {record['leave_status']}"
                elif record["status"] == "Holiday" and record["holiday_name"]:
                    formatted_record += f", {record['holiday_name']}"

                daily_records.append(formatted_record)

            # Monthly or yearly overview (count all used leaves across the year for pending_leaves)
            if month:
                total_days = (end_date - start_date).days + 1
                working_days_base = total_days
                # Subtract Sundays, Second/Fourth Saturdays, and holidays
                for date in (start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1)):
                    day_of_week = date.weekday()
                    if day_of_week == 6:  # Sunday
                        working_days_base -= 1
                    elif day_of_week == 5:  # Saturday
                        first_day_of_month = timezone.datetime(year, month, 1).astimezone(ist).date()
                        weeks_in_month = (date - first_day_of_month).days // 7 + 1
                        if weeks_in_month in [2, 4]:  # Second or Fourth Saturday
                            working_days_base -= 1
                    if holidays.filter(date=date).exists():
                        working_days_base -= 1

                # Only count approved leaves for leave_days (ignore pending)
                approved_leave_records = Leave.objects.filter(
                    user=user,
                    date__range=(start_date, end_date),  # Only count leaves in this month
                    status="Approved"
                )
                # Count half-day leaves as 0.5 days within the month for approved leaves only
                full_day_leaves = approved_leave_records.filter(leave_type__contains="Full Day").count()
                half_day_leaves = approved_leave_records.filter(leave_type__contains="Half Day").count() / 2
                total_leave_days = full_day_leaves + half_day_leaves
                net_working_days = working_days_base - total_leave_days

                # Calculate leave_days for approved leaves only within the month
                overview = {
                    "total_days": total_days,
                    "working_days_base": working_days_base,
                    "net_working_days": net_working_days,
                    "holiday_days": holidays.count(),
                    "leave_days": {
                        "casual": sum(0.5 if "Half Day" in lt else 1 for lt in approved_leave_records.filter(leave_type__in=[
                            "Full Day - Casual Leave", "Half Day - First Half - Casual Leave", "Half Day - Second Half - Casual Leave"
                        ]).values_list('leave_type', flat=True)),
                        "sick": sum(0.5 if "Half Day" in lt else 1 for lt in approved_leave_records.filter(leave_type__in=[
                            "Full Day - Sick Leave", "Half Day - First Half - Sick Leave", "Half Day - Second Half - Sick Leave"
                        ]).values_list('leave_type', flat=True)),
                        "paid": sum(0.5 if "Half Day" in lt else 1 for lt in approved_leave_records.filter(leave_type__in=[
                            "Full Day - Paid Leave", "Half Day - First Half - Paid Leave", "Half Day - Second Half - Paid Leave"
                        ]).values_list('leave_type', flat=True)),
                        "lose_of_pay": sum(0.5 if "Half Day" in lt else 1 for lt in approved_leave_records.filter(leave_type__in=[
                            "Full Day - Lose of Pay", "Half Day - First Half - Lose of Pay", "Half Day - Second Half - Lose of Pay"
                        ]).values_list('leave_type', flat=True)),
                    },
                    "pending_leaves": {
                        # Calculate pending leaves (all used leaves across the year, approved or pending) for balance
                        "casual": max(0, 10 - sum(0.5 if "Half Day" in lt else 1 for lt in Leave.objects.filter(
                            user=user,
                            date__year=year,
                            leave_type__in=["Full Day - Casual Leave", "Half Day - First Half - Casual Leave", "Half Day - Second Half - Casual Leave"],
                            status__in=["Approved", "Pending"]  # Include both approved and pending for total usage
                        ).values_list('leave_type', flat=True))),
                        "sick": max(0, 8 - sum(0.5 if "Half Day" in lt else 1 for lt in Leave.objects.filter(
                            user=user,
                            date__year=year,
                            leave_type__in=["Full Day - Sick Leave", "Half Day - First Half - Sick Leave", "Half Day - Second Half - Sick Leave"],
                            status__in=["Approved", "Pending"]
                        ).values_list('leave_type', flat=True))),
                        "paid": max(0, 10 - sum(0.5 if "Half Day" in lt else 1 for lt in Leave.objects.filter(
                            user=user,
                            date__year=year,
                            leave_type__in=["Full Day - Paid Leave", "Half Day - First Half - Paid Leave", "Half Day - Second Half - Paid Leave"],
                            status__in=["Approved", "Pending"]
                        ).values_list('leave_type', flat=True))),
                    },
                    "late_punch_ins": attendance_records.filter(status_punchin="Late").count(),
                    "early_punch_outs": attendance_records.filter(status_punchout="Early").count()
                }
            else:
                # Yearly overview (count all used leaves across the year for pending_leaves)
                total_days = (end_date - start_date).days + 1
                working_days_base = total_days
                # Subtract Sundays, Second/Fourth Saturdays, and holidays for the year
                for date in (start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1)):
                    day_of_week = date.weekday()
                    if day_of_week == 6:  # Sunday
                        working_days_base -= 1
                    elif day_of_week == 5:  # Saturday
                        # Determine if it's the 2nd or 4th Saturday of its month
                        month_start = timezone.datetime(date.year, date.month, 1).astimezone(ist).date()
                        weeks_in_month = (date - month_start).days // 7 + 1
                        if weeks_in_month in [2, 4]:  # Second or Fourth Saturday
                            working_days_base -= 1
                    if holidays.filter(date=date).exists():
                        working_days_base -= 1

                # Only count approved leaves for leave_days (ignore pending)
                approved_leave_records = Leave.objects.filter(
                    user=user,
                    date__range=(start_date, end_date),  # Only count leaves in this year
                    status="Approved"
                )
                # Count half-day leaves as 0.5 days within the year for approved leaves only
                full_day_leaves = approved_leave_records.filter(leave_type__contains="Full Day").count()
                half_day_leaves = approved_leave_records.filter(leave_type__contains="Half Day").count() / 2
                total_leave_days = full_day_leaves + half_day_leaves
                net_working_days = working_days_base - total_leave_days

                # Calculate leave_days for approved leaves only across the year
                overview = {
                    "total_days": total_days,
                    "working_days_base": working_days_base,
                    "net_working_days": net_working_days,
                    "holiday_days": holidays.count(),
                    "leave_days": {
                        "casual": sum(0.5 if "Half Day" in lt else 1 for lt in approved_leave_records.filter(leave_type__in=[
                            "Full Day - Casual Leave", "Half Day - First Half - Casual Leave", "Half Day - Second Half - Casual Leave"
                        ]).values_list('leave_type', flat=True)),
                        "sick": sum(0.5 if "Half Day" in lt else 1 for lt in approved_leave_records.filter(leave_type__in=[
                            "Full Day - Sick Leave", "Half Day - First Half - Sick Leave", "Half Day - Second Half - Sick Leave"
                        ]).values_list('leave_type', flat=True)),
                        "paid": sum(0.5 if "Half Day" in lt else 1 for lt in approved_leave_records.filter(leave_type__in=[
                            "Full Day - Paid Leave", "Half Day - First Half - Paid Leave", "Half Day - Second Half - Paid Leave"
                        ]).values_list('leave_type', flat=True)),
                        "lose_of_pay": sum(0.5 if "Half Day" in lt else 1 for lt in approved_leave_records.filter(leave_type__in=[
                            "Full Day - Lose of Pay", "Half Day - First Half - Lose of Pay", "Half Day - Second Half - Lose of Pay"
                        ]).values_list('leave_type', flat=True)),
                    },
                    "pending_leaves": {
                        # Calculate pending leaves (all used leaves across the year, approved or pending) for balance
                        "casual": max(0, 10 - sum(0.5 if "Half Day" in lt else 1 for lt in Leave.objects.filter(
                            user=user,
                            date__year=year,
                            leave_type__in=["Full Day - Casual Leave", "Half Day - First Half - Casual Leave", "Half Day - Second Half - Casual Leave"],
                            status__in=["Approved", "Pending"]  # Include both approved and pending for total usage
                        ).values_list('leave_type', flat=True))),
                        "sick": max(0, 8 - sum(0.5 if "Half Day" in lt else 1 for lt in Leave.objects.filter(
                            user=user,
                            date__year=year,
                            leave_type__in=["Full Day - Sick Leave", "Half Day - First Half - Sick Leave", "Half Day - Second Half - Sick Leave"],
                            status__in=["Approved", "Pending"]
                        ).values_list('leave_type', flat=True))),
                        "paid": max(0, 10 - sum(0.5 if "Half Day" in lt else 1 for lt in Leave.objects.filter(
                            user=user,
                            date__year=year,
                            leave_type__in=["Full Day - Paid Leave", "Half Day - First Half - Paid Leave", "Half Day - Second Half - Paid Leave"],
                            status__in=["Approved", "Pending"]
                        ).values_list('leave_type', flat=True))),
                    },
                    "late_punch_ins": attendance_records.filter(status_punchin="Late").count(),
                    "early_punch_outs": attendance_records.filter(status_punchout="Early").count()
                }

            return JsonResponse({
                "message": f"Attendance report for {user.username} in {month or 'Year'} {year} retrieved successfully",
                "daily_records": daily_records,
                "overview": overview,
                "user_id": user.id
            }, status=200)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    return JsonResponse({"error": "Invalid request method"}, status=405)





    
@csrf_exempt  # Keep this for now, or use @csrf_protect if enforcing CSRF (see previous advice)
def request_leave(request):
    from django.utils import timezone
    from datetime import time
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode('utf-8'))

            # Get the current user
            user_id = data.get("user")
            try:
                user = User.objects.get(id=int(user_id))
            except (ValueError, User.DoesNotExist):
                return JsonResponse({"error": "Invalid or non-existent user ID."}, status=400)

            if not user:
                return JsonResponse({"error": "Not Logged In"}, status=400)

            print("First Hello")

            # Parse the JSON data from the request body
            date = data.get("date")
            leave_type = data.get("leave_type")
            reason = data.get("reason", "Personal reason")  # Optional, defaults to "Personal reason"

            # Validate input
            if not date or not leave_type:
                return JsonResponse({"error": "Date and leave type are required fields"}, status=400)

            # Parse and validate the date
            try:
                leave_date = timezone.datetime.strptime(date, "%Y-%m-%d").date()
            except ValueError:
                return JsonResponse({"error": "Invalid date format. Use YYYY-MM-DD."}, status=400)

            # Check if the date is in the past (prevent past dates)
            ist = pytz.timezone("Asia/Kolkata")
            current_date = timezone.now().astimezone(ist).date()
            if leave_date < current_date:
                return JsonResponse({"error": "Cannot request leave for past dates."}, status=400)

            # Optionally, limit future dates (e.g., 1 year in advance)
            max_future_date = current_date + timezone.timedelta(days=365)  # Allow up to 1 year in advance
            if leave_date > max_future_date:
                return JsonResponse({"error": "Cannot request leave more than 1 year in advance."}, status=400)

            # Check if the date is a holiday
            if Holiday.objects.filter(date=leave_date).exists():
                return JsonResponse({"error": "Cannot request leave on a holiday."}, status=400)

            # Check if a leave already exists for the same user and date
            if Leave.objects.filter(user=user, date=leave_date).exists():
                return JsonResponse({"error": "A leave request already exists for this date."}, status=400)

            # Determine the effective leave type (all leave types allowed with full/half-day options)
            effective_leave_type = leave_type
            valid_leave_types = [
                "Full Day - Casual Leave", "Half Day - First Half - Casual Leave", "Half Day - Second Half - Casual Leave",
                "Full Day - Paid Leave", "Half Day - First Half - Paid Leave", "Half Day - Second Half - Paid Leave",
                "Full Day - Sick Leave", "Half Day - First Half - Sick Leave", "Half Day - Second Half - Sick Leave",
                "Full Day - Lose of Pay", "Half Day - First Half - Lose of Pay", "Half Day - Second Half - Lose of Pay"
            ]
            if leave_type not in valid_leave_types:
                return JsonResponse({"error": "Invalid leave type. Only specified leave options are allowed."}, status=400)

            print("Hello")

            # Calculate leave balances for the current year
            current_year = timezone.now().astimezone(ist).year
            start_date = timezone.datetime(current_year, 1, 1).astimezone(ist).date()
            end_date = timezone.datetime(current_year, 12, 31).astimezone(ist).date()

            used_leaves = Leave.objects.filter(
                user=user,
                date__range=(start_date, end_date),
                status__in=["Approved", "Pending"]
            ).exclude(leave_type__contains="Lose of Pay")  # Exclude Lose of Pay from counting

            # Calculate used leaves for each type, counting half-day leaves as 0.5 days
            casual_leaves_used = sum(0.5 if "Half Day" in lt else 1 for lt in used_leaves.filter(leave_type__contains="Casual Leave").values_list('leave_type', flat=True))
            paid_leaves_used = sum(0.5 if "Half Day" in lt else 1 for lt in used_leaves.filter(leave_type__contains="Paid Leave").values_list('leave_type', flat=True))
            sick_leaves_used = sum(0.5 if "Half Day" in lt else 1 for lt in used_leaves.filter(leave_type__contains="Sick Leave").values_list('leave_type', flat=True))

            # Define leave limits per year (in full-day equivalents)
            CASUAL_LEAVE_LIMIT = 10
            PAID_LEAVE_LIMIT = 10
            SICK_LEAVE_LIMIT = 8

            # Check if adding this leave exceeds the respective limit
            if "Casual Leave" in leave_type:
                if "Half Day" in leave_type:
                    if casual_leaves_used >= CASUAL_LEAVE_LIMIT - 0.5:
                        effective_leave_type = leave_type.replace("Casual Leave", "Lose of Pay")
                else:  # Full Day
                    if casual_leaves_used >= CASUAL_LEAVE_LIMIT:
                        effective_leave_type = "Full Day - Lose of Pay"
            elif "Paid Leave" in leave_type:
                if "Half Day" in leave_type:
                    if paid_leaves_used >= PAID_LEAVE_LIMIT - 0.5:
                        effective_leave_type = leave_type.replace("Paid Leave", "Lose of Pay")
                else:  # Full Day
                    if paid_leaves_used >= PAID_LEAVE_LIMIT:
                        effective_leave_type = "Full Day - Lose of Pay"
            elif "Sick Leave" in leave_type:
                if "Half Day" in leave_type:
                    if sick_leaves_used >= SICK_LEAVE_LIMIT - 0.5:
                        effective_leave_type = leave_type.replace("Sick Leave", "Lose of Pay")
                else:  # Full Day
                    if sick_leaves_used >= SICK_LEAVE_LIMIT:
                        effective_leave_type = "Full Day - Lose of Pay"
            # No limit check for Lose of Pay (it’s unlimited)

            print("Third Hello")

            # Extract half_day_option from leave_type if applicable
            half_day_option = ""
            if "Half Day" in effective_leave_type:
                if "First Half" in effective_leave_type:
                    half_day_option = "First Half"
                elif "Second Half" in effective_leave_type:
                    half_day_option = "Second Half"

            # Create the leave request with the effective leave type and status "Pending"
            leave = Leave.objects.create(
                user=user,
                date=leave_date,
                leave_type=effective_leave_type,
                half_day_option=half_day_option,
                reason=reason,
                status="Pending"
            )

            # Notify admins and managers
            admins = User.objects.filter(role='Admin')
            for admin in admins:
                Notification.objects.create(
                    user=admin,
                    message=f"{user.username} has requested for leave on {leave_date} {'(Half Day - ' + leave.half_day_option + ')' if leave.half_day_option else ''}",
                    type='leave',
                    leave=leave,
                    created_by=user
                )

            managers = User.objects.filter(role='Manager')
            for manager in managers:
                Notification.objects.create(
                    user=manager,
                    message=f"{user.username} has requested for leave on {leave_date} {'(Half Day - ' + leave.half_day_option + ')' if leave.half_day_option else ''}",
                    type='leave',
                    leave=leave,
                    created_by=user
                )

            # Return success response with the created leave details in IST
            leave_date_ist = timezone.make_aware(timezone.datetime.combine(leave.date, time.min), ist)

            return JsonResponse({
                "message": "Leave request submitted successfully",
                "date": leave_date_ist.isoformat(),
                "leave_type": leave.leave_type,
                "half_day_option": leave.half_day_option if leave.half_day_option else "Full Day",
                "reason": leave.reason,
                "status": leave.status,
                "effective_leave_type": effective_leave_type  # Indicate if it was adjusted to Lose of Pay
            }, status=201)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    return JsonResponse({"error": "Invalid request method"}, status=405)







def list_leave_requests(request):
    if request.method == "GET":
        try:
            user_id = request.GET.get("user_id")  # Get user_id from query parameter to filter leaves
            print(user_id)
            request_user = User.objects.get(id = int(user_id))


            # Check user role and permissions using request.user (authenticated user)
            if request_user.role not in ['Admin', 'Manager', 'Staff']:
                return JsonResponse({"error": "Permission denied. Only Admins, Managers, and Staff can view leave requests."}, status=403)

            # Staff users can only view their own leave requests
            if request_user.role == 'Staff':
                if user_id and str(request_user.id) != user_id:
                    return JsonResponse({"error": "Permission denied. You can only view your own leave requests."}, status=403)
                user_id = str(request_user.id)  # Default to current user's ID for Staff

            # Fetch leave requests based on user_id (if provided) or all for Admins/Managers
            if user_id:
                try:
                    user = User.objects.get(id=int(user_id))
                    leaves = Leave.objects.filter(user=user).select_related('user').order_by('-date')
                except (ValueError, User.DoesNotExist):
                    return JsonResponse({"error": "Invalid or non-existent user ID."}, status=400)
            else:
                leaves = Leave.objects.all().select_related('user').order_by('-date')  # Admins/Managers see all

            # Serialize leave requests
            leave_list = [
                {
                    "id": leave.id,
                    "user_id": leave.user.id,
                    "username": leave.user.username,
                    "date": timezone.make_aware(timezone.datetime.combine(leave.date, timezone.datetime.min.time()), pytz.timezone("Asia/Kolkata")).isoformat(),
                    "leave_type": leave.leave_type,
                    "half_day_option": leave.half_day_option if leave.half_day_option else "Full Day",
                    "reason": leave.reason,
                    "status": leave.status,
                }
                for leave in leaves
            ]

            return JsonResponse({
                "message": "Leave requests retrieved successfully",
                "leave_requests": leave_list
            }, status=200)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    return JsonResponse({"error": "Invalid request method"}, status=405)



@csrf_exempt
def leave_detail(request, leave_id):
    try:
        leave = Leave.objects.get(id=leave_id)

        # Get user_id from query parameter (optional)
        query_user_id = request.GET.get("user_id")
        request_user = User.objects.get(id = int(query_user_id))

        # Check user role and permissions
        if request_user.role not in ['Admin', 'Manager']:
            # Staff users can only view/manage their own leave requests
            if query_user_id and str(request_user.id) != query_user_id:
                return JsonResponse({"error": "Permission denied. You can only manage your own leave requests."}, status=403)
            if str(request_user.id) != str(leave.user.id):
                return JsonResponse({"error": "Permission denied. You can only manage your own leave requests."}, status=403)

        # For Admins/Managers, verify query_user_id matches leave.user.id if provided
        elif query_user_id:
            try:
                user = User.objects.get(id=int(query_user_id))
                if str(user.id) != str(leave.user.id):
                    return JsonResponse({"error": "Leave request does not belong to the specified user."}, status=400)
            except (ValueError, User.DoesNotExist):
                return JsonResponse({"error": "Invalid or non-existent user ID."}, status=400)

        if request.method == "GET":
            # Return leave details
            return JsonResponse({
                "message": "Leave details retrieved successfully",
                "id": leave.id,
                "user_id": leave.user.id,
                "username": leave.user.username,
                "date": timezone.make_aware(timezone.datetime.combine(leave.date, timezone.datetime.min.time()), pytz.timezone("Asia/Kolkata")).isoformat(),
                "leave_type": leave.leave_type,
                "half_day_option": leave.half_day_option if leave.half_day_option else "Full Day",
                "reason": leave.reason,
                "status": leave.status,
            }, status=200)

        elif request.method == "PATCH":
            # Handle accept/reject actions
            data = json.loads(request.body.decode('utf-8'))
            new_status = data.get("status")
            if new_status not in ["Approved", "Rejected"]:
                return JsonResponse({"error": "Invalid status. Use 'Approved' or 'Rejected'."}, status=400)

            # Ensure only Admins/Managers or the leave owner (Staff) can update status
            if request_user.role not in ['Admin', 'Manager'] and str(request_user.id) != str(leave.user.id):
                return JsonResponse({"error": "Permission denied. You can only manage your own leave requests."}, status=403)

            leave.status = new_status
            leave.save()

            # Notify the user about the status change
            ist = pytz.timezone("Asia/Kolkata")
            leave_date_ist = timezone.make_aware(timezone.datetime.combine(leave.date, timezone.datetime.min.time()), ist)
            Notification.objects.create(
                user=leave.user,
                message=f"Your leave request on {leave_date_ist.date()} {'(Half Day - ' + leave.half_day_option + ')' if leave.half_day_option else ''} has been {new_status.lower()}.",
                type='leave',
                leave=leave,
                created_by=request_user
            )

            return JsonResponse({
                "message": f"Leave request {new_status.lower()} successfully",
                "id": leave.id,
                "status": leave.status
            }, status=200)

        return JsonResponse({"error": "Invalid request method"}, status=405)

    except Leave.DoesNotExist:
        return JsonResponse({"error": "Leave request not found."}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)





def check_punch_status(request):
    if request.method == "GET":
        try:
            user_id = request.GET.get("user_id")  # Get user_id from query parameter
            print(user_id)
            request_user = User.objects.get(id = int(user_id))

            # Check user role and permissions
            if request_user.role not in ['Admin', 'Manager', 'Staff']:
                return JsonResponse({"error": "Permission denied. Only Admins, Managers, and Staff can check punch status."}, status=403)

            # Staff users can only check their own punch status
            if request_user.role == 'Staff':
                if user_id and str(request_user.id) != user_id:
                    return JsonResponse({"error": "Permission denied. You can only check your own punch status."}, status=403)
                user_id = str(request_user.id)  # Default to current user's ID for Staff

            # Fetch or validate user
            if user_id:
                try:
                    user = User.objects.get(id=int(user_id))
                except (ValueError, User.DoesNotExist):
                    return JsonResponse({"error": "Invalid or non-existent user ID."}, status=400)
            else:
                user = request_user  # Default to current user for Admins/Managers

            # Get today's date in IST
            ist = pytz.timezone("Asia/Kolkata")
            today = timezone.now().astimezone(ist).date()

            # Check if the user has a punch-in record for today
            attendance = Attendance.objects.filter(
                user=user,
                date=today
            ).first()
            
            
            print(attendance)

            punch_status = {
                "user_id": user.id,
                "username": user.username,
                "is_punched_in": bool(attendance and attendance.punch_in_time),  # True if punched in, False otherwise
                "punch_in_time": attendance.punch_in_time.astimezone(ist).strftime("%I:%M %p") if attendance and attendance.punch_in_time else None,
                "punch_out_time": attendance.punch_out_time.astimezone(ist).strftime("%I:%M %p") if attendance and attendance.punch_out_time else None,
            }

            return JsonResponse({
                "message": "Punch status retrieved successfully",
                "punch_status": punch_status
            }, status=200)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    return JsonResponse({"error": "Invalid request method"}, status=405)