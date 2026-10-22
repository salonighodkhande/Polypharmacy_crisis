from itertools import combinations

from .models import PrescriptionMedicine


def get_normalized_medicines(prescription_id):
    return PrescriptionMedicine.objects.filter(
        prescription_id=prescription_id,
        verified=True,
        normalization_status="normalized"
    ).exclude(
        rxnorm_rxcui__isnull=True
    ).exclude(
        rxnorm_rxcui=""
    )


def generate_medicine_pairs(prescription_id):
    medicines = list(
        get_normalized_medicines(prescription_id)
    )

    pairs = combinations(medicines, 2)

    return [
        {
            "medicine_a": medicine_a,
            "medicine_b": medicine_b,
            "rxcui_a": medicine_a.rxnorm_rxcui,
            "rxcui_b": medicine_b.rxnorm_rxcui
        }
        for medicine_a, medicine_b in pairs
    ]