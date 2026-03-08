"""
PDF -> DOCX conversion with full Arabic/RTL support.

Strategy tiers (attempted in order):
  Tier 1 — PyMuPDF text extraction + python-docx rebuild
            Best for text-based Arabic PDFs. Extracts actual characters,
            detects RTL per paragraph, sets w:bidi + right-align in DOCX.
  Tier 2 — Tesseract OCR + python-docx rebuild
            For image-based (scanned) PDFs. Renders each page at 300 DPI,
            runs tesseract with ara+eng, builds DOCX with RTL properties.
  Tier 3 — LibreOffice headless fallback
            Last resort. May produce rasterized DOCX for some inputs,
            but kept for edge cases (tables, embedded objects, etc.).
"""

import logging
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Arabic Unicode ranges for RTL detection
# U+0600–U+06FF  Arabic
# U+0750–U+077F  Arabic Supplement
# U+08A0–U+08FF  Arabic Extended-A
# U+FB50–U+FDFF  Arabic Presentation Forms-A
# U+FE70–U+FEFF  Arabic Presentation Forms-B
# ---------------------------------------------------------------------------
_ARABIC_RE = re.compile(
    r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]"
)

# Minimum extractable characters on page 1 to classify PDF as text-based
_TEXT_THRESHOLD = 50

LIBREOFFICE_BINS = [
    "libreoffice",
    "soffice",
    "/usr/bin/libreoffice",
    "/usr/bin/soffice",
    "/usr/lib/libreoffice/program/soffice",
]


# ===========================================================================
# Utility helpers
# ===========================================================================

def find_libreoffice() -> str | None:
    for bin_path in LIBREOFFICE_BINS:
        if shutil.which(bin_path):
            return bin_path
    return None


def detect_rtl(text: str) -> bool:
    """Return True if the text contains Arabic characters (RTL paragraph)."""
    return bool(_ARABIC_RE.search(text))


def is_text_based_pdf(pdf_path: str) -> bool:
    """
    Return True if the PDF has extractable text (not just images).
    Checks the first page for at least _TEXT_THRESHOLD non-whitespace chars.
    """
    try:
        import fitz  # pymupdf
        doc = fitz.open(pdf_path)
        if len(doc) == 0:
            return False
        text = doc[0].get_text("text")
        doc.close()
        return len(text.strip()) >= _TEXT_THRESHOLD
    except Exception as exc:
        logger.warning(f"is_text_based_pdf check failed: {exc}")
        return False


# ===========================================================================
# python-docx RTL helpers
# ===========================================================================

def _set_rtl_paragraph_props(paragraph) -> None:
    """
    Inject w:bidi and w:jc val="right" into paragraph properties.
    Both are required for Word to render an RTL paragraph correctly.
    """
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement

    pPr = paragraph._p.get_or_add_pPr()

    bidi = OxmlElement("w:bidi")
    pPr.append(bidi)

    jc = OxmlElement("w:jc")
    jc.set(qn("w:val"), "right")
    pPr.append(jc)


def _set_ltr_paragraph_props(paragraph) -> None:
    """Set explicit left alignment for LTR paragraphs."""
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement

    pPr = paragraph._p.get_or_add_pPr()
    jc = OxmlElement("w:jc")
    jc.set(qn("w:val"), "left")
    pPr.append(jc)


def _set_run_rtl(run) -> None:
    """Inject w:rtl into run properties — required for correct char order."""
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement

    rPr = run._r.get_or_add_rPr()
    rtl_el = OxmlElement("w:rtl")
    rPr.append(rtl_el)


def build_rtl_paragraph(doc, text: str, font_name: str = "Amiri") -> None:
    """
    Add a paragraph to doc with full RTL or LTR properties as needed.

    Sets:
      - w:bidi + w:jc right  (RTL paragraphs)
      - w:rtl on run          (RTL paragraphs)
      - w:rFonts w:cs         (complex script font — critical for Arabic in Word)
    """
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement

    paragraph = doc.add_paragraph()
    is_rtl = detect_rtl(text)

    if is_rtl:
        _set_rtl_paragraph_props(paragraph)
    else:
        _set_ltr_paragraph_props(paragraph)

    run = paragraph.add_run(text)
    run.font.name = font_name

    if is_rtl:
        _set_run_rtl(run)

    # w:rFonts w:cs sets the complex-script font.
    # Arabic is a complex script in Word; without this it defaults to
    # Times New Roman which cannot render Arabic glyphs.
    rPr = run._r.get_or_add_rPr()
    cs_font = OxmlElement("w:rFonts")
    cs_font.set(qn("w:cs"), font_name)
    rPr.append(cs_font)


# ===========================================================================
# Tier 1: PyMuPDF text extraction -> python-docx
# ===========================================================================

