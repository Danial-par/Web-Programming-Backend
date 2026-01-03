from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()


class TicketRulesTests(APITestCase):
    def setUp(self):
        self.customer = User.objects.create_user(
            username="customerT",
            email="customerT@example.com",
            phone="09000000200",
            password="CustomerPass123",
            role="CUSTOMER",
        )
        self.customer2 = User.objects.create_user(
            username="customerT2",
            email="customerT2@example.com",
            phone="09000000201",
            password="CustomerPass123",
            role="CUSTOMER",
        )
        self.support = User.objects.create_user(
            username="supportT",
            email="supportT@example.com",
            phone="09000000202",
            password="SupportPass123",
            role="SUPPORT",
        )

    def test_ticket_owner_can_edit_but_cannot_respond(self):
        # create ticket as customer
        self.client.force_authenticate(user=self.customer)
        res = self.client.post(reverse("ticket-list"), {"title": "Help", "message": "Need support"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        ticket_id = res.data["id"]

        # owner can edit
        res = self.client.patch(reverse("ticket-detail", kwargs={"pk": ticket_id}), {"message": "Updated"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # owner cannot respond
        res = self.client.post(reverse("ticket-respond", kwargs={"pk": ticket_id}), {"support_response": "No"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_support_can_respond_and_other_user_cannot_access(self):
        # create ticket as customer
        self.client.force_authenticate(user=self.customer)
        res = self.client.post(reverse("ticket-list"), {"title": "Help", "message": "Need support"}, format="json")
        ticket_id = res.data["id"]

        # another customer cannot retrieve (should be 404/403 depending on queryset)
        self.client.force_authenticate(user=self.customer2)
        res = self.client.get(reverse("ticket-detail", kwargs={"pk": ticket_id}))
        self.assertIn(res.status_code, (status.HTTP_404_NOT_FOUND, status.HTTP_403_FORBIDDEN))

        # support can respond
        self.client.force_authenticate(user=self.support)
        res = self.client.post(
            reverse("ticket-respond", kwargs={"pk": ticket_id}),
            {"support_response": "We are investigating.", "status": "IN_PROGRESS"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["status"], "IN_PROGRESS")
        self.assertEqual(res.data["support_response"], "We are investigating.")
