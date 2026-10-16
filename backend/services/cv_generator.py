import shutil
from pathlib import Path
from typing import Dict, Any, Optional

import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether, HRFlowable
from reportlab.lib import colors

from backend.app.schemas import TailoredCVContent, TailoredCoverLetterContent

def check_pdf_converter_availability() -> Dict[str, Any]:
    """Detects available PDF conversion engines."""
    libreoffice_paths = [
        Path("C:/Program Files/LibreOffice/program/soffice.exe"),
        Path("C:/Program Files (x86)/LibreOffice/program/soffice.exe"),
        Path(shutil.which("soffice") or "")
    ]
    lo_found = any(p.exists() for p in libreoffice_paths if p.name)
    
    return {
        "available": True,
        "primary_engine": "reportlab_native",
        "libreoffice_detected": lo_found,
        "description": "High-fidelity vector PDF generation with selectable text layer via ReportLab / PyMuPDF."
    }

def add_docx_hr(paragraph):
    """Adds a subtle horizontal divider line under section headings."""
    pPr = paragraph._p.get_or_add_pPr()
    pBdr = OxmlElement('w:pBdr')
    bottom = OxmlElement('w:bottom')
    bottom.set(qn('w:val'), 'single')
    bottom.set(qn('w:sz'), '6')
    bottom.set(qn('w:space'), '1')
    bottom.set(qn('w:color'), '334155') # slate-700
    pBdr.append(bottom)
    pPr.append(pBdr)