def _tier1_pymupdf_to_docx(input_path: str, output_path: str) -> bool:
    """
    Extract text from a text-based PDF using PyMuPDF and write a DOCX.

    Uses get_text("blocks") which returns text blocks sorted top-to-bottom.
    Each block: (x0, y0, x1, y1, text, block_no, block_type)
    block_type 0 = text, 1 = image (skipped).

    Returns True on success, False on any error.
    """
    try:
        import fitz  # pymupdf
        from docx import Document

        doc_pdf = fitz.open(input_path)
        doc_word = Document()

        # Remove the default empty paragraph python-docx adds
        for para in doc_word.paragraphs:
            p = para._element
            p.getparent().remove(p)

        total_paragraphs = 0

        for page_num in range(len(doc_pdf)):
            page = doc_pdf[page_num]
            blocks = page.get_text("blocks")

            # Page break between pages (not before the first)
            if page_num > 0:
                from docx.oxml.ns import qn
                from docx.oxml import OxmlElement
                para = doc_word.add_paragraph()
                run = para.add_run()
                br = OxmlElement("w:br")
                br.set(qn("w:type"), "page")
                run._r.append(br)

            for block in blocks:
                if len(block) < 7:
                    continue
                if block[6] != 0:
                    continue  # skip image blocks

                block_text = block[4]
                if not block_text or not block_text.strip():
                    continue

                for line in block_text.split("\n"):
                    line = line.strip()
                    if not line:
                        continue
                    build_rtl_paragraph(doc_word, line)
                    total_paragraphs += 1

        doc_pdf.close()

        if total_paragraphs == 0:
            logger.warning("Tier 1: no text paragraphs extracted — PDF may be image-only")
            return False

        doc_word.save(output_path)
        logger.info(
            f"Tier 1 (PyMuPDF) succeeded: {total_paragraphs} paragraphs, "
            f"{Path(output_path).stat().st_size} bytes"
        )
        return True

    except ImportError as exc:
        logger.warning(f"Tier 1 skipped — missing dependency: {exc}")
        return False
    except Exception as exc:
        logger.warning(f"Tier 1 failed: {exc}")
        return False


# ===========================================================================
# Tier 2: Tesseract OCR -> python-docx
# ===========================================================================

def _render_page_to_pil(page, dpi: int = 300):
    """Render a PyMuPDF page to a PIL Image at the given DPI."""
    from PIL import Image
    import io
    import fitz

    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    return Image.open(io.BytesIO(pix.tobytes("png")))


def _tier2_tesseract_ocr_to_docx(input_path: str, output_path: str) -> bool:
    """
    OCR each PDF page using Tesseract (ara+eng) and build a DOCX.

    Rendering via PyMuPDF at 300 DPI. OCR with LSTM engine (--oem 1) for
    best Arabic accuracy. RTL detection applied per line same as Tier 1.

    Returns True on success, False on any error.
    """
    try:
        import fitz  # pymupdf
        import pytesseract
        from docx import Document

        # Verify tesseract binary is present
        try:
            subprocess.run(
                ["tesseract", "--version"],
                capture_output=True,
                timeout=10,
                check=True,
            )
        except (subprocess.CalledProcessError, FileNotFoundError) as exc:
            logger.warning(f"Tier 2 skipped — tesseract not found: {exc}")
            return False

        doc_pdf = fitz.open(input_path)
        doc_word = Document()

        for para in doc_word.paragraphs:
            p = para._element
            p.getparent().remove(p)

        total_paragraphs = 0

        for page_num in range(len(doc_pdf)):
            page = doc_pdf[page_num]

            if page_num > 0:
                from docx.oxml.ns import qn
                from docx.oxml import OxmlElement
                para = doc_word.add_paragraph()
                run = para.add_run()
                br = OxmlElement("w:br")
                br.set(qn("w:type"), "page")
                run._r.append(br)

            pil_image = _render_page_to_pil(page, dpi=300)

            ocr_text = pytesseract.image_to_string(
                pil_image,
                lang="ara+eng",
                config="--psm 3 --oem 1",
            )

            if not ocr_text or not ocr_text.strip():
                logger.info(f"Tier 2: page {page_num + 1} returned empty OCR")
                continue

            for line in ocr_text.split("\n"):
                line = line.strip()
                if not line:
                    continue
                build_rtl_paragraph(doc_word, line)
                total_paragraphs += 1

        doc_pdf.close()

        if total_paragraphs == 0:
            logger.warning("Tier 2: no text extracted via OCR")
            return False

        doc_word.save(output_path)
        logger.info(
            f"Tier 2 (Tesseract OCR) succeeded: {total_paragraphs} paragraphs, "
            f"{Path(output_path).stat().st_size} bytes"
        )
        return True

    except ImportError as exc:
        logger.warning(f"Tier 2 skipped — missing dependency: {exc}")
        return False
    except Exception as exc:
        logger.warning(f"Tier 2 failed: {exc}")
        return False


# ===========================================================================
# Tier 3: LibreOffice fallback
# ===========================================================================

def _run_lo(
    lo_bin: str,
    extra_args: list,
    input_file: Path,
    out_dir: Path,
) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["LANG"] = "en_US.UTF-8"
    env["LC_ALL"] = "en_US.UTF-8"
    cmd = [
        lo_bin,
        "--headless",
        "--norestore",
        "--nofirststartwizard",
        *extra_args,
        "--outdir", str(out_dir),
        str(input_file),
    ]
    logger.info(f"LO running: {' '.join(cmd)}")
    return subprocess.run(cmd, capture_output=True, text=True, timeout=120, env=env)


