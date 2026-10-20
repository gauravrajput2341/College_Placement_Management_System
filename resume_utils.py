"""Helper to read text out of a resume PDF (used for AI/ML matching)."""
from pypdf import PdfReader


def extract_text(pdf_path, max_chars=20000):
    """Return the text of a PDF as one clean string.
    Returns "" if the PDF has no readable text (for example a scanned image)."""
    try:
        reader = PdfReader(pdf_path)
        parts = []
        for page in reader.pages[:10]:          # resumes are short, 10 pages is plenty
            parts.append(page.extract_text() or "")
        text = " ".join(parts)
    except Exception:
        return ""
    text = " ".join(text.split())               # remove extra spaces and new lines
    return text[:max_chars]


# Run this file directly to test it:  python resume_utils.py path/to/resume.pdf
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python resume_utils.py path/to/resume.pdf")
    else:
        result = extract_text(sys.argv[1])
        print(f"Characters found: {len(result)}")
        print(result[:1000])