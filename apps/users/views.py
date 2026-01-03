from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404

from rest_framework import generics, permissions, status
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.views import APIView

from drf_spectacular.utils import (
    extend_schema,
    OpenApiExample,
    OpenApiResponse,
)

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
        tags=["Auth"],
        summary="Register",
        description="Create a new user account (defaults to CUSTOMER role). Returns token for TokenAuth.",
        request=RegisterSerializer,
        responses={
            201: AuthResponseSerializer,
            400: OpenApiResponse(description="Validation error"),
        },
        examples=[
            OpenApiExample(
                "Register request",
                value={
                    "username": "danial",
                    "email": "danial@example.com",
                    "phone": "09120000000",
                    "password": "StrongPass123",
                },
                request_only=True,
            ),
            OpenApiExample(
                "Register response",
                value={
                    "token": "TOKEN_STRING",
                    "user": {
                        "id": 1,
                        "username": "danial",
                        "email": "danial@example.com",
                        "phone": "09120000000",
                        "role": "CUSTOMER",
                        "is_superuser": False,
                    },
                },
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
        tags=["Auth"],
        summary="Login",
        description="Login with identifier + password. Identifier may be username OR email OR phone.",
        request=LoginSerializer,
        responses={
            200: AuthResponseSerializer,
            400: OpenApiResponse(description="Invalid credentials"),
        },
        examples=[
            OpenApiExample(
                "Login request using email",
                value={"identifier": "danial@example.com", "password": "StrongPass123"},
                request_only=True,
            ),
            OpenApiExample(
                "Login request using phone",
                value={"identifier": "09120000000", "password": "StrongPass123"},
                request_only=True,
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
        tags=["Auth"],
        summary="Assign SUPPORT role",
        description="ADMIN(superuser) only: set a user's role to SUPPORT.",
        responses={200: RoleChangeResponseSerializer, 403: OpenApiResponse(description="Forbidden")},
        examples=[
            OpenApiExample(
                "Role change response",
                value={
                    "id": 10,
                    "username": "support1",
                    "email": "support1@example.com",
                    "phone": "09123334444",
                    "role": "SUPPORT",
                    "is_superuser": False,
                },
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
        tags=["Auth"],
        summary="Assign CONTRACTOR role",
        description="SUPPORT or ADMIN: set a user's role to CONTRACTOR.",
        responses={200: RoleChangeResponseSerializer, 403: OpenApiResponse(description="Forbidden")},
    )
    def patch(self, request, pk: int):
        user = get_object_or_404(User, pk=pk)

        if user.is_superuser:
            return Response({"detail": "Cannot change role of a superuser."}, status=status.HTTP_400_BAD_REQUEST)

        user.role = "CONTRACTOR"
        user.save(update_fields=["role"])
        return Response(RoleChangeResponseSerializer(user).data, status=status.HTTP_200_OK)
