"""
utils.py - The Helper Functions Layer (LangSmith-Traced)

This module provides utility functions for document processing.
All significant operations are traced with @traceable for LangSmith visibility.

Architecture:
- Vision-First: PDFs are converted to images, NOT text extracted
- Image optimization: Resize to max 1024px width to save tokens
- Multiple backends: PyMuPDF (recommended) or pdf2image (Poppler)
"""

import base64
import io
import logging
from pathlib import Path
from typing import List, Optional, Tuple

from langsmith import traceable

# Configure logging
logger = logging.getLogger(__name__)

# =============================================================================
# IMAGE CONFIGURATION
# =============================================================================

# Maximum image width for vision API (saves tokens without losing layout info)
MAX_IMAGE_WIDTH = 1024


@traceable(
    name="pdf_to_base64_images",
    tags=["preprocessing", "pdf", "vision"],
    metadata={"operation": "pdf_conversion"}
)
def pdf_to_base64_images(
    pdf_path: str,
    dpi: int = 200,
    max_pages: Optional[int] = None,
    image_format: str = "JPEG",
    max_width: int = MAX_IMAGE_WIDTH
) -> List[Tuple[str, str]]:
    """
    Convert PDF pages to base64-encoded images for vision model processing.
    
    VISION-FIRST ARCHITECTURE:
    Financial statements rely heavily on visual layout:
    - Indentation indicates hierarchy (COGS vs OpEx)
    - Column alignment maps values to periods
    - Section headers define logical groupings
    - Bold/formatting indicates totals vs line items
    
    Text extraction (pypdf, pdfminer) LOSES this critical context.
    Vision models can "see" and interpret the layout directly.
    
    COST OPTIMIZATION:
    Images are resized to max_width (default 1024px) before encoding.
    This saves ~70% of tokens without losing layout information.
    
    Args:
        pdf_path: Path to the PDF file
        dpi: Resolution for rendering (200 is good balance)
        max_pages: Maximum pages to process (None = all)
        image_format: Output format ('JPEG' recommended for smaller size)
        max_width: Maximum image width in pixels (default: 1024)
        
    Returns:
        List of tuples: (base64_encoded_image, media_type)
    """
    # Validate input path
    pdf_file = Path(pdf_path)
    if not pdf_file.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    
    if not pdf_file.suffix.lower() == ".pdf":
        raise ValueError(f"File is not a PDF: {pdf_path}")
    
    # Try PyMuPDF first (no external dependencies)
    try:
        return _pdf_to_images_pymupdf(pdf_path, dpi, max_pages, image_format, max_width)
    except ImportError:
        logger.info("PyMuPDF not available, trying pdf2image...")
    
    # Fallback to pdf2image (requires Poppler)
    try:
        return _pdf_to_images_pdf2image(pdf_path, dpi, max_pages, image_format, max_width)
    except ImportError as e:
        raise ImportError(
            "No PDF library available. Install one of:\n"
            "  pip install pymupdf  (recommended, no external deps)\n"
            "  pip install pdf2image  (requires Poppler)\n\n"
            "For pdf2image, also install Poppler:\n"
            "  Mac: brew install poppler\n"
            "  Windows: Download from https://github.com/oschwartz10612/poppler-windows/releases\n"
            "  Linux: apt-get install poppler-utils"
        ) from e


def _resize_image_if_needed(img, max_width: int):
    """
    Resize PIL Image if width exceeds max_width, maintaining aspect ratio.
    
    Args:
        img: PIL Image object
        max_width: Maximum allowed width
        
    Returns:
        Resized PIL Image (or original if no resize needed)
    """
    from PIL import Image
    
    width, height = img.size
    
    if width <= max_width:
        return img
    
    # Calculate new dimensions maintaining aspect ratio
    ratio = max_width / width
    new_height = int(height * ratio)
    
    logger.debug(f"Resizing image from {width}x{height} to {max_width}x{new_height}")
    
    # Use LANCZOS for high-quality downsampling
    return img.resize((max_width, new_height), Image.LANCZOS)


