"""
PDF → DOCX conversion using LibreOffice headless.

LibreOffice handles Arabic/RTL text, complex scripts, and mixed
bidirectional content correctly. Multiple conversion strategies are
tried in order to maximise compatibility across different environments.
"""

import logging
import os
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


def _run_lo(lo_bin: str, extra_args: list, input_file: Path, out_dir: Path) -> subprocess.CompletedProcess:
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
    logger.info(f"Running: {' '.join(cmd)}")
    return subprocess.run(cmd, capture_output=True, text=True, timeout=120, env=env)


def convert_pdf_to_docx(input_path: str, output_path: str) -> None:
    """
    Convert a PDF file to DOCX using LibreOffice headless.

    Tries multiple strategies in order:
    1. writer_pdf_import filter (best quality, needs libreoffice-pdfimport)
    2. Direct PDF open without filter (LibreOffice Draw fallback)
    3. PDF → ODT → DOCX two-step (most compatible)

    Args:
        input_path: Absolute path to the input PDF file.
        output_path: Absolute path where the output DOCX will be saved.

    Raises:
        RuntimeError: If all strategies fail.
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
        tmp_path = Path(tmp_dir)

        # ── Strategy 1: writer_pdf_import filter ──────────────────────────
        result = _run_lo(lo_bin, ["--infilter=writer_pdf_import", "--convert-to", "docx"],
                         input_file, tmp_path)
        docx_files = list(tmp_path.glob("*.docx"))
        if docx_files:
            shutil.move(str(docx_files[0]), str(output_file))
            logger.info(f"Strategy 1 (writer_pdf_import) succeeded: {output_file.stat().st_size} bytes")
            return

        logger.warning(f"Strategy 1 failed. rc={result.returncode} stdout={result.stdout!r} stderr={result.stderr!r}")

        # ── Strategy 2: direct convert without filter ─────────────────────
        result = _run_lo(lo_bin, ["--convert-to", "docx"],
                         input_file, tmp_path)
        docx_files = list(tmp_path.glob("*.docx"))
        if docx_files:
            shutil.move(str(docx_files[0]), str(output_file))
            logger.info(f"Strategy 2 (direct) succeeded: {output_file.stat().st_size} bytes")
            return

        logger.warning(f"Strategy 2 failed. rc={result.returncode} stdout={result.stdout!r} stderr={result.stderr!r}")

        # ── Strategy 3: PDF → ODT → DOCX two-step ────────────────────────
        odt_dir = tmp_path / "odt"
        odt_dir.mkdir()
        result = _run_lo(lo_bin, ["--convert-to", "odt"],
                         input_file, odt_dir)
        odt_files = list(odt_dir.glob("*.odt"))

        if odt_files:
            docx_dir = tmp_path / "docx"
            docx_dir.mkdir()
            result2 = _run_lo(lo_bin, ["--convert-to", "docx"],
                              odt_files[0], docx_dir)
            docx_files = list(docx_dir.glob("*.docx"))
            if docx_files:
                shutil.move(str(docx_files[0]), str(output_file))
                logger.info(f"Strategy 3 (ODT→DOCX) succeeded: {output_file.stat().st_size} bytes")
                return
            logger.warning(f"Strategy 3 step2 failed. rc={result2.returncode} stdout={result2.stdout!r} stderr={result2.stderr!r}")
        else:
            logger.warning(f"Strategy 3 step1 (ODT) failed. rc={result.returncode} stdout={result.stdout!r} stderr={result.stderr!r}")

        raise RuntimeError(
            "PDF→DOCX conversion failed with all strategies. "
            "The PDF may be encrypted, image-only (scanned), or corrupted."
        )
