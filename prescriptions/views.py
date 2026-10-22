from rest_framework import status
from rest_framework.generics import (
    GenericAPIView,
    RetrieveUpdateAPIView
)
from rest_framework.mixins import CreateModelMixin
from rest_framework.parsers import (
    MultiPartParser,
    FormParser
)
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    Prescription,
    PrescriptionMedicine
)

from .serializers import (
    PrescriptionSerializer,
    PrescriptionMedicineSerializer,
    PrescriptionReportSerializer
)

from .ocr import extract_text_from_image
from .medicine_extractor import extract_medicines

from .rxnorm import (
    normalize_prescription_medicine
)

from .interaction_engine import (
    generate_medicine_pairs
)

from .interaction_service import (
    check_and_save_interaction
)

from .risk_engine import (
    generate_risk_findings
)


class PrescriptionUploadView(
    CreateModelMixin,
    GenericAPIView
):

    serializer_class = PrescriptionSerializer

    parser_classes = [
        MultiPartParser,
        FormParser
    ]

    def get(self, request):

        return Response({
            "message": (
                "Prescription upload API is working."
            )
        })

    def post(self, request):

        serializer = self.get_serializer(
            data=request.data
        )

        if not serializer.is_valid():

            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        prescription = serializer.save()

        image_path = prescription.image.path

        ocr_text = extract_text_from_image(
            image_path
        )

        medicines = extract_medicines(
            ocr_text
        )

        created_medicines = []

        for medicine in medicines:

            created_medicine = (
                PrescriptionMedicine.objects.create(
                    prescription=prescription,
                    raw_text=medicine["raw_text"],
                    medicine_text=medicine["medicine_text"],
                    duration=medicine["duration"],
                    confidence=medicine["confidence"]
                )
            )

            created_medicines.append({
                "id": created_medicine.id,
                "raw_text": created_medicine.raw_text,
                "medicine_text": created_medicine.medicine_text,
                "duration": created_medicine.duration,
                "confidence": created_medicine.confidence,
                "verified": created_medicine.verified,
                "verified_name": created_medicine.verified_name,
            })

        prescription.status = "processed"

        prescription.save(
            update_fields=["status"]
        )

        return Response(
            {
                "id": prescription.id,
                "image": prescription.image.url,
                "status": prescription.status,
                "ocr_text": ocr_text,
                "medicines": created_medicines
            },
            status=status.HTTP_201_CREATED
        )


class PrescriptionMedicineVerificationView(
    RetrieveUpdateAPIView
):

    queryset = PrescriptionMedicine.objects.all()

    serializer_class = (
        PrescriptionMedicineSerializer
    )


class PrescriptionMedicineNormalizationView(
    APIView
):

    def post(
        self,
        request,
        pk
    ):

        try:

            medicine = PrescriptionMedicine.objects.get(
                id=pk
            )

        except PrescriptionMedicine.DoesNotExist:

            return Response(
                {
                    "detail": (
                        "Medicine not found."
                    )
                },
                status=status.HTTP_404_NOT_FOUND
            )

        result = normalize_prescription_medicine(
            medicine
        )

        if result["status"] == "needs_verification":

            return Response(
                result,
                status=status.HTTP_400_BAD_REQUEST
            )

        if result["status"] == "needs_review":

            return Response(
                result,
                status=status.HTTP_422_UNPROCESSABLE_ENTITY
            )

        return Response(
            result,
            status=status.HTTP_200_OK
        )


class PrescriptionInteractionCheckView(
    APIView
):

    def post(
        self,
        request,
        prescription_id
    ):

        pairs = generate_medicine_pairs(
            prescription_id
        )

        results = []

        for pair in pairs:

            result = check_and_save_interaction(
                pair["medicine_a"],
                pair["medicine_b"]
            )

            results.append(result)

        return Response({
            "prescription_id": prescription_id,
            "total_pairs_checked": len(pairs),
            "results": results
        })


class PrescriptionRiskAnalysisView(
    APIView
):

    def get(
        self,
        request,
        prescription_id
    ):

        try:

            prescription = Prescription.objects.get(
                id=prescription_id
            )

        except Prescription.DoesNotExist:

            return Response(
                {
                    "detail": (
                        "Prescription not found."
                    )
                },
                status=status.HTTP_404_NOT_FOUND
            )

        result = generate_risk_findings(
            prescription
        )

        return Response({
            "prescription_id": prescription.id,
            "status": result["status"],
            "findings": result["findings"],
            "total_findings": len(
                result["findings"]
            )
        })


class PrescriptionReportView(
    APIView
):

    def get(
        self,
        request,
        prescription_id
    ):

        try:

            prescription = Prescription.objects.get(
                id=prescription_id
            )

        except Prescription.DoesNotExist:

            return Response(
                {
                    "detail": (
                        "Prescription not found."
                    )
                },
                status=status.HTTP_404_NOT_FOUND
            )

        medicines = prescription.medicines.all()

        interactions = (
            prescription.interactions.all()
        )

        risk_result = generate_risk_findings(
            prescription
        )

        patient_data = None

        if prescription.patient:

            patient_data = {
                "id": prescription.patient.id,

                "age": prescription.patient.age,

                "allergies": (
                    prescription.patient.allergies
                ),

                "conditions": (
                    prescription.patient.conditions
                ),

                "current_medications": (
                    prescription.patient.current_medications
                )
            }

        medicine_data = []

        for medicine in medicines:

            medicine_data.append({
                "id": medicine.id,

                "raw_text": (
                    medicine.raw_text
                ),

                "medicine_text": (
                    medicine.medicine_text
                ),

                "duration": (
                    medicine.duration
                ),

                "confidence": (
                    medicine.confidence
                ),

                "verified": (
                    medicine.verified
                ),

                "verified_name": (
                    medicine.verified_name
                ),

                "rxnorm_name": (
                    medicine.rxnorm_name
                ),

                "rxnorm_rxcui": (
                    medicine.rxnorm_rxcui
                ),

                "normalization_status": (
                    medicine.normalization_status
                )
            })

        interaction_data = []

        for interaction in interactions:

            interaction_data.append({
                "id": interaction.id,

                "medicine_a": (
                    interaction.medicine_a.verified_name
                    or interaction.medicine_a.rxnorm_name
                    or interaction.medicine_a.medicine_text
                ),

                "medicine_b": (
                    interaction.medicine_b.verified_name
                    or interaction.medicine_b.rxnorm_name
                    or interaction.medicine_b.medicine_text
                ),

                "severity": (
                    interaction.severity
                ),

                "description": (
                    interaction.description
                ),

                "source": (
                    interaction.source
                ),

                "created_at": (
                    interaction.created_at
                )
            })

        summary = {
            "total_medicines": (
                medicines.count()
            ),

            "verified_medicines": (
                medicines.filter(
                    verified=True
                ).count()
            ),

            "normalized_medicines": (
                medicines.filter(
                    normalization_status="normalized"
                ).count()
            ),

            "interactions_found": (
                interactions.count()
            ),

            "risk_findings": (
                risk_result["findings"]
            ),

            "total_risk_findings": (
                len(
                    risk_result["findings"]
                )
            )
        }

        report = {
            "prescription_id": (
                prescription.id
            ),

            "status": (
                prescription.status
            ),

            "image": (
                prescription.image.url
            ),

            "patient": patient_data,

            "medicines": medicine_data,

            "interactions": interaction_data,

            "summary": summary
        }

        serializer = (
            PrescriptionReportSerializer(
                report
            )
        )

        return Response(
            serializer.data
        )
