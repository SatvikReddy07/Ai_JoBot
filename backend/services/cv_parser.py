import re
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

def extract_text_from_file(file_path: Path, filename: str) -> str:
    """
    Extract raw text from PDF using PyMuPDF (fitz) or DOCX using python-docx.
    """
    ext = file_path.suffix.lower()
    text_content = ""

    if ext == ".pdf":
        import fitz  # PyMuPDF
        try:
            doc = fitz.open(str(file_path))
            pages_text = []
            for page in doc:
                pages_text.append(page.get_text())
            doc.close()
            text_content = "\n".join(pages_text)
        except Exception as exc:
            logger.error(f"Error parsing PDF file {filename}: {exc}")
            raise ValueError(f"Failed to extract text from PDF: {exc}")

    elif ext in [".docx", ".doc"]:
        import docx
        try:
            doc = docx.Document(str(file_path))
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            
            # Also extract text from any tables
            table_lines = []
            for table in doc.tables:
                for row in table.rows:
                    row_cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                    if row_cells:
                        table_lines.append(" | ".join(row_cells))
            
            text_content = "\n".join(paragraphs + table_lines)
        except Exception as exc:
            logger.error(f"Error parsing DOCX file {filename}: {exc}")
            raise ValueError(f"Failed to extract text from DOCX: {exc}")
    else:
        raise ValueError(f"Unsupported CV file extension: '{ext}'. Allowed: .pdf, .docx")

    cleaned = "\n".join([line.strip() for line in text_content.splitlines() if line.strip()])
    return cleaned

def parse_cv_content(raw_text: str, existing_profile: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Conservative local extraction. Uploads never replace confirmed profile facts.

    Employment, certifications and achievements require explicit user review; no
    default employers, credentials, dates or performance claims are inserted.
    """
    import copy
    if existing_profile is not None:
        return copy.deepcopy(existing_profile)
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    result = {
        "name": lines[0] if lines else "",
        "current_role": lines[1] if len(lines) > 1 else "",
        "current_company": "", "location": "", "experience_years": 0,
        "summary": "", "employment_history": [], "qualifications": [],
        "skills": [], "certifications": [], "achievements": [],
        "target_countries": [], "target_titles": []
    }
    # These values are extracted suggestions, never an assertion of verification.
    for label in ["M.Tech Environmental Engineering", "B.Tech Mechanical Engineering",
                  "MBA Human Resources", "Diploma in Industrial Safety"]:
        if label.lower() in raw_text.lower():
            result["qualifications"].append(label)
    match = re.search(r"\b(\d{1,2})\+?\s*(?:years|yrs)\b", raw_text, re.I)
    if match:
        result["experience_years"] = int(match.group(1))
    if len(lines) > 2:
        result["current_company"] = lines[2].split(",")[0].strip()
    return result
