
from rest_framework import serializers
from .models import Prescription, PrescriptionMedicine


class PrescriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Prescription
        fields = ["id", "image", "uploaded_at", "status"]
        read_only_fields = ["id", "uploaded_at", "status"]
        extra_kwargs = {
            "image": {"required": True}
        }


class PrescriptionMedicineSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrescriptionMedicine
        fields = [
            "id",
            "prescription",
            "raw_text",
            "medicine_text",
            "duration",
            "confidence",
            "verified",
            "verified_name",
            "rxnorm_name",
            "rxnorm_rxcui",
            "normalization_status",
        ]
        read_only_fields = [
            "id",
            "prescription",
            "raw_text",
            "confidence",
            "rxnorm_name",
            "rxnorm_rxcui",
            "normalization_status",
        ]

    def update(self, instance, validated_data):
        old_name = instance.verified_name or instance.medicine_text
        new_name = validated_data.get(
            "verified_name", instance.verified_name
        )
        new_verified = validated_data.get(
            "verified", instance.verified
        )

        name_changed = (
            new_name is not None
            and new_name.strip() != old_name.strip()
        )
        verification_changed = new_verified != instance.verified

        if name_changed or verification_changed:
            instance.rxnorm_name = None
            instance.rxnorm_rxcui = None
            instance.normalization_status = (
                "pending" if new_verified else "needs_review"
            )

        return super().update(instance, validated_data)


class PrescriptionReportSerializer(serializers.Serializer):
    prescription_id = serializers.IntegerField()
    status = serializers.CharField()
    image = serializers.CharField()
    patient = serializers.DictField(allow_null=True)
    medicines = serializers.ListField()
    interactions = serializers.ListField()
    summary = serializers.DictField()

