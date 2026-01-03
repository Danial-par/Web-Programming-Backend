from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import Ad, AdRequest

User = get_user_model()


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
        # Only allow editing base fields through PATCH/PUT; status transitions use actions.
        if self.instance:
            forbidden = {"status", "assigned_contractor", "scheduled_at", "location",
                         "work_reported_done_at", "completed_at", "canceled_at", "creator"}
            if any(k in attrs for k in forbidden):
                raise serializers.ValidationError("Use the dedicated action endpoints for workflow fields.")
        return attrs


class AdRequestSerializer(serializers.ModelSerializer):
    contractor = serializers.PrimaryKeyRelatedField(read_only=True)
    status = serializers.CharField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = AdRequest
        fields = ("id", "ad", "contractor", "status", "note", "created_at")

    def validate_ad(self, ad: Ad):
        request = self.context["request"]
        user = request.user

        if getattr(user, "role", None) != "CONTRACTOR" and not user.is_superuser:
            raise serializers.ValidationError("Only contractors can apply.")

        if ad.status != "OPEN":
            raise serializers.ValidationError("You can only apply to OPEN ads.")

        if ad.creator_id == user.id:
            raise serializers.ValidationError("You cannot apply to your own ad.")

        return ad

    def create(self, validated_data):
        """
        Enforce 1 request per (ad, contractor). If it exists withdrawn, re-apply.
        """
        request = self.context["request"]
        contractor = request.user
        ad = validated_data["ad"]
        note = validated_data.get("note", "")

        obj, created = AdRequest.objects.get_or_create(
            ad=ad,
            contractor=contractor,
            defaults={"note": note, "status": "APPLIED"},
        )
        if not created:
            obj.status = "APPLIED"
            obj.note = note
            obj.save(update_fields=["status", "note", "updated_at"])
        return obj


class AdAssignSerializer(serializers.Serializer):
    contractor_id = serializers.IntegerField()
    scheduled_at = serializers.DateTimeField()
    location = serializers.CharField(max_length=255)
