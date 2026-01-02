from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Roles required by the homework:
    - CUSTOMER (normal user)
    - CONTRACTOR (service provider)
    - SUPPORT (support staff)
    Admin is Django superuser (is_superuser=True).
    """

    class Role(models.TextChoices):
        CUSTOMER = "CUSTOMER", "Customer"
        CONTRACTOR = "CONTRACTOR", "Contractor"
        SUPPORT = "SUPPORT", "Support"

    # Keep username from AbstractUser to support login via username.
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, unique=True)

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.CUSTOMER,
        db_index=True,
    )

    def __str__(self) -> str:
        return f"{self.username} ({self.role})"
