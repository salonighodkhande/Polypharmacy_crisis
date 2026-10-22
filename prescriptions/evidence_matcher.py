
import re


def normalize_text(text):
    if not text:
        return ""

    text = text.lower()
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def find_relevant_evidence(
    interaction_text,
    medicine_name
):
    interaction_text_normalized = normalize_text(
        interaction_text
    )

    medicine_name_normalized = normalize_text(
        medicine_name
    )

    if not interaction_text_normalized or not medicine_name_normalized:
        return {
            "matched": False,
            "match_type": None,
            "matched_term": None
        }

    if medicine_name_normalized in interaction_text_normalized:
        return {
            "matched": True,
            "match_type": "exact_name",
            "matched_term": medicine_name
        }

    return {
        "matched": False,
        "match_type": None,
        "matched_term": None
    }
