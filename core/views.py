from django.contrib.auth import authenticate
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from django.conf import settings
from rest_framework.permissions import AllowAny
from .serializers import LoginSerializer
from .models import User
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import IsAuthenticated



class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            username = serializer.validated_data['username']  # Use 'email' or 'username' as per your custom model
            password = serializer.validated_data['password']
            key = serializer.validated_data['key']

            # Check API key
            if key != settings.SECRET_KEY_API:
                return Response({"detail": "Invalid key"}, status=status.HTTP_400_BAD_REQUEST)

            try:
                # Get the user explicitly from your custom User model
                user = User.objects.get(username=username)  # Change to 'email=username' if using email
                print(user)
            except User.DoesNotExist:
                return Response({"detail": "Invalid credentials"}, status=status.HTTP_400_BAD_REQUEST)

            # Verify password using the custom User model's check_password method
            if user.password == password:
                refresh = RefreshToken.for_user(user)
                return Response({
                    "detail": "Login successful",
                    "access_token": str(refresh.access_token),
                    "refresh_token": str(refresh),
                }, status=status.HTTP_200_OK)
            return Response({"detail": "Invalid credentials"}, status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)




class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]  # Ensure only authenticated users can access this view

    def get(self, request):
        # The JWTAuthentication class automatically extracts and validates the token
        authentication = JWTAuthentication()
        user, auth = authentication.authenticate(request)

        # Once authenticated, the 'user' object will contain the user details
        if user:
            # You can return the user's details in the response
            return Response({
                'username': user.username,
                'full_name': user.full_name,
                'email': user.email,
                'role': user.role,
                'department': user.department,
                'position': user.position,
            })
        else:
            return Response({"detail": "User not found or invalid token."}, status=401)