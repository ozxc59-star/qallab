"""
قلّب Converter Service — FastAPI microservice for PDF↔DOCX conversion.

Authentication: X-API-Key header (never exposed to browser).
All file I/O goes through Cloudflare R2.
"""

import logging
import os
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path

import magic
from fastapi import FastAPI, Header, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse

from converters.pdf_to_docx import convert_pdf_to_docx
from converters.docx_to_pdf import convert_docx_to_pdf, is_libreoffice_available
from storage.r2_client import download_from_r2, upload_to_r2
from models import ConversionResult, HealthResponse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

API_KEY = os.environ.get("CONVERTER_API_KEY", "")

# Magic bytes for validation
MAGIC_BYTES = {
    "pdf": b"%PDF",
    "docx": b"PK\x03\x04",  # ZIP-based (DOCX is a ZIP)
    "doc": b"\xd0\xcf\x11\xe0",  # OLE Compound Document
}

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
}

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("قلّب Converter Service starting up")
    logger.info(f"LibreOffice available: {is_libreoffice_available()}")
    yield
    logger.info("قلّب Converter Service shutting down")


app = FastAPI(
    title="قلّب Converter Service",
    description="Internal PDF↔DOCX conversion service",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None,  # Disable public docs
    redoc_url=None,
)


def verify_api_key(x_api_key: str | None) -> None:
    if not API_KEY:
        raise HTTPException(status_code=500, detail="API key not configured")
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")


def validate_file_magic_bytes(data: bytes, expected_type: str) -> bool:
    """Validate file using magic bytes, not just extension."""
    magic_signature = MAGIC_BYTES.get(expected_type, b"")
    return data[: len(magic_signature)] == magic_signature


def detect_file_type(data: bytes) -> str | None:
    """Detect file type from magic bytes."""
    for file_type, signature in MAGIC_BYTES.items():
        if data[: len(signature)] == signature:
            return file_type
    return None


@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(
        status="ok",
        libreoffice_available=is_libreoffice_available(),
    )


@app.post("/convert", response_model=ConversionResult)
async def convert(
    job_id: str = Form(...),
    conversion_type: str = Form(...),
    file: UploadFile = File(...),
    x_api_key: str | None = Header(None, alias="X-API-Key"),
):
    """
    Convert a PDF to DOCX or DOCX to PDF.

    - Validates API key
    - Validates file size and magic bytes
    - Converts the file
    - Uploads result to R2
    - Returns the R2 output key
    """
    verify_api_key(x_api_key)

    if conversion_type not in ("pdf-to-docx", "docx-to-pdf"):
        raise HTTPException(status_code=400, detail="Invalid conversion_type")

    # Read file content
    content = await file.read()

    # Size check
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large (max 10 MB)")

    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Empty file")

    # Magic byte validation
    detected_type = detect_file_type(content)

    if conversion_type == "pdf-to-docx" and detected_type != "pdf":
        raise HTTPException(
            status_code=400, detail="File does not appear to be a valid PDF"
        )

    if conversion_type == "docx-to-pdf" and detected_type not in ("docx", "doc"):
        raise HTTPException(
            status_code=400,
            detail="File does not appear to be a valid Word document",
        )

    # Determine extensions
    if conversion_type == "pdf-to-docx":
        input_ext = ".pdf"
        output_ext = ".docx"
        output_content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    else:
        input_ext = ".docx" if detected_type == "docx" else ".doc"
        output_ext = ".pdf"
        output_content_type = "application/pdf"

    output_key = f"outputs/{job_id}{output_ext}"

    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            input_path = str(Path(tmp_dir) / f"input{input_ext}")
            output_path = str(Path(tmp_dir) / f"output{output_ext}")

            # Write input file
            with open(input_path, "wb") as f:
                f.write(content)

            # Convert
            if conversion_type == "pdf-to-docx":
                convert_pdf_to_docx(input_path, output_path)
            else:
                convert_docx_to_pdf(input_path, output_path)

            # Upload result to R2
            upload_to_r2(output_path, output_key, output_content_type)

    except RuntimeError as e:
        logger.error(f"Conversion failed for job {job_id}: {e}")
        return ConversionResult(
            job_id=job_id,
            success=False,
            error=str(e),
        )
    except Exception as e:
        logger.exception(f"Unexpected error for job {job_id}")
        return ConversionResult(
            job_id=job_id,
            success=False,
            error="unexpected_error",
        )

    logger.info(f"Job {job_id} completed: {output_key}")
    return ConversionResult(
        job_id=job_id,
        success=True,
        output_key=output_key,
    )
