"""
Multi-Format Document Processing & Lightning-Fast OCR Engine - Layer 3, Branch A
Extracts structured text, entities, financial figures, statutory IDs,
and clause evidence from uploaded PDF (including Scanned Image PDFs),
Images (JPG, PNG, TIFF, BMP, WEBP), Word (.docx), and Excel (.xlsx) bid documents and Tender RFPs.

Optimized for cloud-hosting (Render/MeghRaj) with adaptive page-sampling,
smart downsampling, and sub-3-second extraction on multi-page files.
"""
import pymupdf
import docx
import openpyxl
import pandas as pd
import re
import os
import cv2
import numpy as np

# Initialize RapidOCR with lazy singleton loading
_ocr_engine = None

def get_ocr_engine():
    global _ocr_engine
    if _ocr_engine is None:
        try:
            from rapidocr_onnxruntime import RapidOCR
            _ocr_engine = RapidOCR()
        except Exception as e:
            print(f"RapidOCR initialization notice: {e}")
            _ocr_engine = None
    return _ocr_engine


def extract_document_text(file_path: str) -> tuple[str, int, str]:
    """
    Universal high-speed text & OCR extractor returning (full_text, page_count, file_type).
    - Digital PDFs: extracted in ~30ms via PyMuPDF.
    - Scanned PDFs: prioritizes critical metadata pages (first 4 + last 2 pages) at 110 DPI for <3s execution.
    - Large Images: auto-scaled to max 1600px to prevent ONNX bottlenecks.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    ext = os.path.splitext(file_path)[1].lower()
    full_text = ""
    page_count = 1

    # 1. PDF (Digital Text or Scanned Image PDF)
    if ext == ".pdf":
        try:
            doc = pymupdf.open(file_path)
            page_count = len(doc)
            digital_pages = []
            pages_needing_ocr = []

            # Fast digital text extraction pass (<50ms for 50 pages)
            for i, page in enumerate(doc):
                t = page.get_text()
                if t and len(t.strip()) > 30:
                    digital_pages.append(f"\n--- Page {i + 1} ---\n" + t)
                else:
                    pages_needing_ocr.append(i)

            # If digital text exists across the document, use it
            if len(digital_pages) > 0 and len("".join(digital_pages).strip()) >= 50:
                full_text = "\n".join(digital_pages)
