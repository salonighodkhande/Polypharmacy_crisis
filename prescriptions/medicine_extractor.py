
import re


MEDICINE_START_PATTERN = re.compile(
    r"^\s*(?:(\d+)\s*[).]\s*)?"
    r"(?:TAB(?:LET)?|CAP(?:SULE)?|SYP|SYR(?:UP)?|"
    r"SUSP(?:ENSION)?|INJ(?:ECTION)?|DROP|CREAM|"
    r"OINT(?:MENT)?)\s*\.?\s*(.*)$",
    re.IGNORECASE,
)

DURATION_PATTERN = re.compile(
    r"\b(\d+)\s*(days?|d)\b",
    re.IGNORECASE,
)

DOSAGE_PATTERN = re.compile(
    r"\b\d+\s+"
    r"(?:morning|afternoon|evening|night|"
    r"once|twice|thrice|daily|weekly)\b",
    re.IGNORECASE,
)

STRENGTH_PATTERN = re.compile(
    r"\b\d+(?:\.\d+)?\s*(?:mg|mcg|g|ml|kg)\b",
    re.IGNORECASE,
)


def clean_line(line):
    return re.sub(r"\s+", " ", line).strip()


def parse_medicine_line(line):
    match = MEDICINE_START_PATTERN.match(line)

    if not match:
        return None

    content = match.group(2).strip()

    # Remove total-count and food instructions from
    # the text used to identify the medicine name.
    content = re.sub(
        r"\([^)]*(?:tot|total|after food|before food)"
        r"[^)]*\)",
        " ",
        content,
        flags=re.IGNORECASE,
    )

    duration_match = DURATION_PATTERN.search(content)
    duration = None

    if duration_match:
        duration = duration_match.group(0).strip()
        content = (
            content[:duration_match.start()]
            + " "
            + content[duration_match.end():]
        )

    content = clean_line(content)

    dosage_match = DOSAGE_PATTERN.search(content)

    if dosage_match:
        content = content[:dosage_match.start()].strip()

    content = re.sub(r"[\s,;:-]+$", "", content).strip()

    return {
        "medicine_text": content,
        "duration": duration,
    }



def is_medicine_detail_line(line):
    if not line:
        return False

    line = clean_line(line)

    # Skip numbered medicine entries: they start a new record.
    if MEDICINE_START_PATTERN.match(line):
        return False

    # Keep instructions and total quantities for review.
    if re.search(
        r"\b(after food|before food|with food|"
        r"before meals|after meals|tot(?:al)?\s*:?)\b",
        line,
        re.IGNORECASE,
    ):
        return True

    # Keep lines that appear to contain medicine strengths.
    if STRENGTH_PATTERN.search(line):
        return True

    # Keep likely ingredient names, but avoid common
    # prescription headings and general advice.
    excluded_lines = {
        "advice",
        "diagnosis",
        "follow up",
        "medicine name dosage duration",
        "chief complaints clinical findings",
    }

    if line.rstrip(":").casefold() in excluded_lines:
        return False

    letters = re.sub(r"[^A-Za-z]", "", line)

    return (
        len(letters) >= 4
        and letters.isupper()
        and not line.startswith(("*", "-", "•"))
    )

def calculate_confidence(medicine_text, duration):
    # This is a simple extraction-quality heuristic,
    # NOT a calibrated OCR accuracy probability.
    score = 0.0

    if medicine_text:
        score += 0.5

    if re.search(r"[A-Za-z]{3,}", medicine_text):
        score += 0.3

    if duration:
        score += 0.2

    return round(score, 2)




def extract_medicines(ocr_text):
    medicines = []
    current_medicine = None

    for original_line in ocr_text.splitlines():
        line = clean_line(original_line)

        if not line:
            continue

        parsed = parse_medicine_line(line)

        if parsed and parsed["medicine_text"]:
            current_medicine = {
                "raw_text": line,
                "detail_text": "",
                "medicine_text": parsed["medicine_text"],
                "duration": parsed["duration"],
            }

            medicines.append(current_medicine)
            continue

        if (
            current_medicine is not None
            and is_medicine_detail_line(line)
        ):
            current_medicine["raw_text"] += "\n" + line

            if current_medicine["detail_text"]:
                current_medicine["detail_text"] += "\n" + line
            else:
                current_medicine["detail_text"] = line

    for medicine in medicines:
        medicine["confidence"] = calculate_confidence(
            medicine["medicine_text"],
            medicine["duration"],
        )

    return medicines
