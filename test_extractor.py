from prescriptions.medicine_extractor import extract_medicines


ocr_text = """
Smile Designing | Teeth Whitening
Dental Implants | General Dentistry

Tab. Prymentin 625

Ph: +91 8108112511
Web: www.thewhitetusk.com
"""


medicines = extract_medicines(ocr_text)

for medicine in medicines:
    print(medicine)