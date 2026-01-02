# apps/users/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        CUSTOMER = "CUSTOMER", "Customer"
        CONTRACTOR = "CONTRACTOR", "Contractor"
        SUPPORT = "SUPPORT", "Support"

    # Keep username for simplicity (lets you login by username too)
    # Make email unique as required
    email = models.EmailField(unique=True)

    # Phone must be unique (login identifier)
    phone = models.CharField(max_length=20, unique=True)

    # Role: admin is handled by is_superuser/is_staff
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.CUSTOMER,
    )

    def __str__(self) -> str:
        return f"{self.username} ({self.role})"
