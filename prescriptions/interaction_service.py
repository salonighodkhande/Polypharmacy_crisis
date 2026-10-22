
from prescriptions.models import DrugInteraction
from prescriptions.interaction_evidence import find_interaction_evidence


def check_and_save_interaction(medicine_a, medicine_b):
    result = find_interaction_evidence(
        medicine_a,
        medicine_b
    )

    if result["status"] != "interaction_evidence_found":
        return result

    evidence = result["evidence"][0]

    existing_interaction = DrugInteraction.objects.filter(
        prescription=medicine_a.prescription,
        medicine_a=medicine_a,
        medicine_b=medicine_b
    ).first()

    if existing_interaction:
        existing_interaction.severity = "needs_clinical_review"
        existing_interaction.description = evidence["interaction_section"]
        existing_interaction.source = (
            f"DailyMed | {evidence['title']}"
        )
        existing_interaction.save(
            update_fields=[
                "severity",
                "description",
                "source"
            ]
        )

        interaction = existing_interaction
        status = "interaction_updated"
    else:
        interaction = DrugInteraction.objects.create(
            prescription=medicine_a.prescription,
            medicine_a=medicine_a,
            medicine_b=medicine_b,
            severity="needs_clinical_review",
            description=evidence["interaction_section"],
            source=f"DailyMed | {evidence['title']}"
        )

        status = "interaction_saved"

    return {
        "status": status,
        "interaction_id": interaction.id,
        "medicine_a": result["medicine_a"],
        "medicine_b": result["medicine_b"],
        "severity": interaction.severity,
        "description": interaction.description,
        "source": interaction.source,
        "source_url": evidence["source_url"],
        "match_type": evidence["match_type"],
        "matched_term": evidence["matched_term"],
    }
