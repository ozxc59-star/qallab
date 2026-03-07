"""
PDF → DOCX conversion using pdf2docx.

Quality note: Scanned Arabic PDFs (image-based) will have poor quality
because pdf2docx relies on text extraction. This limitation is surfaced
to users in the UI via a warning.

For best results, the PDF must have selectable/searchable text.
"""

import logging
from pathlib import Path
from pdf2docx import Converter

logger = logging.getLogger(__name__)


def convert_pdf_to_docx(input_path: str, output_path: str) -> None:
    """
    Convert a PDF file to DOCX format.

    Args:
        input_path: Absolute path to the input PDF file.
        output_path: Absolute path where the output DOCX will be saved.

    Raises:
        RuntimeError: If conversion fails.
    """
    input_file = Path(input_path)
    output_file = Path(output_path)

    if not input_file.exists():
        raise RuntimeError(f"Input file not found: {input_path}")

    logger.info(f"Converting PDF → DOCX: {input_file.name}")

    try:
        cv = Converter(str(input_file))
        cv.convert(str(output_file), start=0, end=None)
        cv.close()
    except Exception as e:
        logger.error(f"PDF→DOCX conversion failed: {e}")
        raise RuntimeError(f"PDF→DOCX conversion failed: {e}") from e

    if not output_file.exists() or output_file.stat().st_size == 0:
        raise RuntimeError("Conversion produced an empty or missing output file")

    logger.info(
        f"PDF→DOCX conversion complete: {output_file.stat().st_size} bytes"
    )
