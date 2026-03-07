"""
DOCX → PDF conversion using LibreOffice headless.

LibreOffice provides the best Arabic text shaping support:
- Kashida (كشيدة) preservation
- Bidirectional text handling
- Arabic font rendering
- Complex script shaping

The subprocess approach avoids LibreOffice Python UNO binding complexity
and works reliably in Docker containers.
"""

import logging
import subprocess
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

# LibreOffice binary — try multiple common paths
LIBREOFFICE_BINS = [
    "libreoffice",
    "soffice",
    "/usr/bin/libreoffice",
    "/usr/bin/soffice",
    "/usr/lib/libreoffice/program/soffice",
]


def find_libreoffice() -> str | None:
    """Return the first available LibreOffice binary path."""
    for bin_path in LIBREOFFICE_BINS:
        if shutil.which(bin_path):
            return bin_path
    return None


def is_libreoffice_available() -> bool:
    return find_libreoffice() is not None


def convert_docx_to_pdf(input_path: str, output_path: str) -> None:
    """
    Convert a DOCX file to PDF using LibreOffice headless.

    Args:
        input_path: Absolute path to the input DOCX/DOC file.
        output_path: Absolute path where the output PDF will be saved.

    Raises:
        RuntimeError: If LibreOffice is not available or conversion fails.
    """
    lo_bin = find_libreoffice()
    if not lo_bin:
        raise RuntimeError(
            "LibreOffice is not installed. Cannot convert DOCX to PDF."
        )

    input_file = Path(input_path)
    output_file = Path(output_path)

    if not input_file.exists():
        raise RuntimeError(f"Input file not found: {input_path}")

    output_dir = output_file.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Converting DOCX → PDF: {input_file.name}")

    # LibreOffice writes the PDF in the same directory as input,
    # so we use a temp dir and then move to output_path.
    import tempfile

    with tempfile.TemporaryDirectory() as tmp_dir:
        cmd = [
            lo_bin,
            "--headless",
            "--norestore",
            "--nofirststartwizard",
            "--convert-to", "pdf",
            "--outdir", tmp_dir,
            str(input_file),
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,  # 2 minutes max
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

        # Find the generated PDF in tmp_dir
        generated = list(Path(tmp_dir).glob("*.pdf"))
        if not generated:
            raise RuntimeError("LibreOffice did not produce a PDF output")

        # Move to desired output path
        shutil.move(str(generated[0]), str(output_file))

    if not output_file.exists() or output_file.stat().st_size == 0:
        raise RuntimeError("Conversion produced an empty or missing PDF")

    logger.info(
        f"DOCX→PDF conversion complete: {output_file.stat().st_size} bytes"
    )
