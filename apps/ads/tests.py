from datetime import timedelta

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()


class AdWorkflowTests(APITestCase):
    def setUp(self):
        self.customer = User.objects.create_user(
            username="customer",
            email="customer@example.com",
            phone="09000000100",
            password="CustomerPass123",
            role="CUSTOMER",
        )
        self.contractor = User.objects.create_user(
            username="contractor",
            email="contractor@example.com",
            phone="09000000101",
            password="ContractorPass123",
            role="CONTRACTOR",
        )
        self.support = User.objects.create_user(
            username="support",
            email="support2@example.com",
            phone="09000000102",
            password="SupportPass123",
            role="SUPPORT",
        )

    def _create_ad_as_customer(self):
        self.client.force_authenticate(user=self.customer)
        res = self.client.post(
            reverse("ad-list"),
            {"title": "Fix sink", "description": "Leaking", "category": "plumbing"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        return res.data["id"]

    def test_ad_lifecycle_happy_path_and_permissions(self):
        ad_id = self._create_ad_as_customer()

        # contractor applies
        self.client.force_authenticate(user=self.contractor)
        res = self.client.post(reverse("ad-apply", kwargs={"pk": ad_id}), {"note": "I can do it."}, format="json")
        self.assertIn(res.status_code, (status.HTTP_200_OK, status.HTTP_201_CREATED))
        self.assertEqual(res.data["status"], "APPLIED")

        # customer assigns
        self.client.force_authenticate(user=self.customer)
        scheduled_at = (timezone.now() + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        res = self.client.post(
            reverse("ad-assign", kwargs={"pk": ad_id}),
            {"contractor_id": self.contractor.id, "scheduled_at": scheduled_at, "location": "Tehran"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["status"], "ASSIGNED")
        self.assertEqual(res.data["assigned_contractor"], self.contractor.id)

        # contractor marks done
        self.client.force_authenticate(user=self.contractor)
        res = self.client.post(reverse("ad-report-done", kwargs={"pk": ad_id}), {}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(res.data["work_reported_done_at"])

        # contractor cannot confirm completion (must be customer)
        res = self.client.post(reverse("ad-confirm-completion", kwargs={"pk": ad_id}), {}, format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

        # customer confirms completion
        self.client.force_authenticate(user=self.customer)
        res = self.client.post(reverse("ad-confirm-completion", kwargs={"pk": ad_id}), {}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["status"], "DONE")

        # customer can review after DONE
        res = self.client.post(reverse("ad-review", kwargs={"pk": ad_id}), {"rating": 5, "comment": "Great"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["rating"], 5)

    def test_canceled_ad_visibility(self):
        ad_id = self._create_ad_as_customer()

        # cancel as owner
        self.client.force_authenticate(user=self.customer)
        res = self.client.post(reverse("ad-cancel", kwargs={"pk": ad_id}), {}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["status"], "CANCELED")

        # contractor should NOT see it (404 is ideal; some implementations use 403)
        self.client.force_authenticate(user=self.contractor)
        res = self.client.get(reverse("ad-detail", kwargs={"pk": ad_id}))
        self.assertIn(res.status_code, (status.HTTP_404_NOT_FOUND, status.HTTP_403_FORBIDDEN))

        # support SHOULD see it
        self.client.force_authenticate(user=self.support)
        res = self.client.get(reverse("ad-detail", kwargs={"pk": ad_id}))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["status"], "CANCELED")
