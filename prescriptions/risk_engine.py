
import re

from .models import PrescriptionMedicine


ALLERGY_CLASS_MAPPINGS = {
    "penicillin": [
        "amoxicillin",
        "ampicillin",
        "penicillin"
    ]
}


def normalize_text(text):

    if not text:
        return ""

    text = text.lower()

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


def split_patient_list(text):

    if not text:
        return []

    items = re.split(
        r"[,;\n]",
        text
    )

    return [
        normalize_text(item)
        for item in items
        if normalize_text(item)
    ]


def check_allergy_risks(
    medicines,
    allergies
):

    findings = []

    allergy_list = split_patient_list(
        allergies
    )

    for medicine in medicines:

        medicine_name = normalize_text(
            medicine.verified_name
            or medicine.rxnorm_name
            or medicine.medicine_text
        )

        for allergy in allergy_list:

            # Direct allergy match
            if allergy in medicine_name:

                findings.append({
                    "type": "allergy",
                    "severity": "high",
                    "medicine": (
                        medicine.verified_name
                        or medicine.rxnorm_name
                        or medicine.medicine_text
                    ),
                    "message": (
                        f"Medicine may match "
                        f"patient allergy: {allergy}."
                    ),
                    "source": (
                        "Patient-provided allergy information"
                    )
                })

                continue

            # Controlled allergy-class mapping
            related_medicines = (
                ALLERGY_CLASS_MAPPINGS.get(
                    allergy,
                    []
                )
            )

            for related_medicine in related_medicines:

                if related_medicine in medicine_name:

                    findings.append({
                        "type": "allergy",
                        "severity": "high",
                        "medicine": (
                            medicine.verified_name
                            or medicine.rxnorm_name
                            or medicine.medicine_text
                        ),
                        "message": (
                            f"Medicine may belong to the "
                            f"{allergy} allergy group."
                        ),
                        "source": (
                            "Patient-provided allergy information "
                            "+ controlled medication class mapping"
                        )
                    })

                    break

    return findings


def check_duplicate_medicines(
    medicines
):

    findings = []

    seen = {}

    for medicine in medicines:

        medicine_name = normalize_text(
            medicine.rxnorm_name
            or medicine.verified_name
            or medicine.medicine_text
        )

        if not medicine_name:
            continue

        if medicine_name in seen:

            findings.append({
                "type": "duplicate",
                "severity": "needs_clinical_review",
                "medicine": medicine_name,
                "message": (
                    f"Duplicate medication detected: "
                    f"{medicine_name}."
                ),
                "source": "Medication reconciliation"
            })

        else:

            seen[medicine_name] = medicine.id

    return findings


def check_condition_risks(
    medicines,
    conditions
):

    findings = []

    condition_list = split_patient_list(
        conditions
    )

    for medicine in medicines:

        medicine_name = normalize_text(
            medicine.verified_name
            or medicine.rxnorm_name
            or medicine.medicine_text
        )

        for condition in condition_list:

            if (
                condition == "diabetes"
                and "metformin" in medicine_name
            ):
                continue

    return findings


def generate_risk_findings(
    prescription
):

    medicines = list(
        PrescriptionMedicine.objects.filter(
            prescription=prescription,
            verified=True,
            normalization_status="normalized"
        )
    )

    patient = prescription.patient

    if not patient:

        return {
            "status": "patient_context_missing",
            "findings": []
        }

    findings = []

    findings.extend(
        check_allergy_risks(
            medicines,
            patient.allergies
        )
    )

    findings.extend(
        check_duplicate_medicines(
            medicines
        )
    )

    findings.extend(
        check_condition_risks(
            medicines,
            patient.conditions
        )
    )

    for interaction in prescription.interactions.all():

        findings.append({
            "type": "drug_interaction",
            "severity": interaction.severity,
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
            "message": interaction.description,
            "source": interaction.source
        })

    return {
        "status": "analysis_complete",
        "findings": findings
    }
