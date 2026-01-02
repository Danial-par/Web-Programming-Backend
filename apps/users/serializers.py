from django.contrib.auth import authenticate, get_user_model
from rest_framework import serializers

User = get_user_model()


class UserPublicSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "email", "phone", "role", "is_superuser")
        read_only_fields = fields


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = ("username", "email", "phone", "password")

    def create(self, validated_data):
        # Default role is CUSTOMER (per model default)
        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            phone=validated_data["phone"],
            password=validated_data["password"],
        )
        return user


class LoginSerializer(serializers.Serializer):
    identifier = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        identifier = attrs["identifier"]
        password = attrs["password"]

        # Find by username OR email OR phone (per PDF requirement) :contentReference[oaicite:1]{index=1}
        user = (
            User.objects.filter(username=identifier).first()
            or User.objects.filter(email=identifier).first()
            or User.objects.filter(phone=identifier).first()
        )
        if not user:
            raise serializers.ValidationError({"identifier": "User not found."})

        # Authenticate using username/password (default Django backend)
        authed = authenticate(username=user.username, password=password)
        if not authed:
            raise serializers.ValidationError({"password": "Invalid credentials."})

        attrs["user"] = authed
        return attrs


class AuthResponseSerializer(serializers.Serializer):
    token = serializers.CharField()
    user = UserPublicSerializer()


class RoleChangeResponseSerializer(UserPublicSerializer):
    """
    Just a named serializer for role-change responses (same fields).
    """
    pass
