def extract_text_from_image(image_path: str) -> str:
    """Extract text from an image using pytesseract (OCR)."""
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        return "OCR not available: install pytesseract and pillow."

    try:
        img = Image.open(image_path)
        text = pytesseract.image_to_string(img)
        return text.strip()
    except Exception as e:
        return f"OCR error: {e}"


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text from a PDF using PyPDF2."""
    try:
        import PyPDF2
    except ImportError:
        return "PDF extraction not available: install PyPDF2."

    try:
        text_parts = []
        with open(pdf_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                page_text = page.extract_text() or ""
                text_parts.append(page_text)
        return "\n".join(text_parts).strip()
    except Exception as e:
        return f"PDF extraction error: {e}"
