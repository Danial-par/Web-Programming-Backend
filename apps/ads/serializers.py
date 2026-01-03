from rest_framework import serializers
from .models import Ad, AdRequest


class AdSerializer(serializers.ModelSerializer):
    creator = serializers.PrimaryKeyRelatedField(read_only=True)
    assigned_contractor = serializers.PrimaryKeyRelatedField(read_only=True)

    status = serializers.CharField(read_only=True)
    scheduled_at = serializers.DateTimeField(read_only=True)
    location = serializers.CharField(read_only=True)

    work_reported_done_at = serializers.DateTimeField(read_only=True)
    completed_at = serializers.DateTimeField(read_only=True)
    canceled_at = serializers.DateTimeField(read_only=True)

    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = Ad
        fields = (
            "id",
            "title",
            "description",
            "category",
            "status",
            "creator",
            "assigned_contractor",
            "scheduled_at",
            "location",
            "work_reported_done_at",
            "completed_at",
            "canceled_at",
            "created_at",
            "updated_at",
        )

    def validate(self, attrs):
        # Prevent direct edits of workflow fields via PATCH/PUT:
        if self.instance:
            forbidden = {
                "status",
                "creator",
                "assigned_contractor",
                "scheduled_at",
                "location",
                "work_reported_done_at",
                "completed_at",
                "canceled_at",
            }
            if any(k in attrs for k in forbidden):
                raise serializers.ValidationError(
                    "Workflow fields are read-only. Use lifecycle action endpoints."
                )
        return attrs


class AdApplySerializer(serializers.Serializer):
    note = serializers.CharField(required=False, allow_blank=True)


class AdRequestSerializer(serializers.ModelSerializer):
    contractor = serializers.PrimaryKeyRelatedField(read_only=True)
    status = serializers.CharField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = AdRequest
        fields = ("id", "ad", "contractor", "status", "note", "created_at", "updated_at")


class AdAssignSerializer(serializers.Serializer):
    contractor_id = serializers.IntegerField()
    scheduled_at = serializers.DateTimeField()
    location = serializers.CharField(max_length=255)


class AdReviewCreateSerializer(serializers.Serializer):
    rating = serializers.IntegerField(min_value=1, max_value=5)
    comment = serializers.CharField(required=False, allow_blank=True)


class AdSummarySerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for profile endpoints (avoid huge nested payloads).
    """
    class Meta:
        model = Ad
        fields = (
            "id",
            "title",
            "category",
            "status",
            "created_at",
            "scheduled_at",
            "location",
            "assigned_contractor",
            "completed_at",
        )
        read_only_fields = fields
