from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404

from rest_framework import generics, permissions, status
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.views import APIView

from drf_spectacular.utils import OpenApiExample, extend_schema

from .permissions import IsAdmin, IsSupportOrAdmin
from .serializers import (
    AuthResponseSerializer,
    LoginSerializer,
    RegisterSerializer,
    RoleChangeResponseSerializer,
    UserPublicSerializer,
)

User = get_user_model()


class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        request=RegisterSerializer,
        responses={201: AuthResponseSerializer},
        examples=[
            OpenApiExample(
                "Register example",
                value={"username": "danial", "email": "danial@example.com", "phone": "09120000000", "password": "StrongPass123"},
                request_only=True,
            ),
            OpenApiExample(
                "Register response example",
                value={"token": "TOKEN_STRING", "user": {"id": 1, "username": "danial", "email": "danial@example.com", "phone": "09120000000", "role": "CUSTOMER", "is_superuser": False}},
                response_only=True,
            ),
        ],
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        token, _ = Token.objects.get_or_create(user=user)
        data = {"token": token.key, "user": UserPublicSerializer(user).data}
        return Response(data, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        request=LoginSerializer,
        responses={200: AuthResponseSerializer},
        examples=[
            OpenApiExample(
                "Login example (identifier can be username/email/phone)",
                value={"identifier": "danial@example.com", "password": "StrongPass123"},
                request_only=True,
            ),
            OpenApiExample(
                "Login response example",
                value={"token": "TOKEN_STRING", "user": {"id": 1, "username": "danial", "email": "danial@example.com", "phone": "09120000000", "role": "CUSTOMER", "is_superuser": False}},
                response_only=True,
            ),
        ],
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]
        token, _ = Token.objects.get_or_create(user=user)

        data = {"token": token.key, "user": UserPublicSerializer(user).data}
        return Response(data, status=status.HTTP_200_OK)


class MeView(generics.RetrieveAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserPublicSerializer

    def get_object(self):
        return self.request.user


class SetSupportRoleView(APIView):
    """
    Only ADMIN (superuser) can assign SUPPORT role. :contentReference[oaicite:2]{index=2}
    """
    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    @extend_schema(
        responses={200: RoleChangeResponseSerializer},
        examples=[
            OpenApiExample(
                "Response example",
                value={"id": 2, "username": "ali", "email": "ali@example.com", "phone": "09121111111", "role": "SUPPORT", "is_superuser": False},
                response_only=True,
            )
        ],
    )
    def patch(self, request, pk: int):
        user = get_object_or_404(User, pk=pk)

        # You can choose to disallow changing role of superusers; safe default:
        if user.is_superuser:
            return Response({"detail": "Cannot change role of a superuser."}, status=status.HTTP_400_BAD_REQUEST)

        user.role = "SUPPORT"
        user.save(update_fields=["role"])
        return Response(RoleChangeResponseSerializer(user).data, status=status.HTTP_200_OK)


class SetContractorRoleView(APIView):
    """
    ADMIN or SUPPORT can assign CONTRACTOR role. :contentReference[oaicite:3]{index=3}
    """
    permission_classes = [permissions.IsAuthenticated, IsSupportOrAdmin]

    @extend_schema(
        responses={200: RoleChangeResponseSerializer},
        examples=[
            OpenApiExample(
                "Response example",
                value={"id": 3, "username": "reza", "email": "reza@example.com", "phone": "09122222222", "role": "CONTRACTOR", "is_superuser": False},
                response_only=True,
            )
        ],
    )
    def patch(self, request, pk: int):
        user = get_object_or_404(User, pk=pk)

        if user.is_superuser:
            return Response({"detail": "Cannot change role of a superuser."}, status=status.HTTP_400_BAD_REQUEST)

        user.role = "CONTRACTOR"
        user.save(update_fields=["role"])
        return Response(RoleChangeResponseSerializer(user).data, status=status.HTTP_200_OK)
