import re

import requests


RXNORM_APPROXIMATE_URL = (
    "https://rxnav.nlm.nih.gov/REST/approximateTerm.json"
)

RXNORM_PROPERTIES_URL = (
    "https://rxnav.nlm.nih.gov/REST/rxcui"
)

REQUEST_TIMEOUT = 15


def normalize_text(text):
    if not text:
        return ""

    return " ".join(text.lower().split())


def normalize_ingredient_text(text):
    text = normalize_text(text)

    replacements = {
        "clavulanic acid": "clavulanate",
        "potassium clavulanate": "clavulanate",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    return text


def extract_strengths(text):
    text = normalize_ingredient_text(text)

    matches = re.findall(
        r"\b\d+(?:\.\d+)?\s*(?:mg|mcg|g|ml)\b",
        text,
    )

    return {
        match.replace(" ", "")
        for match in matches
    }


def extract_ingredients(text):
    text = normalize_ingredient_text(text)

    # Remove strengths before extracting ingredient names.
    text = re.sub(
        r"\b\d+(?:\.\d+)?\s*(?:mg|mcg|g|ml)\b",
        " ",
        text,
        flags=re.IGNORECASE,
    )

    # Remove common dosage forms and units.
    text = re.sub(
        r"\b(oral|tablet|tablets|capsule|capsules|"
        r"syrup|solution|suspension|injection|"
        r"ip|usp|sr|er|dr)\b",
        " ",
        text,
        flags=re.IGNORECASE,
    )

    # Remove punctuation and normalize whitespace.
    text = re.sub(r"[^a-z0-9]+", " ", text)
    text = " ".join(text.split())

    # Remove known brand names and salt-form words.
    ignored_terms = {
        "diclegis",
        "succinate",
        "hydrochloride",
        "chloride",
        "sodium",
        "potassium",
        "calcium",
        "phosphate",
    }

    return {
        word
        for word in text.split()
        if len(word) > 2 and word not in ignored_terms
    }


def get_rxnorm_candidates(medicine_name):
    params = {
        "term": medicine_name,
        "maxEntries": 5,
        "option": 1,
    }

    try:
        response = requests.get(
            RXNORM_APPROXIMATE_URL,
            params=params,
            timeout=REQUEST_TIMEOUT,
        )

        response.raise_for_status()

        data = response.json()

    except (requests.RequestException, ValueError):
        return []

    candidates = (
        data
        .get("approximateGroup", {})
        .get("candidate", [])
    )

    return candidates


def get_rxnorm_properties(rxcui):
    url = (
        f"{RXNORM_PROPERTIES_URL}/"
        f"{rxcui}/properties.json"
    )

    try:
        response = requests.get(
            url,
            timeout=REQUEST_TIMEOUT,
        )

        response.raise_for_status()

        data = response.json()

    except (requests.RequestException, ValueError):
        return None

    return data.get("properties")


def calculate_match_score(
    medicine_name,
    candidate_name,
    candidate_score,
):
    medicine = normalize_ingredient_text(
        medicine_name
    )

    candidate = normalize_ingredient_text(
        candidate_name
    )

    if not medicine or not candidate:
        return 0

    score = 0

    # Exact normalized text match.
    if medicine == candidate:
        score += 50

    medicine_ingredients = extract_ingredients(
        medicine
    )

    candidate_ingredients = extract_ingredients(
        candidate
    )

    medicine_strengths = extract_strengths(
        medicine
    )

    candidate_strengths = extract_strengths(
        candidate
    )

    # Ingredient matching.
    if medicine_ingredients:
        common_ingredients = (
            medicine_ingredients
            & candidate_ingredients
        )

        ingredient_ratio = (
            len(common_ingredients)
            / len(medicine_ingredients)
        )

        if ingredient_ratio == 1:
            score += 40
        elif ingredient_ratio >= 0.5:
            score += 20

    # Strength matching.
    if medicine_strengths:
        common_strengths = (
            medicine_strengths
            & candidate_strengths
        )

        strength_ratio = (
            len(common_strengths)
            / len(medicine_strengths)
        )

        if strength_ratio == 1:
            score += 30
        elif strength_ratio >= 0.5:
            score += 15

    # RxNorm approximateTerm scores are NOT
    # percentages. Use them only as a small
    # supporting signal.
    try:
        rxnorm_score = float(
            candidate_score or 0
        )
    except (TypeError, ValueError):
        rxnorm_score = 0

    if rxnorm_score >= 15:
        score += 5

    return score


def find_best_rxnorm_match(medicine_name):
    candidates = get_rxnorm_candidates(
        medicine_name
    )

    if not candidates:
        return None

    # Keep only the best candidate for each RxCUI.
    unique_candidates = {}

    for candidate in candidates:
        rxcui = candidate.get("rxcui")

        if not rxcui:
            continue

        candidate_score = candidate.get(
            "score"
        )

        try:
            candidate_score_value = float(
                candidate_score or 0
            )
        except (TypeError, ValueError):
            candidate_score_value = 0

        existing = unique_candidates.get(rxcui)

        if existing is None:
            unique_candidates[rxcui] = candidate
        else:
            try:
                existing_score = float(
                    existing.get("score") or 0
                )
            except (TypeError, ValueError):
                existing_score = 0

            if candidate_score_value > existing_score:
                unique_candidates[rxcui] = candidate

    best_candidate = None
    best_score = -1

    for candidate in unique_candidates.values():
        rxcui = candidate.get("rxcui")
        candidate_name = candidate.get("name")
        candidate_score = candidate.get("score")

        if not rxcui:
            continue

        if not candidate_name:
            try:
                response = requests.get(
                    (
                        "https://rxnav.nlm.nih.gov/REST/"
                        f"rxcui/{rxcui}/properties.json"
                    ),
                    timeout=REQUEST_TIMEOUT,
                )

                response.raise_for_status()

                properties = (
                    response.json()
                    .get("properties", {})
                )

                candidate_name = properties.get("name")

            except (requests.RequestException, ValueError):
                continue

        if not candidate_name:
            continue

        match_score = calculate_match_score(
            medicine_name,
            candidate_name,
            candidate_score,
        )

        medicine_ingredients = extract_ingredients(medicine_name)
        candidate_ingredients = extract_ingredients(candidate_name)

        if not medicine_ingredients.issubset(candidate_ingredients):
            continue

        if match_score > best_score:
            best_score = match_score

            best_candidate = {
                "rxcui": rxcui,
                "name": candidate_name,
                "match_score": match_score,
                "rxnorm_score": candidate_score,
            }

    if not best_candidate:
        return None

    # Safety threshold.
    #
    # A candidate must have sufficient
    # ingredient/strength similarity before
    # it can be automatically normalized.
    if best_candidate["match_score"] < 70:
        return {
            "status": "needs_review",
            "name": best_candidate["name"],
            "rxcui": best_candidate["rxcui"],
            "match_score": best_candidate[
                "match_score"
            ],
            "rxnorm_score": best_candidate[
                "rxnorm_score"
            ],
        }

    return {
        "status": "normalized",
        "name": best_candidate["name"],
        "rxcui": best_candidate["rxcui"],
        "match_score": best_candidate[
            "match_score"
        ],
        "rxnorm_score": best_candidate[
            "rxnorm_score"
        ],
    }


def normalize_prescription_medicine(
    medicine
):
    if not medicine.verified:
        return {
            "status": "needs_review",
            "reason": (
                "Medicine must be verified "
                "before RxNorm normalization."
            ),
        }

    medicine_name = (
        medicine.verified_name
        or medicine.medicine_text
    )

    if not medicine_name:
        medicine.normalization_status = (
            "needs_review"
        )

        medicine.save(
            update_fields=[
                "normalization_status"
            ]
        )

        return {
            "status": "needs_review",
            "reason": (
                "Medicine has no usable name."
            ),
        }

    result = find_best_rxnorm_match(
        medicine_name
    )

    if not result:
        medicine.rxnorm_name = None
        medicine.rxnorm_rxcui = None
        medicine.normalization_status = (
            "needs_review"
        )

        medicine.save(
            update_fields=[
                "rxnorm_name",
                "rxnorm_rxcui",
                "normalization_status",
            ]
        )

        return {
            "status": "needs_review",
            "reason": (
                "No sufficiently reliable "
                "RxNorm match was found."
            ),
        }

    if result["status"] != "normalized":
        medicine.rxnorm_name = None
        medicine.rxnorm_rxcui = None
        medicine.normalization_status = (
            "needs_review"
        )

        medicine.save(
            update_fields=[
                "rxnorm_name",
                "rxnorm_rxcui",
                "normalization_status",
            ]
        )

        return result

    properties = get_rxnorm_properties(
        result["rxcui"]
    )

    if not properties:
        medicine.rxnorm_name = None
        medicine.rxnorm_rxcui = None
        medicine.normalization_status = (
            "needs_review"
        )

        medicine.save(
            update_fields=[
                "rxnorm_name",
                "rxnorm_rxcui",
                "normalization_status",
            ]
        )

        return {
            "status": "needs_review",
            "reason": (
                "RxNorm candidate could not "
                "be verified."
            ),
        }

    medicine.rxnorm_name = (
        properties.get("name")
        or result["name"]
    )

    medicine.rxnorm_rxcui = (
        properties.get("rxcui")
        or result["rxcui"]
    )

    medicine.normalization_status = (
        "normalized"
    )

    medicine.save(
        update_fields=[
            "rxnorm_name",
            "rxnorm_rxcui",
            "normalization_status",
        ]
    )

    return {
        "status": "normalized",
        "name": medicine.rxnorm_name,
        "rxcui": medicine.rxnorm_rxcui,
        "match_score": result[
            "match_score"
        ],
        "rxnorm_score": result[
            "rxnorm_score"
        ],
    }