def generate_cv_docx(cv_data: TailoredCVContent, output_path: Path) -> Path:
    """
    Generates a clean, ATS-compliant, single-column executive resume in DOCX format.
    Uses standard Calibri / Arial font, standard headings, and single-column flow.
    """
    doc = docx.Document()

    # Set 0.7 inch margins
    for section in doc.sections:
        section.top_margin = Inches(0.7)
        section.bottom_margin = Inches(0.7)
        section.left_margin = Inches(0.7)
        section.right_margin = Inches(0.7)

    # 1. Header (Name, Headline, Contact)
    p_name = doc.add_paragraph()
    p_name.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_name = p_name.add_run(cv_data.name)
    r_name.font.name = "Calibri"
    r_name.font.size = Pt(20)
    r_name.font.bold = True
    r_name.font.color.rgb = RGBColor(15, 23, 42) # slate-900

    p_head = doc.add_paragraph()
    p_head.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_head = p_head.add_run(cv_data.headline)
    r_head.font.name = "Calibri"
    r_head.font.size = Pt(11)
    r_head.font.bold = True
    r_head.font.color.rgb = RGBColor(13, 148, 136) # emerald-teal

    p_contact = doc.add_paragraph()
    p_contact.alignment = WD_ALIGN_PARAGRAPH.CENTER
    contact_parts = [cv_data.contact_location, cv_data.contact_phone, cv_data.contact_email, cv_data.contact_linkedin]
    r_contact = p_contact.add_run("  •  ".join([c for c in contact_parts if c]))
    r_contact.font.name = "Calibri"
    r_contact.font.size = Pt(9.5)
    r_contact.font.color.rgb = RGBColor(71, 85, 105) # slate-600

    # 2. Section: Professional Summary
    h_sum = doc.add_paragraph()
    add_docx_hr(h_sum)
    r_sum = h_sum.add_run("EXECUTIVE PROFESSIONAL SUMMARY")
    r_sum.font.name = "Calibri"
    r_sum.font.size = Pt(11)
    r_sum.font.bold = True
    r_sum.font.color.rgb = RGBColor(30, 41, 59)

    p_sum = doc.add_paragraph(cv_data.summary)
    p_sum.paragraph_format.line_spacing = 1.15
    p_sum.paragraph_format.space_after = Pt(8)
    for r in p_sum.runs:
        r.font.name = "Calibri"
        r.font.size = Pt(10)

    # 3. Section: Core Competencies
    h_skills = doc.add_paragraph()
    add_docx_hr(h_skills)
    r_skills = h_skills.add_run("CORE COMPETENCIES & HSE GOVERNANCE")
    r_skills.font.name = "Calibri"
    r_skills.font.size = Pt(11)
    r_skills.font.bold = True
    r_skills.font.color.rgb = RGBColor(30, 41, 59)

    # Single-column bullet points (ATS best practice)
    for skill in cv_data.core_competencies:
        p_sk = doc.add_paragraph(skill, style="List Bullet")
        p_sk.paragraph_format.space_after = Pt(2)
        p_sk.paragraph_format.line_spacing = 1.05
        for r in p_sk.runs:
            r.font.name = "Calibri"
            r.font.size = Pt(9.5)

    # 4. Section: Professional Experience
    h_exp = doc.add_paragraph()
    add_docx_hr(h_exp)
    r_exp = h_exp.add_run("PROFESSIONAL LEADERSHIP EXPERIENCE")
    r_exp.font.name = "Calibri"
    r_exp.font.size = Pt(11)
    r_exp.font.bold = True
    r_exp.font.color.rgb = RGBColor(30, 41, 59)

    for item in cv_data.employment_history:
        p_role = doc.add_paragraph()
        p_role.paragraph_format.space_before = Pt(6)
        p_role.paragraph_format.space_after = Pt(2)
        
        r_co = p_role.add_run(item.company)
        r_co.font.bold = True
        r_co.font.size = Pt(10.5)
        r_co.font.color.rgb = RGBColor(15, 23, 42)

        r_sep = p_role.add_run("  |  ")
        r_sep.font.color.rgb = RGBColor(148, 163, 184)

        r_title = p_role.add_run(item.role)
        r_title.font.italic = True
        r_title.font.size = Pt(10)
        r_title.font.color.rgb = RGBColor(51, 65, 85)

        if item.location:
            r_loc = p_role.add_run(f"  ({item.location})")
            r_loc.font.size = Pt(9.5)
            r_loc.font.color.rgb = RGBColor(100, 116, 139)

        for hl in item.highlights:
            p_hl = doc.add_paragraph(hl, style="List Bullet")
            p_hl.paragraph_format.space_after = Pt(2)
            p_hl.paragraph_format.line_spacing = 1.1
            for r in p_hl.runs:
                r.font.name = "Calibri"
                r.font.size = Pt(9.5)

    # 5. Section: Education
    h_edu = doc.add_paragraph()
    add_docx_hr(h_edu)
    r_edu = h_edu.add_run("EDUCATION & ACADEMIC CREDENTIALS")
    r_edu.font.name = "Calibri"
    r_edu.font.size = Pt(11)
    r_edu.font.bold = True
    r_edu.font.color.rgb = RGBColor(30, 41, 59)

    for edu in cv_data.education:
        p_edu = doc.add_paragraph(edu, style="List Bullet")
        p_edu.paragraph_format.space_after = Pt(2)
        for r in p_edu.runs:
            r.font.name = "Calibri"
            r.font.size = Pt(9.5)

    # 6. Section: Certifications
    if cv_data.certifications:
        h_cert = doc.add_paragraph()
        add_docx_hr(h_cert)
        r_cert = h_cert.add_run("CERTIFICATIONS & MANAGEMENT SYSTEMS")
        r_cert.font.name = "Calibri"
        r_cert.font.size = Pt(11)
        r_cert.font.bold = True
        r_cert.font.color.rgb = RGBColor(30, 41, 59)

        for cert in cv_data.certifications:
            p_c = doc.add_paragraph(cert, style="List Bullet")
            p_c.paragraph_format.space_after = Pt(2)
            for r in p_c.runs:
                r.font.name = "Calibri"
                r.font.size = Pt(9.5)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output_path))
    return output_path

