from django.shortcuts import render
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from .serializers import RegisterSerializer, CustomTokenObtainPairSerializer, UserSerializer
from .supabase_serializers import CompanySerializer
from django.utils import timezone


# Create your views here.
from .supabase_models import SbUser


# Map Django roles to Supabase roles
ROLE_MAPPING = {
    'jobseeker': 'job_seeker',  # Supabase expects 'job_seeker'
    'company': 'company',       # This one matches
    'admin': 'admin'           # Just in case
}


class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = CustomTokenObtainPairSerializer.get_token(user)
            access = refresh.access_token

            # Create corresponding SbUser record
            try:
                now = timezone.now()
                full_name = f"{user.first_name} {user.last_name}".strip()
                if not full_name:
                    full_name = user.username
                    
                # Map the Django role to Supabase role
                supabase_role = ROLE_MAPPING.get(user.role, 'seeker')  # Default to seeker if mapping not found
                
                SbUser.objects.create(
                    email=user.email,
                    role=supabase_role,
                    full_name=full_name,
                    password_hash=user.password,  # This is already hashed by Django
                    created_at=now,
                    updated_at=now,
                    company=user if user.role == 'company' else None
                )
            except Exception as e:
                return Response(
                    {
                        "detail": "User created but SbUser creation failed",
                        "error": str(e),
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
            
            return Response(
                {
                    "access": str(access),
                    "refresh": str(refresh),
                    "user": UserSerializer(user).data,
                },
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(TokenObtainPairView):
    permission_classes = [permissions.AllowAny]
    serializer_class = CustomTokenObtainPairSerializer