def _pdf_to_images_pymupdf(
    pdf_path: str,
    dpi: int,
    max_pages: Optional[int],
    image_format: str,
    max_width: int
) -> List[Tuple[str, str]]:
    """Convert PDF to images using PyMuPDF (no external dependencies)."""
    import fitz  # PyMuPDF
    from PIL import Image
    
    logger.info(f"Converting PDF to images (PyMuPDF): {pdf_path} (DPI={dpi})")
    
    doc = fitz.open(pdf_path)
    
    if not doc.page_count:
        raise ValueError(f"PDF appears to be empty: {pdf_path}")
    
    # Calculate zoom for desired DPI (PyMuPDF default is 72 DPI)
    zoom = dpi / 72.0
    matrix = fitz.Matrix(zoom, zoom)
    
    base64_images = []
    
    # Determine media type
    fmt_lower = image_format.lower()
    if fmt_lower in ("jpg", "jpeg"):
        media_type = "image/jpeg"
        pil_format = "JPEG"
    else:
        media_type = f"image/{fmt_lower}"
        pil_format = image_format.upper()
    
    pages_to_process = min(doc.page_count, max_pages) if max_pages else doc.page_count
    
    for page_num in range(pages_to_process):
        page = doc[page_num]
        pix = page.get_pixmap(matrix=matrix)
        
        # Convert to PIL Image for resizing
        img_data = pix.tobytes("png")
        img = Image.open(io.BytesIO(img_data))
        
        # Convert to RGB if necessary (JPEG doesn't support RGBA)
        if pil_format == "JPEG" and img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        
        # Resize if needed
        img = _resize_image_if_needed(img, max_width)
        
        # Encode to base64
        buffer = io.BytesIO()
        img.save(buffer, format=pil_format, quality=85 if pil_format == "JPEG" else None)
        buffer.seek(0)
        
        img_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
        base64_images.append((img_base64, media_type))
        
        logger.debug(f"Page {page_num+1}: {len(img_base64)} bytes (base64), size: {img.size}")
    
    doc.close()
    logger.info(f"Converted {len(base64_images)} pages from PDF (max_width={max_width})")
    
    return base64_images


def _pdf_to_images_pdf2image(
    pdf_path: str,
    dpi: int,
    max_pages: Optional[int],
    image_format: str,
    max_width: int
) -> List[Tuple[str, str]]:
    """Convert PDF to images using pdf2image (requires Poppler)."""
    from pdf2image import convert_from_path
    from PIL import Image
    
    logger.info(f"Converting PDF to images (pdf2image): {pdf_path} (DPI={dpi})")
    
    try:
        images = convert_from_path(
            pdf_path,
            dpi=dpi,
            fmt=image_format.lower(),
            first_page=1,
            last_page=max_pages if max_pages else None
        )
    except Exception as e:
        if "poppler" in str(e).lower() or "pdftoppm" in str(e).lower():
            raise ImportError(
                "Poppler not found. Please install it:\n"
                "  Mac: brew install poppler\n"
                "  Windows: Download from https://github.com/oschwartz10612/poppler-windows/releases\n"
                "  Linux: apt-get install poppler-utils"
            ) from e
        raise ValueError(f"Failed to convert PDF: {e}") from e
    
    if not images:
        raise ValueError(f"PDF appears to be empty: {pdf_path}")
    
    logger.info(f"Converted {len(images)} pages from PDF")
    
    base64_images = []
    
    # Determine format and media type
    fmt_lower = image_format.lower()
    if fmt_lower in ("jpg", "jpeg"):
        media_type = "image/jpeg"
        pil_format = "JPEG"
    else:
        media_type = f"image/{fmt_lower}"
        pil_format = image_format.upper()
    
    for i, img in enumerate(images):
        # Convert to RGB if necessary (JPEG doesn't support RGBA)
        if pil_format == "JPEG" and img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        
        # Resize if needed
        img = _resize_image_if_needed(img, max_width)
        
        # Encode to base64
        buffer = io.BytesIO()
        img.save(buffer, format=pil_format, quality=85 if pil_format == "JPEG" else None)
        buffer.seek(0)
        
        img_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
        base64_images.append((img_base64, media_type))
        
        logger.debug(f"Page {i+1}: {len(img_base64)} bytes (base64), size: {img.size}")
    
    logger.info(f"Converted {len(base64_images)} pages (max_width={max_width})")
    
    return base64_images


