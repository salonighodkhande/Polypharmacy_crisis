
import re
import xml.etree.ElementTree as ET

import requests

from .evidence_matcher import find_relevant_evidence


DAILYMED_SPL_URL = (
    "https://dailymed.nlm.nih.gov/"
    "dailymed/services/v2/spls.json"
)

DAILYMED_LABEL_URL = (
    "https://dailymed.nlm.nih.gov/"
    "dailymed/services/v2/spls"
)

REQUEST_TIMEOUT = 15


def normalize_text(text):
    if not text:
        return ""

    text = text.lower()
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def clean_evidence_text(text):
    if not text:
        return ""

    text = re.sub(r"\s+", " ", text).strip()

    patterns = [
        (r"of\s*prothrombin", "of prothrombin"),
        (r"oral\s*anticoagulants", "oral anticoagulants"),
        (r"anticoagulants\s*may", "anticoagulants may"),
        (r"desired\s*level", "desired level"),
        (r"prothrombin\s*time", "prothrombin time"),
    ]

    for pattern, replacement in patterns:
        text = re.sub(
            pattern,
            replacement,
            text,
            flags=re.IGNORECASE
        )

    text = re.sub(r"\s+([,.!?;:])", r"\1", text)
    text = re.sub(r"\s+", " ", text).strip()

    return text


def get_base_drug_name(drug_name):
    if not drug_name:
        return ""

    drug_name = drug_name.strip()

    drug_name = re.sub(
        r"\s+\d+(?:\.\d+)?\s*"
        r"(?:mg|mcg|g|ml|units?|%)"
        r"(?:\s*/\s*\d+(?:\.\d+)?\s*"
        r"(?:mg|mcg|g|ml|units?|%))?"
        r"\s*$",
        "",
        drug_name,
        flags=re.IGNORECASE
    )

    return drug_name.strip()


def get_daily_med_labels(drug_name):
    params = {
        "drug_name": drug_name,
        "name_type": "generic",
        "pagesize": 5,
        "page": 1
    }

    try:
        response = requests.get(
            DAILYMED_SPL_URL,
            params=params,
            timeout=REQUEST_TIMEOUT
        )

        response.raise_for_status()
        data = response.json()

    except (requests.RequestException, ValueError):
        return []

    return data.get("data", [])


def is_matching_label(title, medicine_name):
    title = normalize_text(title)
    medicine_name = normalize_text(medicine_name)

    if not medicine_name or medicine_name not in title:
        return False

    extra_ingredients = [
        "clavulanate",
        "potassium clavulanate",
        "sulbactam",
        "tazobactam",
    ]

    for ingredient in extra_ingredients:
        if (
            ingredient in title
            and ingredient not in medicine_name
        ):
            return False

    return True


def get_label_xml(set_id):
    url = f"{DAILYMED_LABEL_URL}/{set_id}.xml"

    try:
        response = requests.get(
            url,
            timeout=REQUEST_TIMEOUT
        )

        response.raise_for_status()
        return response.text

    except requests.RequestException:
        return None


def extract_drug_interactions_section(xml_text):
    if not xml_text:
        return None

    try:
        root = ET.fromstring(xml_text)

    except ET.ParseError:
        return None

    for element in root.iter():
        tag_name = element.tag.split("}")[-1]

        if tag_name != "section":
            continue

        title = None

        for child in element:
            child_name = child.tag.split("}")[-1]

            if child_name == "title":
                title = normalize_text(
                    "".join(child.itertext())
                )
                break

        if not title:
            continue

        if (
            "drug interactions" in title
            or "drug interaction" in title
        ):
            text_parts = []

            for part in element.itertext():
                part = part.strip()

                if part:
                    text_parts.append(part)

            interaction_text = " ".join(text_parts)

            return clean_evidence_text(interaction_text)

    return None


