from django.urls import path

from .views import (
    PrescriptionUploadView,
    PrescriptionMedicineVerificationView,
    PrescriptionMedicineNormalizationView,
    PrescriptionInteractionCheckView,
    PrescriptionReportView,
    PrescriptionRiskAnalysisView
)


urlpatterns = [
    path(
        "upload/",
        PrescriptionUploadView.as_view(),
        name="prescription-upload"
    ),

    path(
        "medicines/<int:pk>/verify/",
        PrescriptionMedicineVerificationView.as_view(),
        name="medicine-verification"
    ),

    path(
        "medicines/<int:pk>/normalize/",
        PrescriptionMedicineNormalizationView.as_view(),
        name="medicine-normalization"
    ),

    path(
        "<int:prescription_id>/check-interactions/",
        PrescriptionInteractionCheckView.as_view(),
        name="prescription-interaction-check"
    ),

    path(
        "<int:prescription_id>/risk-analysis/",
        PrescriptionRiskAnalysisView.as_view(),
        name="prescription-risk-analysis"
    ),

    path(
        "<int:prescription_id>/report/",
        PrescriptionReportView.as_view(),
        name="prescription-report"
    ),
]

