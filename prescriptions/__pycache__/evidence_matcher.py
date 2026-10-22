import re


CLASS_MAPPINGS = {
    "oral anticoagulants": [
        "warfarin",
    ],
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


def find_relevant_evidence(
    interaction_text,
    medicine_b_name
):
    text = normalize_text(interaction_text)
    medicine_b_name = normalize_text(medicine_b_name)

    # Direct medicine-name match
    if medicine_b_name in text:
        return {
            "matched": True,
            "match_type": "medicine_name",
            "matched_term": medicine_b_name
        }

    # Class-based match
    for class_name, medicines in CLASS_MAPPINGS.items():

        if class_name not in text:
            continue

        for medicine in medicines:

            if medicine == medicine_b_name:
                return {
                    "matched": True,
                    "match_type": "drug_class",
                    "matched_term": class_name
                }

    return {
        "matched": False,
        "match_type": None,
        "matched_term": None
    }