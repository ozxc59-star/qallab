from pydantic import BaseModel
from enum import Enum


class ConversionType(str, Enum):
    pdf_to_docx = "pdf-to-docx"
    docx_to_pdf = "docx-to-pdf"


class ConversionRequest(BaseModel):
    job_id: str
    conversion_type: ConversionType
    input_key: str   # R2 key where input file is stored
    output_key: str  # R2 key where output should be stored


class ConversionResult(BaseModel):
    job_id: str
    success: bool
    output_key: str | None = None
    error: str | None = None


class HealthResponse(BaseModel):
    status: str
    libreoffice_available: bool
