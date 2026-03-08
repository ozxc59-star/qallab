"""
PDF → DOCX conversion using LibreOffice headless.

LibreOffice handles Arabic/RTL text, complex scripts, and mixed
bidirectional content far better than pdf2docx which loses Arabic text.
"""

import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

LIBREOFFICE_BINS = [
    "libreoffice",
    "soffice",
    "/usr/bin/libreoffice",
    "/usr/bin/soffice",
    "/usr/lib/libreoffice/program/soffice",
]


def find_libreoffice() -> str | None:
    for bin_path in LIBREOFFICE_BINS:
        if shutil.which(bin_path):
            return bin_path
    return None


def convert_pdf_to_docx(input_path: str, output_path: str) -> None:
    """
    Convert a PDF file to DOCX using LibreOffice headless.

    LibreOffice is used instead of pdf2docx because it correctly handles:
    - Arabic / RTL text
    - Mixed bidirectional content
    - Complex Arabic script shaping
    - Arabic fonts embedded in PDFs

    Args:
        input_path: Absolute path to the input PDF file.
        output_path: Absolute path where the output DOCX will be saved.

    Raises:
        RuntimeError: If LibreOffice is not available or conversion fails.
    """
    lo_bin = find_libreoffice()
    if not lo_bin:
        raise RuntimeError("LibreOffice is not installed. Cannot convert PDF to DOCX.")

    input_file = Path(input_path)
    output_file = Path(output_path)

    if not input_file.exists():
        raise RuntimeError(f"Input file not found: {input_path}")

    output_file.parent.mkdir(parents=True, exist_ok=True)

    logger.info(f"Converting PDF → DOCX: {input_file.name}")

    with tempfile.TemporaryDirectory() as tmp_dir:
        cmd = [
            lo_bin,
            "--headless",
            "--norestore",
            "--nofirststartwizard",
            "--convert-to", "docx:MS Word 2007 XML",
            "--outdir", tmp_dir,
            str(input_file),
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError("LibreOffice conversion timed out (>2 minutes)")
        except Exception as e:
            raise RuntimeError(f"Failed to run LibreOffice: {e}") from e

        if result.returncode != 0:
            logger.error(f"LibreOffice stderr: {result.stderr}")
            raise RuntimeError(
                f"LibreOffice exited with code {result.returncode}: {result.stderr[:500]}"
            )

        generated = list(Path(tmp_dir).glob("*.docx"))
        if not generated:
            raise RuntimeError("LibreOffice did not produce a DOCX output")

        shutil.move(str(generated[0]), str(output_file))

    if not output_file.exists() or output_file.stat().st_size == 0:
        raise RuntimeError("Conversion produced an empty or missing output file")

    logger.info(f"PDF→DOCX conversion complete: {output_file.stat().st_size} bytes")
