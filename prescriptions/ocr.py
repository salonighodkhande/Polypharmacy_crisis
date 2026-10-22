
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter, ImageOps


def preprocess_image(image):
    image = ImageOps.exif_transpose(image)
    image = image.convert("RGB")

    image = ImageOps.grayscale(image)

    width, height = image.size

    if width < 1600:
        scale = 1600 / width
        image = image.resize(
            (1600, int(height * scale)),
            Image.Resampling.LANCZOS
        )

    image = ImageEnhance.Contrast(image).enhance(1.8)
    image = image.filter(ImageFilter.SHARPEN)

    image = image.point(
        lambda pixel: 255 if pixel > 170 else 0
    )

    return image


def extract_text_from_image(image_path):
    try:
        with Image.open(image_path) as original:
            image = preprocess_image(original)

        text = pytesseract.image_to_string(
            image,
            config="--oem 3 --psm 6"
        )

        return text.strip()

    except (OSError, ValueError) as error:
        raise ValueError(
            f"Could not process prescription image: {error}"
        ) from error
