"""
PDF -> DOCX conversion with full Arabic/RTL support + layout preservation.

Strategy tiers (attempted in order):
  Tier 1 — PyMuPDF rich extraction + python-docx rebuild
            Uses get_text("dict") for span-level detail: font size, bold,
            italic, position. Extracts embedded images and inserts them at
            the correct position. Detects headings by font size. RTL-aware.
  Tier 2 — Tesseract OCR + python-docx rebuild
            For image-based (scanned) PDFs. Renders each page at 200 DPI,
            runs tesseract with ara+eng, builds DOCX with RTL properties.
  Tier 3 — LibreOffice headless fallback
            Last resort. May produce rasterized DOCX for some inputs,
            but kept for edge cases.
"""

import io
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
# python-docx RTL / style helpers
# ===========================================================================

def _set_rtl_paragraph_props(paragraph) -> None:
    """Inject w:bidi and w:jc val="right" into paragraph properties."""
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


def _apply_cs_font(run, font_name: str) -> None:
    """
    Set complex-script (cs) font on a run.
    Arabic is a complex script — without w:rFonts w:cs Word uses Times New Roman
    which cannot render Arabic glyphs.
    """
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement

    rPr = run._r.get_or_add_rPr()
    cs_font = OxmlElement("w:rFonts")
    cs_font.set(qn("w:cs"), font_name)
    rPr.append(cs_font)


def _add_page_break(doc_word) -> None:
    """Insert a hard page break paragraph."""
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement

    para = doc_word.add_paragraph()
    run = para.add_run()
    br = OxmlElement("w:br")
    br.set(qn("w:type"), "page")
    run._r.append(br)


def _add_styled_paragraph(
    doc_word,
    text: str,
    font_size_pt: float = 11.0,
    bold: bool = False,
    italic: bool = False,
    font_name: str = "Amiri",
) -> None:
    """
    Add a paragraph with RTL/LTR detection, font size, bold, italic, and
    complex-script font set correctly for Arabic rendering.
    """
    from docx.shared import Pt

    is_rtl = detect_rtl(text)
    paragraph = doc_word.add_paragraph()

    if is_rtl:
        _set_rtl_paragraph_props(paragraph)
    else:
        _set_ltr_paragraph_props(paragraph)

    run = paragraph.add_run(text)
    run.font.name = font_name
    run.font.size = Pt(font_size_pt)
    run.font.bold = bold
    run.font.italic = italic

    if is_rtl:
        _set_run_rtl(run)

    _apply_cs_font(run, font_name)


# ===========================================================================
# Tier 1: PyMuPDF rich extraction -> python-docx
# ===========================================================================

def _classify_font_size(size: float, page_median: float) -> float:
    """
    Normalise raw PDF font size against the page median so headings are
    recognised reliably regardless of PDF zoom level.
    Returns a normalised size (median becomes 11pt for body text).
    """
    if page_median > 0:
        return (size / page_median) * 11.0
    return size


def _get_page_median_font_size(page_dict: dict) -> float:
    """
    Compute the median font size across all spans on a page.
    Used to normalise heading detection.
    """
    sizes = []
    for block in page_dict.get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                sz = span.get("size", 0)
                if sz > 0:
                    sizes.append(sz)
    if not sizes:
        return 11.0
    sizes.sort()
    mid = len(sizes) // 2
    return sizes[mid]


