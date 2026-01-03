from rest_framework import serializers
from apps.ads.models import Ad
from .models import Review


class ReviewSerializer(serializers.ModelSerializer):
    author = serializers.PrimaryKeyRelatedField(read_only=True)
    contractor = serializers.PrimaryKeyRelatedField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = Review
        fields = ("id", "ad", "author", "contractor", "rating", "comment", "created_at")

    def validate_ad(self, ad: Ad):
        request = self.context["request"]
        user = request.user

        # Must be ad creator and ad must be DONE (customer confirmed)
        if ad.creator_id != user.id:
            raise serializers.ValidationError("You can only review your own ad.")
        if ad.status != "DONE":
            raise serializers.ValidationError("You can only review after the ad is DONE.")
        if not ad.assigned_contractor_id:
            raise serializers.ValidationError("Ad has no assigned contractor.")
        return ad

    def create(self, validated_data):
        request = self.context["request"]
        ad: Ad = validated_data["ad"]

        return Review.objects.create(
            ad=ad,
            author=request.user,
            contractor=ad.assigned_contractor,
            rating=validated_data["rating"],
            comment=validated_data.get("comment", ""),
        )
