from rest_framework import serializers
from .models import Ticket


class TicketSerializer(serializers.ModelSerializer):
    created_by = serializers.PrimaryKeyRelatedField(read_only=True)
    responded_by = serializers.PrimaryKeyRelatedField(read_only=True)
    responded_at = serializers.DateTimeField(read_only=True)
    support_response = serializers.CharField(read_only=True)

    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = Ticket
        fields = (
            "id",
            "title",
            "message",
            "status",
            "ad",
            "created_by",
            "support_response",
            "responded_by",
            "responded_at",
            "created_at",
            "updated_at",
        )


class TicketRespondSerializer(serializers.Serializer):
    support_response = serializers.CharField()
    status = serializers.ChoiceField(choices=["OPEN", "IN_PROGRESS", "CLOSED"], required=False)