def create_image_content_block(base64_image: str, media_type: str) -> dict:
    """
    Create an image content block for LangChain/OpenAI Vision API format.
    
    Args:
        base64_image: Base64-encoded image string
        media_type: MIME type (e.g., "image/jpeg")
        
    Returns:
        Dict in OpenAI Vision API format
    """
    return {
        "type": "image_url",
        "image_url": {
            "url": f"data:{media_type};base64,{base64_image}",
            "detail": "high"
        }
    }


def create_vision_message_content(
    text_prompt: str,
    base64_images: List[Tuple[str, str]]
) -> List[dict]:
    """
    Create a complete vision message content list with text and images.
    
    This constructs the proper format for OpenAI Vision API:
    [
        {"type": "text", "text": "..."},
        {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,..."}},
        ...
    ]
    
    Args:
        text_prompt: The text instruction to include
        base64_images: List of (base64_string, media_type) tuples
        
    Returns:
        List of content blocks ready for HumanMessage
    """
    content = [{"type": "text", "text": text_prompt}]
    
    for base64_img, media_type in base64_images:
        content.append(create_image_content_block(base64_img, media_type))
    
    return content


@traceable(
    name="excel_to_markdown",
    tags=["preprocessing", "excel"],
    metadata={"operation": "excel_conversion"}
)
def excel_to_markdown(
    excel_path: str,
    sheet_name: Optional[str] = None,
    max_rows: Optional[int] = None
) -> str:
    """
    Convert Excel file to Markdown table format.
    
    Args:
        excel_path: Path to the Excel file
        sheet_name: Specific sheet to convert (None = first)
        max_rows: Maximum rows to include (None = all)
        
    Returns:
        Markdown-formatted table string
    """
    excel_file = Path(excel_path)
    if not excel_file.exists():
        raise FileNotFoundError(f"Excel file not found: {excel_path}")
    
    valid_extensions = {".xlsx", ".xls", ".xlsm"}
    if excel_file.suffix.lower() not in valid_extensions:
        raise ValueError(
            f"Invalid Excel file extension: {excel_file.suffix}. "
            f"Expected one of: {valid_extensions}"
        )
    
    try:
        import pandas as pd
    except ImportError as e:
        raise ImportError(
            "pandas is required for Excel processing. "
            "Install with: pip install pandas openpyxl"
        ) from e
    
    logger.info(f"Converting Excel to Markdown: {excel_path}")
    
    try:
        df = pd.read_excel(
            excel_path,
            sheet_name=sheet_name if sheet_name else 0,
            nrows=max_rows
        )
    except Exception as e:
        raise ValueError(f"Failed to read Excel file: {e}") from e
    
    markdown = df.to_markdown(index=False)
    logger.info(f"Converted {len(df)} rows to Markdown")
    
    return markdown


def validate_file_path(file_path: str, allowed_extensions: List[str]) -> Path:
    """
    Validate that a file exists and has an allowed extension.
    """
    path = Path(file_path)
    
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    if not path.is_file():
        raise ValueError(f"Path is not a file: {file_path}")
    
    normalized_ext = path.suffix.lower()
    allowed_normalized = [ext.lower() for ext in allowed_extensions]
    
    if normalized_ext not in allowed_normalized:
        raise ValueError(
            f"Invalid file type: {normalized_ext}. "
            f"Allowed types: {allowed_extensions}"
        )
    
    return path


def estimate_token_count(base64_images: List[Tuple[str, str]]) -> int:
    """
    Estimate token usage for vision API calls.
    
    Note: With max_width=1024, images are smaller and token usage is reduced.
    At 1024px width, typical financial statement page uses ~1000-1500 tokens.
    """
    # OpenAI vision: ~85 tokens base + ~170 per 512x512 tile
    # At 1024px width, US Letter ~1024x1300px → ~6 tiles
    TOKENS_PER_PAGE_ESTIMATE = 85 + (6 * 170)  # ~1105 per page
    return len(base64_images) * TOKENS_PER_PAGE_ESTIMATE


def format_currency(value: Optional[float], scale: str = "units") -> str:
    """
    Format a numerical value as currency string.
    """
    if value is None:
        return "N/A"
    
    multipliers = {
        "units": 1,
        "thousands": 1_000,
        "millions": 1_000_000,
        "billions": 1_000_000_000
    }
    
    multiplier = multipliers.get(scale.lower(), 1)
    actual_value = value * multiplier
    
    if actual_value >= 0:
        return f"${actual_value:,.2f}"
    else:
        return f"(${abs(actual_value):,.2f})"
