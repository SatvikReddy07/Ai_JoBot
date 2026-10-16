import os
import sys
import json
import pymupdf

# Set UTF-8 encoding for standard output
sys.stdout.reconfigure(encoding='utf-8')

pdf_path = "data/cv/20261016_034625_RnR_Updated_CV_HSE_Lead.pdf"
doc = pymupdf.open(pdf_path)

print(f"Total Pages in Master CV: {len(doc)}")
full_text = ""
for page_num, page in enumerate(doc):
    page_text = page.get_text()
    print(f"\n--- PAGE {page_num + 1} ({len(page_text)} chars) ---")
    print(page_text[:1200]) # First 1200 chars of each page
    full_text += f"\n[Page {page_num+1}]\n" + page_text

# Save full extracted text to text file for full cross-check
with open("data/cv/extracted_master_cv_full_text.txt", "w", encoding="utf-8") as f:
    f.write(full_text)

print("\nFull Master CV text saved to data/cv/extracted_master_cv_full_text.txt")
