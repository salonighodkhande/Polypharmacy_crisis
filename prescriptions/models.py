from django.db import models


class Patient(models.Model):
    age = models.PositiveIntegerField()

    allergies = models.TextField(
        blank=True,
        default=""
    )

    conditions = models.TextField(
        blank=True,
        default=""
    )

    current_medications = models.TextField(
        blank=True,
        default=""
    )

    def __str__(self):
        return f"Patient {self.id}"


class Prescription(models.Model):
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="prescriptions",
        null=True,
        blank=True
    )

    image = models.ImageField(
        upload_to="prescriptions/"
    )

    uploaded_at = models.DateTimeField(
        auto_now_add=True
    )

    status = models.CharField(
        max_length=30,
        default="uploaded"
    )

    def __str__(self):
        return f"Prescription {self.id}"


class PrescriptionMedicine(models.Model):
    prescription = models.ForeignKey(
        Prescription,
        on_delete=models.CASCADE,
        related_name="medicines"
    )

    raw_text = models.TextField()

    medicine_text = models.CharField(
        max_length=255
    )

    duration = models.CharField(
        max_length=100,
        null=True,
        blank=True
    )

    confidence = models.FloatField(
        default=0.0
    )

    verified = models.BooleanField(
        default=False
    )

    verified_name = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )

    rxnorm_name = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )

    rxnorm_rxcui = models.CharField(
        max_length=50,
        null=True,
        blank=True
    )

    normalization_status = models.CharField(
        max_length=30,
        default="pending"
    )

    def __str__(self):
        return self.medicine_text


class DrugInteraction(models.Model):
    prescription = models.ForeignKey(
        Prescription,
        on_delete=models.CASCADE,
        related_name="interactions"
    )

    medicine_a = models.ForeignKey(
        PrescriptionMedicine,
        on_delete=models.CASCADE,
        related_name="interactions_as_medicine_a"
    )

    medicine_b = models.ForeignKey(
        PrescriptionMedicine,
        on_delete=models.CASCADE,
        related_name="interactions_as_medicine_b"
    )

    severity = models.CharField(
        max_length=30
    )

    description = models.TextField()

    source = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return (
            f"{self.medicine_a} + "
            f"{self.medicine_b}"
        )