def _tier1_pymupdf_to_docx(input_path: str, output_path: str) -> bool:
    """
    Extract text AND images from a text-based PDF using PyMuPDF.

    Uses page.get_text("dict") for span-level detail:
      - font size  → heading vs. body detection
      - flags      → bold (bit 4 = 16) / italic (bit 1 = 2)
      - bbox       → spatial ordering (already sorted top-to-bottom)

    Uses page.get_images() + doc.extract_image() to embed raster images
    at the position they appear in the PDF flow.

    Returns True on success, False on any error.
    """
    try:
        import fitz  # pymupdf
        from docx import Document
        from docx.shared import Inches, Pt

        doc_pdf = fitz.open(input_path)
        doc_word = Document()

        # Remove the default empty paragraph python-docx adds
        for para in doc_word.paragraphs:
            p = para._element
            p.getparent().remove(p)

        # Set default Arabic font in the document styles
        _set_doc_default_font(doc_word, "Amiri")

        total_paragraphs = 0
        total_images = 0

        for page_num in range(len(doc_pdf)):
            page = doc_pdf[page_num]

            if page_num > 0:
                _add_page_break(doc_word)

            page_dict = page.get_text("dict", sort=True)
            median_size = _get_page_median_font_size(page_dict)

            # Build a map of image xrefs -> their bbox on the page so we can
            # insert images in reading order alongside text blocks.
            image_xref_map: dict[int, fitz.Rect] = {}
            for img_info in page.get_image_info(xrefs=True):
                xref = img_info.get("xref", 0)
                bbox = img_info.get("bbox")
                if xref and bbox:
                    image_xref_map[xref] = fitz.Rect(bbox)

            # Collect all items (text blocks + image blocks) sorted by
            # their top-left Y coordinate for reading-order output.
            items: list[tuple[float, str, dict]] = []  # (y0, kind, data)

            for block in page_dict.get("blocks", []):
                b_type = block.get("type", -1)
                bbox = block.get("bbox", [0, 0, 0, 0])
                y0 = bbox[1]

                if b_type == 0:  # text block
                    items.append((y0, "text", block))
                elif b_type == 1:  # image block embedded in page dict
                    items.append((y0, "image_block", block))

            # Also add standalone images from get_image_info
            for xref, rect in image_xref_map.items():
                # Check it's not already covered by an image block
                items.append((rect.y0, "image_xref", {"xref": xref, "rect": rect}))

            # Sort by y0 for top-to-bottom reading order
            items.sort(key=lambda x: x[0])

            inserted_image_xrefs: set[int] = set()

            for _y0, kind, data in items:
                if kind == "text":
                    for line in data.get("lines", []):
                        # Merge all spans in a line into one paragraph
                        # (spans share a line; splitting by span creates
                        # misaligned fragments for bidi text)
                        line_parts: list[tuple[str, float, bool, bool]] = []
                        for span in line.get("spans", []):
                            span_text = span.get("text", "").strip()
                            if not span_text:
                                continue
                            raw_size = span.get("size", 11.0)
                            flags = span.get("flags", 0)
                            is_bold = bool(flags & 16)
                            is_italic = bool(flags & 2)
                            norm_size = _classify_font_size(raw_size, median_size)
                            line_parts.append((span_text, norm_size, is_bold, is_italic))

                        if not line_parts:
                            continue

                        # Use the dominant (largest) font size for the line
                        line_text = " ".join(p[0] for p in line_parts)
                        dom_size = max(p[1] for p in line_parts)
                        any_bold = any(p[2] for p in line_parts)
                        any_italic = any(p[3] for p in line_parts)

                        # Heading detection: normalised size > 13.5pt is heading
                        if dom_size >= 18:
                            heading_level = 1
                        elif dom_size >= 15:
                            heading_level = 2
                        elif dom_size >= 13.5:
                            heading_level = 3
                        else:
                            heading_level = 0

                        if heading_level > 0:
                            _add_heading_paragraph(
                                doc_word, line_text, heading_level
                            )
                        else:
                            _add_styled_paragraph(
                                doc_word,
                                line_text,
                                font_size_pt=dom_size,
                                bold=any_bold,
                                italic=any_italic,
                            )
                        total_paragraphs += 1

                elif kind == "image_block":
                    # Image block from get_text("dict")
                    xref = data.get("image", {})
                    if isinstance(xref, dict):
                        xref = xref.get("xref", 0)
                    if xref and xref not in inserted_image_xrefs:
                        inserted = _insert_pdf_image(doc_pdf, doc_word, xref)
                        if inserted:
                            inserted_image_xrefs.add(xref)
                            total_images += 1

                elif kind == "image_xref":
                    xref = data["xref"]
                    if xref not in inserted_image_xrefs:
                        inserted = _insert_pdf_image(doc_pdf, doc_word, xref)
                        if inserted:
                            inserted_image_xrefs.add(xref)
                            total_images += 1

        doc_pdf.close()

        if total_paragraphs == 0 and total_images == 0:
            logger.warning("Tier 1: no content extracted — PDF may be image-only")
            return False

        doc_word.save(output_path)
        size = Path(output_path).stat().st_size
        logger.info(
            f"Tier 1 (PyMuPDF) succeeded: {total_paragraphs} paragraphs, "
            f"{total_images} images, {size} bytes"
        )
        return True

    except ImportError as exc:
        logger.warning(f"Tier 1 skipped — missing dependency: {exc}")
        return False
    except Exception as exc:
        logger.warning(f"Tier 1 failed: {exc}", exc_info=True)
        return False