def _tier3_libreoffice_fallback(input_path: str, output_path: str) -> bool:
    """
    LibreOffice-based last resort. Tries writer_pdf_import → direct → ODT→DOCX.
    May produce rasterized images for Arabic PDFs but kept as a safety net.

    Returns True on success, False if all LibreOffice strategies fail.
    """
    lo_bin = find_libreoffice()
    if not lo_bin:
        logger.warning("Tier 3 skipped — LibreOffice not found")
        return False

    input_file = Path(input_path)
    output_file = Path(output_path)

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # 3a: writer_pdf_import filter
        result = _run_lo(
            lo_bin,
            ["--infilter=writer_pdf_import", "--convert-to", "docx"],
            input_file, tmp_path,
        )
        docx_files = list(tmp_path.glob("*.docx"))
        if docx_files:
            shutil.move(str(docx_files[0]), str(output_file))
            logger.info(f"Tier 3a (writer_pdf_import) succeeded: {output_file.stat().st_size} bytes")
            return True
        logger.warning(f"Tier 3a failed. rc={result.returncode} stdout={result.stdout!r} stderr={result.stderr!r}")

        # 3b: direct convert
        result = _run_lo(lo_bin, ["--convert-to", "docx"], input_file, tmp_path)
        docx_files = list(tmp_path.glob("*.docx"))
        if docx_files:
            shutil.move(str(docx_files[0]), str(output_file))
            logger.info(f"Tier 3b (direct) succeeded: {output_file.stat().st_size} bytes")
            return True
        logger.warning(f"Tier 3b failed. rc={result.returncode} stdout={result.stdout!r} stderr={result.stderr!r}")

        # 3c: PDF -> ODT -> DOCX two-step
        odt_dir = tmp_path / "odt"
        odt_dir.mkdir()
        result = _run_lo(lo_bin, ["--convert-to", "odt"], input_file, odt_dir)
        odt_files = list(odt_dir.glob("*.odt"))
        if odt_files:
            docx_dir = tmp_path / "docx"
            docx_dir.mkdir()
            result2 = _run_lo(lo_bin, ["--convert-to", "docx"], odt_files[0], docx_dir)
            docx_files = list(docx_dir.glob("*.docx"))
            if docx_files:
                shutil.move(str(docx_files[0]), str(output_file))
                logger.info(f"Tier 3c (ODT->DOCX) succeeded: {output_file.stat().st_size} bytes")
                return True
            logger.warning(f"Tier 3c step2 failed. rc={result2.returncode} stdout={result2.stdout!r} stderr={result2.stderr!r}")
        else:
            logger.warning(f"Tier 3c step1 failed. rc={result.returncode} stdout={result.stdout!r} stderr={result.stderr!r}")

    return False


# ===========================================================================
# Public entry point
# ===========================================================================

def convert_pdf_to_docx(input_path: str, output_path: str) -> None:
    """
    Convert a PDF to DOCX with Arabic/RTL support.

    Tier 1: PyMuPDF text extraction -> python-docx (text-based PDFs)
    Tier 2: Tesseract OCR -> python-docx (scanned/image-based PDFs)
    Tier 3: LibreOffice headless (last resort for all edge cases)

    Args:
        input_path:  Absolute path to the input PDF.
        output_path: Absolute path where the output DOCX will be saved.

    Raises:
        RuntimeError: If all tiers fail.
    """
    input_file = Path(input_path)
    output_file = Path(output_path)

    if not input_file.exists():
        raise RuntimeError(f"Input file not found: {input_path}")

    output_file.parent.mkdir(parents=True, exist_ok=True)

    logger.info(f"Converting PDF -> DOCX: {input_file.name}")

    pdf_is_text_based = is_text_based_pdf(input_path)
    logger.info(f"PDF type: {'text-based' if pdf_is_text_based else 'image-based (scanned)'}")

    if pdf_is_text_based:
        # Text-based: try PyMuPDF first, then OCR, then LibreOffice
        if _tier1_pymupdf_to_docx(input_path, output_path):
            return
        logger.warning("Tier 1 failed — trying Tier 2 (OCR)")
        if _tier2_tesseract_ocr_to_docx(input_path, output_path):
            return
        logger.warning("Tier 2 failed — trying Tier 3 (LibreOffice)")
        if _tier3_libreoffice_fallback(input_path, output_path):
            return
    else:
        # Image-based: skip Tier 1, go straight to OCR
        logger.info("Image-based PDF — starting with Tier 2 (Tesseract OCR)")
        if _tier2_tesseract_ocr_to_docx(input_path, output_path):
            return
        logger.warning("Tier 2 failed — trying Tier 3 (LibreOffice)")
        if _tier3_libreoffice_fallback(input_path, output_path):
            return

    raise RuntimeError(
        "PDF->DOCX conversion failed with all strategies. "
        "The PDF may be encrypted, password-protected, or severely corrupted."
    )
