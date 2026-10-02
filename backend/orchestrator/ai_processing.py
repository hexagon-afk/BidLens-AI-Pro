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


