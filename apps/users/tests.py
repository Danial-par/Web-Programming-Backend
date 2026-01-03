from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()


class RoleAssignmentTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            phone="09000000001",
            password="AdminPass123",
        )
        self.support = User.objects.create_user(
            username="support",
            email="support@example.com",
            phone="09000000002",
            password="SupportPass123",
            role="SUPPORT",
        )
        self.target = User.objects.create_user(
            username="target",
            email="target@example.com",
            phone="09000000003",
            password="TargetPass123",
            role="CUSTOMER",
        )

    def test_support_cannot_assign_support_but_admin_can(self):
        url = reverse("role-set-support", kwargs={"pk": self.target.id})

        # SUPPORT tries -> forbidden
        self.client.force_authenticate(user=self.support)
        res = self.client.patch(url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

        # ADMIN tries -> ok
        self.client.force_authenticate(user=self.admin)
        res = self.client.patch(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.target.refresh_from_db()
        self.assertEqual(self.target.role, "SUPPORT")

    def test_support_can_assign_contractor(self):
        target2 = User.objects.create_user(
            username="target2",
            email="target2@example.com",
            phone="09000000004",
            password="TargetPass123",
            role="CUSTOMER",
        )
        url = reverse("role-set-contractor", kwargs={"pk": target2.id})

        self.client.force_authenticate(user=self.support)
        res = self.client.patch(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        target2.refresh_from_db()
        self.assertEqual(target2.role, "CONTRACTOR")
