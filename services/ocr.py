import easyocr

reader = easyocr.Reader(["en"])

def extract_text(image_path):
    result = reader.readtext(image_path)
    return "\n".join(
        [r[0] for r in result]
    )