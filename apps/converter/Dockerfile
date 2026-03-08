# قلّب Converter Service
# LibreOffice + Arabic fonts for accurate Arabic document conversion
# Build: 2026-03-09-v4

FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    # LibreOffice for all conversions (PDF↔DOCX) with proper Arabic support
    libreoffice \
    libreoffice-writer \
    libreoffice-draw \
    libreoffice-java-common \
    default-jre-headless \
    # Tesseract OCR for scanned/image-based Arabic PDFs
    tesseract-ocr \
    tesseract-ocr-ara \
    tesseract-ocr-eng \
    # Arabic fonts — critical for correct rendering
    fonts-hosny-amiri \
    fonts-arabeyes \
    fonts-noto-core \
    fonts-noto-extra \
    # Arabic locale support for proper RTL text shaping
    locales \
    # libmagic for file type validation
    libmagic1 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Generate Arabic and English locales
RUN echo "ar_AE.UTF-8 UTF-8" >> /etc/locale.gen && \
    echo "en_US.UTF-8 UTF-8" >> /etc/locale.gen && \
    locale-gen

# Refresh font cache
RUN fc-cache -f -v

# Create non-root user for security
RUN groupadd -r converter && useradd -r -g converter -d /app converter

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set ownership
RUN chown -R converter:converter /app

# Create temp directory for file processing
RUN mkdir -p /tmp/conversions && chown converter:converter /tmp/conversions

USER converter

# LibreOffice needs a home directory for profile
ENV HOME=/tmp/lo-home
RUN mkdir -p /tmp/lo-home

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health').raise_for_status()"

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
