from django.shortcuts import render
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from .serializers import RegisterSerializer, CustomTokenObtainPairSerializer, UserSerializer
from .supabase_serializers import CompanySerializer
from django.utils import timezone


# Create your views here.


class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = CustomTokenObtainPairSerializer.get_token(user)
            access = refresh.access_token
            # Auto-create a company record after issuing tokens
            # if user.role == "company":
            #     try:
            #         company_payload = {
            #             "name": f"{user.username} Company",
            #             "website": "",
            #             "location": "Cairo",
            #             "created_at": timezone.now(),
            #         }
            #         company_serializer = CompanySerializer(data=company_payload)
            #         if company_serializer.is_valid():
            #             company_serializer.save()
            #         # else: silently ignore to avoid failing registration flow
            #     except Exception:
            #         pass
            
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