def _set_doc_default_font(doc_word, font_name: str) -> None:
    """Set the default complex-script font for the entire document."""
    try:
        from docx.oxml.ns import qn
        from docx.oxml import OxmlElement

        rPr = doc_word.styles["Normal"].element.get_or_add_rPr()
        cs_font = OxmlElement("w:rFonts")
        cs_font.set(qn("w:cs"), font_name)
        rPr.append(cs_font)
    except Exception:
        pass  # Non-fatal — individual runs still have cs font set


def _add_heading_paragraph(doc_word, text: str, level: int) -> None:
    """Add a heading paragraph (level 1-3) with RTL/LTR detection."""
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement

    is_rtl = detect_rtl(text)
    try:
        heading = doc_word.add_heading(text, level=level)
    except Exception:
        heading = doc_word.add_paragraph(text)

    if is_rtl:
        _set_rtl_paragraph_props(heading)
        for run in heading.runs:
            _set_run_rtl(run)
            _apply_cs_font(run, "Amiri")
    else:
        for run in heading.runs:
            _apply_cs_font(run, "Amiri")


def _insert_pdf_image(doc_pdf, doc_word, xref: int) -> bool:
    """
    Extract image by xref from the PDF and insert it into the DOCX.
    Returns True if inserted successfully.
    """
    try:
        from docx.shared import Inches

        img_data = doc_pdf.extract_image(xref)
        if not img_data:
            return False

        image_bytes = img_data.get("image")
        if not image_bytes or len(image_bytes) < 100:
            return False

        ext = img_data.get("ext", "png").lower()
        if ext not in ("png", "jpg", "jpeg", "bmp", "tiff", "tif", "gif"):
            ext = "png"

        # Insert image — max width 6 inches to stay within page margins
        para = doc_word.add_paragraph()
        run = para.add_run()
        run.add_picture(io.BytesIO(image_bytes), width=Inches(6.0))
        return True

    except Exception as exc:
        logger.debug(f"Image insertion failed for xref {xref}: {exc}")
        return False


# ===========================================================================
# Tier 2: Tesseract OCR -> python-docx
# ===========================================================================

def _render_page_to_pil(page, dpi: int = 200):
    """Render a PyMuPDF page to a PIL Image at the given DPI."""
    from PIL import Image
    import fitz

    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    return Image.open(io.BytesIO(pix.tobytes("png")))


def _tier2_tesseract_ocr_to_docx(input_path: str, output_path: str) -> bool:
    """
    OCR each PDF page using Tesseract (ara+eng) and build a DOCX.

    Rendering via PyMuPDF at 200 DPI (faster than 300; adequate quality).
    OCR with LSTM engine (--oem 1) for best Arabic accuracy.
    RTL detection applied per line same as Tier 1.

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
                _add_page_break(doc_word)

            # 200 DPI — faster than 300, still good Arabic OCR accuracy
            pil_image = _render_page_to_pil(page, dpi=200)

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
                _add_styled_paragraph(doc_word, line)
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
        logger.warning(f"Tier 2 failed: {exc}", exc_info=True)
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
    Convert a PDF to DOCX with Arabic/RTL support and layout preservation.

    Tier 1: PyMuPDF rich extraction -> python-docx
            Preserves: font sizes, bold/italic, headings, embedded images
            Fast: pure Python, no subprocess
    Tier 2: Tesseract OCR -> python-docx (scanned/image-based PDFs)
            200 DPI for speed, ara+eng LSTM for accuracy
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
        # Text-based: try PyMuPDF first (fast, rich layout), then OCR, then LO
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