def generate_cv_pdf(cv_data: TailoredCVContent, output_path: Path) -> Path:
    """
    Generates matching text-selectable vector PDF resume using ReportLab.
    ATS-friendly single-column layout with standard fonts and clean margins.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=40,
        rightMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()

    # Custom styles
    name_style = ParagraphStyle(
        'CVName',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        alignment=1, # Center
        textColor=colors.HexColor('#0F172A')
    )
    headline_style = ParagraphStyle(
        'CVHeadline',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=15,
        alignment=1,
        textColor=colors.HexColor('#0D9488')
    )
    contact_style = ParagraphStyle(
        'CVContact',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        alignment=1,
        textColor=colors.HexColor('#475569')
    )
    sec_heading_style = ParagraphStyle(
        'CVSecHeading',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=15,
        textColor=colors.HexColor('#1E293B'),
        spaceBefore=10,
        spaceAfter=4
    )
    body_style = ParagraphStyle(
        'CVBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13.5,
        textColor=colors.HexColor('#1E293B'),
        spaceAfter=4
    )
    role_header_style = ParagraphStyle(
        'CVRoleHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#0F172A'),
        spaceBefore=6,
        spaceAfter=2
    )
    bullet_style = ParagraphStyle(
        'CVBullet',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12.5,
        leftIndent=15,
        textColor=colors.HexColor('#334155'),
        spaceAfter=2
    )

    story = []

    # 1. Header
    story.append(Paragraph(cv_data.name, name_style))
    story.append(Paragraph(cv_data.headline, headline_style))
    contact_str = " &nbsp;•&nbsp; ".join([c for c in [cv_data.contact_location, cv_data.contact_phone, cv_data.contact_email, cv_data.contact_linkedin] if c])
    story.append(Paragraph(contact_str, contact_style))
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#CBD5E1'), spaceBefore=2, spaceAfter=8))

    # 2. Executive Summary
    story.append(Paragraph("EXECUTIVE PROFESSIONAL SUMMARY", sec_heading_style))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#94A3B8'), spaceBefore=1, spaceAfter=6))
    story.append(Paragraph(cv_data.summary, body_style))
    story.append(Spacer(1, 6))

    # 3. Core Competencies
    story.append(Paragraph("CORE COMPETENCIES & HSE GOVERNANCE", sec_heading_style))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#94A3B8'), spaceBefore=1, spaceAfter=6))
    for skill in cv_data.core_competencies:
        story.append(Paragraph(f"• {skill}", bullet_style))
    story.append(Spacer(1, 6))

    # 4. Employment History
    story.append(Paragraph("PROFESSIONAL LEADERSHIP EXPERIENCE", sec_heading_style))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#94A3B8'), spaceBefore=1, spaceAfter=6))
    for item in cv_data.employment_history:
        loc_str = f" ({item.location})" if item.location else ""
        header_text = f"<b>{item.company}</b> &nbsp;|&nbsp; <i>{item.role}</i>{loc_str}"
        story.append(Paragraph(header_text, role_header_style))
        for hl in item.highlights:
            story.append(Paragraph(f"• {hl}", bullet_style))
        story.append(Spacer(1, 4))

    # 5. Education
    story.append(Paragraph("EDUCATION & ACADEMIC CREDENTIALS", sec_heading_style))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#94A3B8'), spaceBefore=1, spaceAfter=6))
    for edu in cv_data.education:
        story.append(Paragraph(f"• {edu}", bullet_style))
    story.append(Spacer(1, 6))

    # 6. Certifications
    if cv_data.certifications:
        story.append(Paragraph("CERTIFICATIONS & MANAGEMENT SYSTEMS", sec_heading_style))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#94A3B8'), spaceBefore=1, spaceAfter=6))
        for cert in cv_data.certifications:
            story.append(Paragraph(f"• {cert}", bullet_style))

    doc.build(story)
    return output_path

def generate_cover_letter_docx(letter_data: TailoredCoverLetterContent, output_path: Path) -> Path:
    """Generates tailored executive cover letter in DOCX format."""
    doc = docx.Document()
    for section in doc.sections:
        section.top_margin = Inches(0.9)
        section.bottom_margin = Inches(0.9)
        section.left_margin = Inches(0.9)
        section.right_margin = Inches(0.9)

    # Header
    p_name = doc.add_paragraph()
    r_name = p_name.add_run(letter_data.candidate_name)
    r_name.font.name = "Calibri"
    r_name.font.size = Pt(16)
    r_name.font.bold = True
    r_name.font.color.rgb = RGBColor(15, 23, 42)

    p_contact = doc.add_paragraph(letter_data.candidate_contact)
    p_contact.paragraph_format.space_after = Pt(16)
    for r in p_contact.runs:
        r.font.name = "Calibri"
        r.font.size = Pt(9.5)
        r.font.color.rgb = RGBColor(71, 85, 105)

    # Date
    p_date = doc.add_paragraph(letter_data.date_str)
    p_date.paragraph_format.space_after = Pt(12)
    for r in p_date.runs:
        r.font.name = "Calibri"
        r.font.size = Pt(10)

    # Recipient
    p_rec = doc.add_paragraph()
    p_rec.paragraph_format.space_after = Pt(14)
    r_hm = p_rec.add_run(f"{letter_data.hiring_manager}\n")
    r_co = p_rec.add_run(f"{letter_data.company_name}\n")
    r_re = p_rec.add_run(f"RE: Application for {letter_data.job_title}")
    r_re.font.bold = True
    for r in p_rec.runs:
        r.font.name = "Calibri"
        r.font.size = Pt(10)

    # Salutation
    p_sal = doc.add_paragraph(letter_data.salutation)
    p_sal.paragraph_format.space_after = Pt(10)
    for r in p_sal.runs:
        r.font.name = "Calibri"
        r.font.size = Pt(10)

    # Body paragraphs
    for p_text in letter_data.body_paragraphs:
        p = doc.add_paragraph(p_text)
        p.paragraph_format.line_spacing = 1.2
        p.paragraph_format.space_after = Pt(10)
        for r in p.runs:
            r.font.name = "Calibri"
            r.font.size = Pt(10.5)

    # Sign-off
    p_sign = doc.add_paragraph(letter_data.sign_off)
    p_sign.paragraph_format.space_before = Pt(12)
    for r in p_sign.runs:
        r.font.name = "Calibri"
        r.font.size = Pt(10.5)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output_path))
    return output_path

def generate_cover_letter_pdf(letter_data: TailoredCoverLetterContent, output_path: Path) -> Path:
    """Generates tailored executive cover letter in vector PDF format using ReportLab."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )

    styles = getSampleStyleSheet()

    name_style = ParagraphStyle(
        'CLName',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=16,
        leading=20,
        textColor=colors.HexColor('#0F172A')
    )
    contact_style = ParagraphStyle(
        'CLContact',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=14,
        textColor=colors.HexColor('#475569'),
        spaceAfter=14
    )
    normal_style = ParagraphStyle(
        'CLNormal',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#1E293B'),
        spaceAfter=10
    )
    body_style = ParagraphStyle(
        'CLBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=15,
        textColor=colors.HexColor('#1E293B'),
        spaceAfter=12
    )

    story = []
    story.append(Paragraph(letter_data.candidate_name, name_style))
    story.append(Paragraph(letter_data.candidate_contact, contact_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#CBD5E1'), spaceBefore=2, spaceAfter=14))

    story.append(Paragraph(letter_data.date_str, normal_style))
    story.append(Paragraph(f"<b>{letter_data.hiring_manager}</b><br/>{letter_data.company_name}<br/><b>RE: Application for {letter_data.job_title}</b>", normal_style))
    story.append(Spacer(1, 6))
    story.append(Paragraph(letter_data.salutation, normal_style))

    for p in letter_data.body_paragraphs:
        story.append(Paragraph(p, body_style))

    story.append(Spacer(1, 10))
    story.append(Paragraph(letter_data.sign_off.replace("\n", "<br/>"), normal_style))

    doc.build(story)
    return output_path