def extract_relevant_evidence(
    interaction_text,
    matched_term
):
    if not interaction_text or not matched_term:
        return None

    matched_term = normalize_text(matched_term)
    clean_text = clean_evidence_text(interaction_text)

    # Remove section references such as (7.1), (7.2), etc.
    clean_text = re.sub(
        r"\(\s*\d+(?:\.\d+)?\s*\)",
        "",
        clean_text
    )

    clean_text = clean_evidence_text(clean_text)

    # First, search for a sentence containing the matched term.
    sentences = re.split(
        r"(?<=[.!?])\s+",
        clean_text
    )

    for sentence in sentences:
        normalized_sentence = normalize_text(sentence)

        if matched_term not in normalized_sentence:
            continue

        sentence = clean_evidence_text(sentence)

        # Remove leading subsection numbers.
        sentence = re.sub(
            r"^\d+(?:\.\d+)?\s+",
            "",
            sentence
        )

        sentence = clean_evidence_text(sentence)

        if sentence:
            return sentence

    # Fallback: extract a short passage around the matched term.
    normalized_text = normalize_text(clean_text)

    matched_position = normalized_text.find(matched_term)

    if matched_position == -1:
        return None

    start = max(0, matched_position - 180)

    end = min(
        len(clean_text),
        matched_position + len(matched_term) + 220
    )

    evidence = clean_text[start:end]

    # Move to the beginning of a sentence if possible.
    sentence_start = evidence.rfind(
        ". ",
        0,
        min(
            len(evidence),
            matched_position - start
        )
    )

    if sentence_start != -1:
        evidence = evidence[sentence_start + 2:]

    # Stop at the first complete sentence after the matched term.
    sentence_end = re.search(
        r"[.!?](?:\s|$)",
        evidence
    )

    if sentence_end:
        evidence = evidence[:sentence_end.end()]

    evidence = clean_evidence_text(evidence)

    return evidence if evidence else None


def find_interaction_evidence(
    medicine_a,
    medicine_b
):
    medicine_a_name = (
        medicine_a.rxnorm_name
        or medicine_a.verified_name
        or medicine_a.medicine_text
    )

    medicine_b_name = (
        medicine_b.rxnorm_name
        or medicine_b.verified_name
        or medicine_b.medicine_text
    )

    if not medicine_a_name:
        return {
            "status": "needs_review",
            "reason": "Medicine A has no usable name."
        }

    if not medicine_b_name:
        return {
            "status": "needs_review",
            "reason": "Medicine B has no usable name."
        }

    base_medicine_a_name = get_base_drug_name(
        medicine_a_name
    )

    labels = get_daily_med_labels(
        base_medicine_a_name
    )

    if not labels:
        return {
            "status": "needs_review",
            "medicine_a": medicine_a_name,
            "medicine_b": medicine_b_name,
            "reason": (
                "No DailyMed labels were found "
                "for Medicine A."
            )
        }

    evidence = []

    for label in labels:
        if not is_matching_label(
            label.get("title", ""),
            base_medicine_a_name
        ):
            continue

        set_id = label.get("setid")

        if not set_id:
            continue

        xml_text = get_label_xml(set_id)

        if not xml_text:
            continue

        interaction_text = extract_drug_interactions_section(
            xml_text
        )

        if not interaction_text:
            continue

        match = find_relevant_evidence(
            interaction_text,
            medicine_b_name
        )

        if not match["matched"]:
            continue

        relevant_evidence = extract_relevant_evidence(
            interaction_text,
            match["matched_term"]
        )

        # Safety check: never save the entire section as fallback evidence.
        if not relevant_evidence:
            continue

        evidence.append({
            "set_id": set_id,
            "title": label.get("title"),
            "published_date": label.get("published_date"),
            "interaction_section": relevant_evidence,
            "match_type": match["match_type"],
            "matched_term": match["matched_term"],
            "source": "DailyMed",
            "source_url": (
                f"{DAILYMED_LABEL_URL}/{set_id}.xml"
            )
        })

    if not evidence:
        return {
            "status": "no_relevant_evidence",
            "medicine_a": medicine_a_name,
            "medicine_b": medicine_b_name,
            "reason": (
                "No relevant interaction evidence "
                "was found for this medicine pair."
            )
        }

    return {
        "status": "interaction_evidence_found",
        "medicine_a": medicine_a_name,
        "medicine_b": medicine_b_name,
        "evidence": evidence
    }
