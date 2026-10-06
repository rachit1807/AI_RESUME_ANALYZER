import pdfplumber
from io import BytesIO

def extract_text(pdf_file):

    text = ""

    with pdfplumber.open(BytesIO(pdf_file) if isinstance(pdf_file, bytes) else pdf_file) as pdf:

        for page in pdf.pages:

            page_text = page.extract_text()

            if page_text:
                text += page_text + "\n"

    return text
