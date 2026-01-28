"""
FastAPI Backend for Financial Statement Spreader

This module provides REST API endpoints for uploading and processing
financial statement PDFs, integrating with the existing spreader.py engine.
"""

import os
import logging
import uuid
import traceback
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
from collections import deque

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Import existing spreader functionality
import sys
sys.path.append(str(Path(__file__).parent.parent))

from spreader import spread_financials, spread_pdf, spread_pdf_combined, reset_fallback_flag, was_fallback_used
from models import IncomeStatement, BalanceSheet, CombinedFinancialExtraction

# Import testing module
try:
    from backend.testing.test_runner import (
        run_test, get_test_history, get_test_result_by_id,
        get_test_companies, get_available_models, get_current_prompt_content,
        load_answer_key, save_answer_key
    )
    from backend.testing.test_models import (
        TestRunConfig, TestRunResult, TestHistoryResponse,
        TestingStatusResponse, CompanyAnswerKey
    )
    TESTING_ENABLED = True
except ImportError:
    # Try relative import for when running from backend directory
    try:
        from testing.test_runner import (
            run_test, get_test_history, get_test_result_by_id,
            get_test_companies, get_available_models, get_current_prompt_content,
            load_answer_key, save_answer_key
        )
        from testing.test_models import (
            TestRunConfig, TestRunResult, TestHistoryResponse,
            TestingStatusResponse, CompanyAnswerKey
        )
        TESTING_ENABLED = True
    except ImportError as e:
        logger.warning(f"Testing module not available: {e}")
        TESTING_ENABLED = False

# Configure logging with custom handler for WebSocket broadcasting
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Bridge Financial Spreader API",
    description="API for spreading financial statements from PDFs",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],  # Vite default port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create uploads directory if it doesn't exist
UPLOAD_DIR = Path(__file__).resolve().parent / "uploads"
try:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
except Exception as e:
    logger.warning(f"Could not create uploads directory: {e}. Using temp directory.")
    import tempfile
    UPLOAD_DIR = Path(tempfile.gettempdir()) / "bridge_financial_spreader_uploads"
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Define example financials directory
EXAMPLE_FINANCIALS_DIR = Path(__file__).resolve().parent.parent / "example_financials"

# Store for active WebSocket connections
active_connections: list[WebSocket] = []

# In-memory log buffer for debugging (keeps last 1000 logs)
log_buffer: deque = deque(maxlen=1000)


# =============================================================================
# LOG ENTRY MODEL
# =============================================================================

class LogEntry(BaseModel):
    """Structured log entry for debugging"""
    id: str
    timestamp: str
    level: str
    message: str
    source: Optional[str] = None
    job_id: Optional[str] = None
    filename: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    stack_trace: Optional[str] = None


class ProcessingStep(BaseModel):
    """Processing pipeline step"""
    id: str
    name: str
    status: str  # pending, running, completed, failed
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    duration: Optional[int] = None
    details: Optional[Dict[str, Any]] = None


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class SpreadRequest(BaseModel):
    """Request model for spreading operation"""
    doc_type: str
    period: str = "Latest"
    max_pages: Optional[int] = None
    dpi: int = 200


class SpreadResponse(BaseModel):
    """Response model for spreading operation"""
    success: bool
    job_id: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = {}


class BatchFileResult(BaseModel):
    """Result for a single file in batch processing"""
    filename: str
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    job_id: Optional[str] = None


class BatchSpreadResponse(BaseModel):
    """Response model for batch spreading operation"""
    batch_id: str
    total_files: int
    completed: int
    failed: int
    results: List[BatchFileResult]


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    version: str
    timestamp: str


# =============================================================================
# LOGGING HELPER FUNCTIONS
# =============================================================================

def create_log_entry(
    level: str,
    message: str,
    source: Optional[str] = None,
    job_id: Optional[str] = None,
    filename: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    stack_trace: Optional[str] = None
) -> LogEntry:
    """Create a structured log entry"""
    entry = LogEntry(
        id=str(uuid.uuid4()),
        timestamp=datetime.utcnow().isoformat() + "Z",
        level=level,
        message=message,
        source=source,
        job_id=job_id,
        filename=filename,
        details=details,
        stack_trace=stack_trace
    )
    log_buffer.append(entry.model_dump())
    return entry


async def emit_log(
    level: str,
    message: str,
    source: Optional[str] = None,
    job_id: Optional[str] = None,
    filename: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    stack_trace: Optional[str] = None
):
    """Emit a log entry to all connected WebSocket clients"""
    entry = create_log_entry(level, message, source, job_id, filename, details, stack_trace)
    
    # Also log to console
    log_func = getattr(logger, level, logger.info)
    log_func(f"[{job_id or 'system'}] {message}")
    
    # Broadcast to WebSocket clients
    await broadcast_message({
        "type": "log",
        "job_id": job_id,
        "timestamp": entry.timestamp,
        "payload": entry.model_dump()
    })


async def emit_step(
    job_id: str,
    step_id: str,
    name: str,
    status: str,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    duration: Optional[int] = None,
    details: Optional[Dict[str, Any]] = None
):
    """Emit a processing step update"""
    step = ProcessingStep(
        id=step_id,
        name=name,
        status=status,
        start_time=start_time,
        end_time=end_time,
        duration=duration,
        details=details
    )
    
    await broadcast_message({
        "type": "step",
        "job_id": job_id,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "payload": step.model_dump()
    })


# =============================================================================
# API ENDPOINTS
# =============================================================================

@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        timestamp=datetime.utcnow().isoformat()
    )


@app.get("/api/logs")
async def get_logs(limit: int = 100):
    """Get recent logs from buffer"""
    logs = list(log_buffer)[-limit:]
    return {"logs": logs}


@app.post("/api/spread", response_model=SpreadResponse)
async def spread_financial_statement(
    file: UploadFile = File(...),
    doc_type: str = Form("auto"),
    period: str = Form("Latest"),
    max_pages: Optional[int] = Form(None),
    dpi: int = Form(200),
    model_override: Optional[str] = Form(None),
    extended_thinking: bool = Form(False)
):
    """
    Upload and process a financial statement PDF.
    
    Prompts are loaded from LangSmith Hub. If Hub is unavailable,
    the request will fail with a clear error message.
    
    Args:
        file: PDF file upload
        doc_type: Type of document ('income', 'balance', or 'auto' for auto-detection)
        period: Fiscal period to extract
        max_pages: Maximum pages to process
        dpi: DPI for PDF image conversion
        model_override: Optional model override (e.g., 'gpt-5', 'gpt-4o')
        extended_thinking: Enable extended thinking for Anthropic models (default False)
        
    Returns:
        SpreadResponse with extracted financial data
        - For doc_type='auto': Returns combined results with income_statement and/or balance_sheet
        - For specific doc_type: Returns single statement type with periods
    """
    job_id = str(uuid.uuid4())
    filename = file.filename or "unknown.pdf"
    
    await emit_log("info", f"Starting single file processing", "api", job_id, filename)
    
    # Validate file type
    if not filename.endswith('.pdf'):
        await emit_log("error", "Invalid file type - only PDF files are supported", "api", job_id, filename)
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported"
        )
    
    # Validate doc_type - now supports 'auto'
    if doc_type not in ['income', 'balance', 'auto']:
        await emit_log("error", f"Invalid doc_type: {doc_type}", "api", job_id, filename)
        raise HTTPException(
            status_code=400,
            detail="doc_type must be 'income', 'balance', or 'auto'"
        )
    
    try:
        # Step 1: Save file
        await emit_step(job_id, "save", "Saving File", "running", datetime.utcnow().isoformat())
        file_path = UPLOAD_DIR / f"{job_id}_{filename}"
        
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        await emit_log("info", f"File saved: {file_path.name}", "api", job_id, filename, {
            "size_bytes": len(content),
            "path": str(file_path)
        })
        await emit_step(job_id, "save", "Saving File", "completed", end_time=datetime.utcnow().isoformat())
        
        # Step 2: Process PDF
        await emit_step(job_id, "process", "Processing PDF", "running", datetime.utcnow().isoformat())
        
        # Reset fallback flag before processing
        reset_fallback_flag()
        
        is_auto_mode = doc_type == "auto"
        await emit_log("info", f"Starting PDF processing with doc_type={doc_type}", "spreader", job_id, filename, {
            "doc_type": doc_type,
            "period": period,
            "max_pages": max_pages,
            "dpi": dpi,
            "model_override": model_override,
            "prompt_source": "langsmith_hub",
            "auto_detect_mode": is_auto_mode
        })
        
        # Broadcast progress via WebSocket
        if is_auto_mode:
            await broadcast_progress(job_id, "processing", "Detecting statement types and processing PDF...")
        else:
            await broadcast_progress(job_id, "processing", "Processing PDF...")
        
        # Process the file using vision-first spreader with reasoning loop
        # Prompts are loaded from LangSmith Hub (fail-fast if unavailable)
        if is_auto_mode:
            # Use async combined extraction with auto-detection
            result = await spread_pdf_combined(
                pdf_path=str(file_path),
                max_pages=max_pages,
                dpi=dpi,
                model_override=model_override,
                extended_thinking=extended_thinking
            )
        else:
            # Enable multi-period mode to extract all periods in the document
            result = spread_financials(
                file_path=str(file_path),
                doc_type=doc_type,
                period=period,
                multi_period=True,  # Extract all periods for side-by-side comparison
                max_pages=max_pages,
                dpi=dpi,
                model_override=model_override,
                extended_thinking=extended_thinking
            )
        
        await emit_step(job_id, "process", "Processing PDF", "completed", end_time=datetime.utcnow().isoformat())
        
        # Check if fallback prompt was used
        fallback_used = was_fallback_used()
        if fallback_used:
            logger.warning(f"[FALLBACK WARNING] Fallback prompt was used for {filename}")
        
        # Step 3: Extract metadata
        await emit_step(job_id, "metadata", "Extracting Metadata", "running", datetime.utcnow().isoformat())
        
        # Convert Pydantic model to dict
        result_data = result.model_dump()
        
        # Calculate summary statistics
        metadata = calculate_extraction_metadata(result_data)
        metadata["original_filename"] = filename
        metadata["job_id"] = job_id
        metadata["pdf_url"] = f"/api/files/{job_id}_{filename}"
        metadata["doc_type"] = doc_type
        metadata["fallback_prompt_used"] = fallback_used
        
        # Add auto-detection specific metadata
        if is_auto_mode and isinstance(result, CombinedFinancialExtraction):
            metadata["is_combined"] = True
            metadata["detected_income_statement"] = result.detected_types.has_income_statement
            metadata["detected_balance_sheet"] = result.detected_types.has_balance_sheet
            metadata["statement_types_extracted"] = result.statement_types_extracted
            if result.extraction_metadata:
                metadata["execution_time_seconds"] = result.extraction_metadata.get("execution_time_seconds")
                metadata["parallel_extraction"] = result.extraction_metadata.get("parallel_extraction", False)
        
        await emit_log("info", "Extraction complete", "spreader", job_id, filename, {
            "total_fields": metadata.get("total_fields"),
            "high_confidence": metadata.get("high_confidence"),
            "extraction_rate": metadata.get("extraction_rate"),
            "is_combined": metadata.get("is_combined", False)
        })
        await emit_step(job_id, "metadata", "Extracting Metadata", "completed", end_time=datetime.utcnow().isoformat())
        
        # Broadcast completion
        await broadcast_progress(job_id, "completed", "Processing complete!")
        await emit_log("info", "Processing completed successfully", "api", job_id, filename)
        
        return SpreadResponse(
            success=True,
            job_id=job_id,
            data=result_data,
            metadata=metadata
        )
        
    except Exception as e:
        error_trace = traceback.format_exc()
        await emit_log("error", f"Processing failed: {str(e)}", "spreader", job_id, filename, 
                      {"error_type": type(e).__name__}, error_trace)
        await emit_step(job_id, "process", "Processing PDF", "failed", end_time=datetime.utcnow().isoformat())
        
        # Broadcast error
        await broadcast_progress(job_id, "error", str(e))
        
        return SpreadResponse(
            success=False,
            job_id=job_id,
            error=str(e)
        )


async def _process_single_file(
    file_content: bytes,
    filename: str,
    doc_type: str,
    job_id: str,
    batch_id: str,
    idx: int,
    total_files: int,
    period: str,
    max_pages: Optional[int],
    dpi: int,
    model_override: Optional[str],
    extended_thinking: bool,
    semaphore: asyncio.Semaphore,
    progress_counter: dict,
    progress_lock: asyncio.Lock
) -> BatchFileResult:
    """
    Process a single file for batch processing.
    
    This helper function encapsulates the per-file logic for parallel execution.
    Uses a semaphore to limit concurrent extractions and respects API rate limits.
    
    Args:
        file_content: Raw bytes of the PDF file
        filename: Original filename
        doc_type: Document type ('income', 'balance', or 'auto')
        job_id: Unique job identifier
        batch_id: Batch identifier for progress tracking
        idx: File index in the batch
        total_files: Total number of files in batch
        period: Fiscal period to extract
        max_pages: Maximum pages to process
        dpi: DPI for PDF conversion
        model_override: Optional model override
        extended_thinking: Enable extended thinking for Anthropic models
        semaphore: Asyncio semaphore for concurrency control
        progress_counter: Shared dict for tracking progress {'completed': int}
        progress_lock: Lock for atomic progress updates
        
    Returns:
        BatchFileResult with processing outcome
    """
    async with semaphore:
        await emit_log("info", f"Processing file {idx + 1}/{total_files}: {filename}", "api", job_id, filename)
        
        # Validate file type
        if not filename.endswith('.pdf'):
            await emit_log("warning", f"Skipping non-PDF file: {filename}", "api", job_id, filename)
            return BatchFileResult(
                filename=filename,
                success=False,
                error="Only PDF files are supported",
                job_id=job_id
            )
        
        # Validate doc_type - now supports 'auto' for parallel IS+BS extraction
        if doc_type not in ['income', 'balance', 'auto']:
            await emit_log("warning", f"Invalid doc_type '{doc_type}' for {filename}", "api", job_id, filename)
            return BatchFileResult(
                filename=filename,
                success=False,
                error="doc_type must be 'income', 'balance', or 'auto'",
                job_id=job_id
            )
        
        try:
            # Save file
            file_path = UPLOAD_DIR / f"{job_id}_{filename}"
            
            with open(file_path, "wb") as buffer:
                buffer.write(file_content)
            
            await emit_log("debug", f"File saved: {file_path.name}", "api", job_id, filename)
            
            # Reset fallback flag before processing
            reset_fallback_flag()
            
            # Process based on doc_type
            is_auto_mode = doc_type == "auto"
            await emit_log("info", f"Processing {filename} as {doc_type}", "spreader", job_id, filename, {
                "auto_detect_mode": is_auto_mode
            })
            
            if is_auto_mode:
                # Use async combined extraction - extracts IS+BS in parallel within this file
                result = await spread_pdf_combined(
                    pdf_path=str(file_path),
                    max_pages=max_pages,
                    dpi=dpi,
                    model_override=model_override,
                    extended_thinking=extended_thinking
                )
            else:
                # Use asyncio.to_thread to run sync function without blocking
                result = await asyncio.to_thread(
                    spread_financials,
                    str(file_path),
                    doc_type,
                    period,
                    True,  # multi_period=True
                    max_pages=max_pages,
                    dpi=dpi,
                    model_override=model_override,
                    extended_thinking=extended_thinking
                )
            
            result_data = result.model_dump()
            metadata = calculate_extraction_metadata(result_data)
            metadata["original_filename"] = filename
            metadata["job_id"] = job_id
            metadata["pdf_url"] = f"/api/files/{job_id}_{filename}"
            metadata["doc_type"] = doc_type
            
            # Check if fallback prompt was used
            fallback_used = was_fallback_used()
            metadata["fallback_prompt_used"] = fallback_used
            if fallback_used:
                logger.warning(f"[FALLBACK WARNING] Fallback prompt was used for {filename}")
            
            # Add auto-detection specific metadata
            if is_auto_mode and isinstance(result, CombinedFinancialExtraction):
                metadata["is_combined"] = True
                metadata["detected_income_statement"] = result.detected_types.has_income_statement
                metadata["detected_balance_sheet"] = result.detected_types.has_balance_sheet
                metadata["statement_types_extracted"] = result.statement_types_extracted
                if result.extraction_metadata:
                    metadata["execution_time_seconds"] = result.extraction_metadata.get("execution_time_seconds")
                    metadata["parallel_extraction"] = result.extraction_metadata.get("parallel_extraction", False)
            
            await emit_log("info", f"Successfully processed {filename}", "spreader", job_id, filename, {
                "extraction_rate": metadata.get("extraction_rate"),
                "average_confidence": metadata.get("average_confidence"),
                "is_combined": metadata.get("is_combined", False)
            })
            
            batch_result = BatchFileResult(
                filename=filename,
                success=True,
                data=result_data,
                metadata=metadata,
                job_id=job_id
            )
            
        except Exception as e:
            error_trace = traceback.format_exc()
            await emit_log("error", f"Failed to process {filename}: {str(e)}", "spreader", job_id, filename,
                          {"error_type": type(e).__name__}, error_trace)
            
            batch_result = BatchFileResult(
                filename=filename,
                success=False,
                error=str(e),
                job_id=job_id
            )
        
        # Atomic progress update and broadcast
        async with progress_lock:
            progress_counter['completed'] += 1
            current = progress_counter['completed']
        
        await broadcast_message({
            "type": "progress",
            "job_id": batch_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "payload": {
                "current": current,
                "total": total_files,
                "filename": filename,
                "status": "success" if batch_result.success else "error"
            }
        })
        
        return batch_result


@app.post("/api/spread/batch", response_model=BatchSpreadResponse)
async def spread_batch(
    files: List[UploadFile] = File(...),
    doc_types: str = Form(...),  # JSON array string
    period: str = Form("Latest"),
    max_pages: Optional[int] = Form(None),
    dpi: int = Form(200),
    model_override: Optional[str] = Form(None),
    extended_thinking: bool = Form(False),
    parallel: bool = Form(True),
    max_concurrent: int = Form(4)
):
    """
    Upload and process multiple financial statement PDFs.
    
    Files can be processed in parallel for improved performance. When doc_type='auto'
    is used, each file also extracts both Income Statement and Balance Sheet in parallel.
    
    Prompts are loaded from LangSmith Hub. If Hub is unavailable,
    the request will fail with a clear error message.
    
    Args:
        files: List of PDF file uploads
        doc_types: JSON array of document types matching the files order
                   ('income', 'balance', or 'auto' for auto-detection)
        period: Fiscal period to extract
        max_pages: Maximum pages per file
        dpi: DPI for PDF conversion
        model_override: Optional model override (e.g., 'gpt-5', 'gpt-4o')
        extended_thinking: Enable extended thinking for Anthropic models (default False)
        parallel: If True (default), process files in parallel; if False, sequential
        max_concurrent: Maximum number of concurrent file extractions (default: 4)
        
    Returns:
        BatchSpreadResponse with results for each file
    """
    import json
    
    batch_id = str(uuid.uuid4())
    
    try:
        doc_type_list = json.loads(doc_types)
    except json.JSONDecodeError:
        await emit_log("error", "Invalid doc_types JSON format", "api", batch_id)
        raise HTTPException(status_code=400, detail="doc_types must be a valid JSON array")
    
    if len(doc_type_list) != len(files):
        await emit_log("error", f"Mismatch: {len(files)} files but {len(doc_type_list)} doc_types", "api", batch_id)
        raise HTTPException(
            status_code=400,
            detail=f"Number of doc_types ({len(doc_type_list)}) must match number of files ({len(files)})"
        )
    
    # Validate all doc_types upfront
    for idx, doc_type in enumerate(doc_type_list):
        if doc_type not in ['income', 'balance', 'auto']:
            await emit_log("error", f"Invalid doc_type '{doc_type}' at index {idx}", "api", batch_id)
            raise HTTPException(
                status_code=400,
                detail=f"Invalid doc_type '{doc_type}' at index {idx}. Must be 'income', 'balance', or 'auto'"
            )
    
    processing_mode = "parallel" if parallel else "sequential"
    await emit_log("info", f"Starting batch processing of {len(files)} files ({processing_mode})", "api", batch_id, details={
        "total_files": len(files),
        "filenames": [f.filename for f in files],
        "parallel": parallel,
        "max_concurrent": max_concurrent if parallel else 1,
        "doc_types": doc_type_list
    })
    
    # Pre-read all file contents (needed because UploadFile can only be read once)
    file_contents = []
    for file in files:
        content = await file.read()
        file_contents.append(content)
    
    if parallel:
        # PARALLEL PROCESSING: Use asyncio.gather with semaphore for concurrency control
        semaphore = asyncio.Semaphore(max_concurrent)
        progress_counter = {'completed': 0}
        progress_lock = asyncio.Lock()
        
        # Create tasks for all files
        tasks = []
        for idx, (file, content, doc_type) in enumerate(zip(files, file_contents, doc_type_list)):
            job_id = f"{batch_id}_{idx}"
            filename = file.filename or f"file_{idx}.pdf"
            
            task = _process_single_file(
                file_content=content,
                filename=filename,
                doc_type=doc_type,
                job_id=job_id,
                batch_id=batch_id,
                idx=idx,
                total_files=len(files),
                period=period,
                max_pages=max_pages,
                dpi=dpi,
                model_override=model_override,
                extended_thinking=extended_thinking,
                semaphore=semaphore,
                progress_counter=progress_counter,
                progress_lock=progress_lock
            )
            tasks.append(task)
        
        # Execute all tasks in parallel (with semaphore limiting concurrent extractions)
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results, handling any exceptions that were returned
        processed_results: List[BatchFileResult] = []
        for idx, result in enumerate(results):
            if isinstance(result, Exception):
                # Task raised an exception
                filename = files[idx].filename or f"file_{idx}.pdf"
                job_id = f"{batch_id}_{idx}"
                await emit_log("error", f"Task exception for {filename}: {str(result)}", "api", job_id, filename)
                processed_results.append(BatchFileResult(
                    filename=filename,
                    success=False,
                    error=str(result),
                    job_id=job_id
                ))
            else:
                processed_results.append(result)
        
        results = processed_results
        
    else:
        # SEQUENTIAL PROCESSING: Process files one at a time (original behavior)
        results: List[BatchFileResult] = []
        progress_counter = {'completed': 0}
        progress_lock = asyncio.Lock()
        semaphore = asyncio.Semaphore(1)  # Effectively sequential
        
        for idx, (file, content, doc_type) in enumerate(zip(files, file_contents, doc_type_list)):
            job_id = f"{batch_id}_{idx}"
            filename = file.filename or f"file_{idx}.pdf"
            
            result = await _process_single_file(
                file_content=content,
                filename=filename,
                doc_type=doc_type,
                job_id=job_id,
                batch_id=batch_id,
                idx=idx,
                total_files=len(files),
                period=period,
                max_pages=max_pages,
                dpi=dpi,
                model_override=model_override,
                extended_thinking=extended_thinking,
                semaphore=semaphore,
                progress_counter=progress_counter,
                progress_lock=progress_lock
            )
            results.append(result)
    
    # Calculate completion stats
    completed = sum(1 for r in results if r.success)
    failed = len(results) - completed
    
    await emit_log("info", f"Batch processing complete: {completed}/{len(files)} successful ({processing_mode})", "api", batch_id, details={
        "completed": completed,
        "failed": failed,
        "total": len(files),
        "parallel": parallel
    })
    
    return BatchSpreadResponse(
        batch_id=batch_id,
        total_files=len(files),
        completed=completed,
        failed=failed,
        results=results
    )


@app.get("/api/files/{filename}")
async def get_file(filename: str):
    """
    Serve uploaded PDF files.
    
    Args:
        filename: Name of the file to retrieve
        
    Returns:
        FileResponse with the PDF
    """
    file_path = UPLOAD_DIR / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        file_path,
        media_type="application/pdf",
        filename=filename
    )


@app.get("/api/testing/files/{filename}")
async def get_test_file(filename: str):
    """
    Serve example financial files for testing.
    """
    file_path = EXAMPLE_FINANCIALS_DIR / filename
    
    if not file_path.exists():
        # Fallback to uploads if not found in examples (in case it was uploaded manually)
        file_path = UPLOAD_DIR / filename
        if not file_path.exists():
             raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        file_path,
        media_type="application/pdf",
        filename=filename
    )


@app.websocket("/ws/progress")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time progress updates and log streaming.
    """
    await websocket.accept()
    active_connections.append(websocket)
    
    logger.info("[WEBSOCKET] Client connected")
    await emit_log("debug", "WebSocket client connected", "websocket")
    
    # Send recent logs on connect
    recent_logs = list(log_buffer)[-50:]
    logger.info(f"[WEBSOCKET] Sending {len(recent_logs)} recent logs to client")
    for log in recent_logs:
        try:
            await websocket.send_json({
                "type": "log",
                "job_id": log.get("job_id"),
                "timestamp": log.get("timestamp"),
                "payload": log
            })
        except Exception as e:
            logger.warning(f"[WEBSOCKET] Failed to send initial log: {e}")
            break
    
    try:
        while True:
            # Keep connection alive and handle client messages
            try:
                data = await websocket.receive_text()
                
                # Handle ping/pong
                if data == "ping":
                    await websocket.send_text("pong")
                    logger.debug("[WEBSOCKET] Ping/pong")
                    
            except RuntimeError as e:
                # WebSocket was closed/disconnected
                logger.info(f"[WEBSOCKET] Connection closed: {e}")
                break
            except Exception as e:
                logger.error(f"[WEBSOCKET] Error receiving message: {e}")
                break
                
    except WebSocketDisconnect:
        logger.info("[WEBSOCKET] Client disconnected normally")
    except Exception as e:
        logger.error(f"[WEBSOCKET] Unexpected error: {e}")
    finally:
        if websocket in active_connections:
            active_connections.remove(websocket)
            logger.info("[WEBSOCKET] Client removed from active connections")
        await emit_log("debug", "WebSocket client disconnected", "websocket")


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _count_fields_in_multi_period(data: Dict[str, Any]) -> tuple:
    """Helper to count fields in multi-period data structure."""
    high_confidence_count = 0
    medium_confidence_count = 0
    low_confidence_count = 0
    missing_count = 0
    total_fields = 0
    
    if "periods" in data and isinstance(data["periods"], list):
        for period in data["periods"]:
            period_data = period.get("data", {})
            for field_name, field_value in period_data.items():
                if isinstance(field_value, dict) and "value" in field_value:
                    total_fields += 1
                    
                    if field_value["value"] is None:
                        missing_count += 1
                    elif field_value["confidence"] >= 0.8:
                        high_confidence_count += 1
                    elif field_value["confidence"] >= 0.5:
                        medium_confidence_count += 1
                    else:
                        low_confidence_count += 1
    
    return high_confidence_count, medium_confidence_count, low_confidence_count, missing_count, total_fields


def calculate_extraction_metadata(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate metadata about the extraction quality.
    
    Supports single-period, multi-period, and combined data structures.
    
    Args:
        data: Extracted financial data (single, multi-period, or combined)
        
    Returns:
        Dictionary with metadata statistics
    """
    high_confidence_count = 0
    medium_confidence_count = 0
    low_confidence_count = 0
    missing_count = 0
    total_fields = 0
    
    # Check if this is combined extraction data (from auto-detect mode)
    if "income_statement" in data or "balance_sheet" in data:
        # Combined extraction: aggregate stats from both statement types
        for statement_key in ["income_statement", "balance_sheet"]:
            statement_data = data.get(statement_key)
            if statement_data and isinstance(statement_data, dict):
                h, m, l, miss, total = _count_fields_in_multi_period(statement_data)
                high_confidence_count += h
                medium_confidence_count += m
                low_confidence_count += l
                missing_count += miss
                total_fields += total
    
    # Check if this is multi-period data
    elif "periods" in data and isinstance(data["periods"], list):
        # Multi-period: aggregate stats across all periods
        h, m, l, miss, total = _count_fields_in_multi_period(data)
        high_confidence_count += h
        medium_confidence_count += m
        low_confidence_count += l
        missing_count += miss
        total_fields += total
    else:
        # Single-period: original logic
        for field_name, field_value in data.items():
            if isinstance(field_value, dict) and "value" in field_value:
                total_fields += 1
                
                if field_value["value"] is None:
                    missing_count += 1
                elif field_value["confidence"] >= 0.8:
                    high_confidence_count += 1
                elif field_value["confidence"] >= 0.5:
                    medium_confidence_count += 1
                else:
                    low_confidence_count += 1
    
    return {
        "total_fields": total_fields,
        "high_confidence": high_confidence_count,
        "medium_confidence": medium_confidence_count,
        "low_confidence": low_confidence_count,
        "missing": missing_count,
        "extraction_rate": (total_fields - missing_count) / total_fields if total_fields > 0 else 0,
        "average_confidence": calculate_average_confidence(data)
    }


def _collect_confidences_from_multi_period(data: Dict[str, Any]) -> List[float]:
    """Helper to collect confidence scores from multi-period data."""
    confidences = []
    if "periods" in data and isinstance(data["periods"], list):
        for period in data["periods"]:
            period_data = period.get("data", {})
            for field_value in period_data.values():
                if isinstance(field_value, dict) and "confidence" in field_value and "value" in field_value:
                    if field_value["value"] is not None:
                        confidences.append(field_value["confidence"])
    return confidences


def calculate_average_confidence(data: Dict[str, Any]) -> float:
    """Calculate average confidence score across all fields.
    
    Supports single-period, multi-period, and combined data structures.
    """
    confidences = []
    
    # Check if this is combined extraction data (from auto-detect mode)
    if "income_statement" in data or "balance_sheet" in data:
        # Combined extraction: aggregate confidences from both statement types
        for statement_key in ["income_statement", "balance_sheet"]:
            statement_data = data.get(statement_key)
            if statement_data and isinstance(statement_data, dict):
                confidences.extend(_collect_confidences_from_multi_period(statement_data))
    
    # Check if this is multi-period data
    elif "periods" in data and isinstance(data["periods"], list):
        confidences.extend(_collect_confidences_from_multi_period(data))
    else:
        # Single-period: original logic
        for field_value in data.values():
            if isinstance(field_value, dict) and "confidence" in field_value and "value" in field_value:
                if field_value["value"] is not None:
                    confidences.append(field_value["confidence"])
    
    return sum(confidences) / len(confidences) if confidences else 0.0


async def broadcast_message(message: dict):
    """Broadcast a message to all connected WebSocket clients."""
    disconnected = []
    
    for connection in active_connections:
        try:
            # Check if connection is still active before sending
            await connection.send_json(message)
        except RuntimeError as e:
            # WebSocket is closed or not connected
            logger.debug(f"[BROADCAST] WebSocket closed: {e}")
            disconnected.append(connection)
        except Exception as e:
            logger.error(f"[BROADCAST] Error sending to WebSocket: {e}")
            disconnected.append(connection)
    
    # Clean up disconnected connections
    for conn in disconnected:
        if conn in active_connections:
            active_connections.remove(conn)
            logger.info("[BROADCAST] Removed disconnected client")


async def broadcast_progress(job_id: str, status: str, message: str):
    """Broadcast progress updates to all connected WebSocket clients."""
    await broadcast_message({
        "type": "progress",
        "job_id": job_id,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "payload": {
            "status": status,
            "message": message
        }
    })


# =============================================================================
# STARTUP/SHUTDOWN EVENTS
# =============================================================================

# =============================================================================
# TESTING API ENDPOINTS
# =============================================================================

@app.get("/api/testing/status")
async def get_testing_status():
    """
    Get testing system status including available companies and models.
    """
    if not TESTING_ENABLED:
        raise HTTPException(status_code=503, detail="Testing module not available")
    
    try:
        companies = get_test_companies()
        models = get_available_models()
        
        # Try to get prompt content, but don't fail if LangSmith isn't configured
        prompt_content = None
        try:
            prompt_content = get_current_prompt_content("income")
        except Exception as prompt_err:
            logger.warning(f"Could not get prompt content: {prompt_err}")
        
        return TestingStatusResponse(
            available_companies=companies,
            available_models=models,
            current_prompt_content=prompt_content
        )
    except Exception as e:
        logger.error(f"Error getting testing status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/testing/run")
async def run_test_endpoint(config: dict):
    """
    Execute a test run for the specified company with the given configuration.
    
    This endpoint runs the spreader against all test files for the company,
    compares results to the answer key, and returns detailed grading.
    """
    if not TESTING_ENABLED:
        await emit_log("error", "Testing module not available", "testing")
        raise HTTPException(status_code=503, detail="Testing module not available")
    
    try:
        # Parse config
        test_config = TestRunConfig(**config)
        
        await emit_log("info", f"[TEST RUN START] Company: {test_config.company_id}, Model: {test_config.model_name}", 
                      "testing", details={
                          "company_id": test_config.company_id,
                          "model": test_config.model_name,
                          "dpi": test_config.dpi,
                          "max_pages": test_config.max_pages,
                          "tolerance": test_config.tolerance_percent,
                          "has_prompt_override": bool(test_config.prompt_override)
                      })
        
        await emit_log("info", "[TEST RUN] Calling run_test function...", "testing")
        
        result = await run_test(test_config)
        
        await emit_log("info", 
            f"[TEST RUN COMPLETE] Score: {result.overall_score:.1f}% ({result.overall_grade.value}), Files: {result.total_files}, Periods: {result.total_periods}, Time: {result.execution_time_seconds:.2f}s",
            "testing",
            job_id=result.id,
            details={
                "score": result.overall_score,
                "grade": result.overall_grade.value,
                "total_files": result.total_files,
                "total_periods": result.total_periods,
                "fields_correct": result.fields_correct,
                "fields_wrong": result.fields_wrong,
                "fields_missing": result.fields_missing,
                "execution_time": result.execution_time_seconds
            }
        )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        error_trace = traceback.format_exc()
        logger.error(f"[TEST RUN FAILED] {e}\n{error_trace}")
        await emit_log("error", f"[TEST RUN FAILED] {str(e)}", "testing", stack_trace=error_trace)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/testing/history")
async def get_testing_history(limit: int = 50, company_id: Optional[str] = None):
    """
    Get test run history.
    
    Args:
        limit: Maximum number of records to return
        company_id: Optional filter by company
    """
    if not TESTING_ENABLED:
        raise HTTPException(status_code=503, detail="Testing module not available")
    
    try:
        return get_test_history(limit=limit, company_id=company_id)
    except Exception as e:
        logger.error(f"Error getting test history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/testing/result/{test_id}")
async def get_test_result(test_id: str):
    """
    Get detailed results for a specific test run.
    """
    if not TESTING_ENABLED:
        raise HTTPException(status_code=503, detail="Testing module not available")
    
    try:
        result = get_test_result_by_id(test_id)
        if not result:
            raise HTTPException(status_code=404, detail="Test result not found")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting test result: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/testing/answer-key/{company_id}")
async def get_answer_key(company_id: str):
    """
    Get the answer key for a specific company.
    """
    if not TESTING_ENABLED:
        raise HTTPException(status_code=503, detail="Testing module not available")
    
    try:
        answer_key = load_answer_key(company_id)
        if not answer_key:
            raise HTTPException(status_code=404, detail="Answer key not found")
        return answer_key
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading answer key: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/testing/answer-key")
async def update_answer_key(answer_key: dict):
    """
    Update the answer key for a company.
    """
    if not TESTING_ENABLED:
        raise HTTPException(status_code=503, detail="Testing module not available")
    
    try:
        parsed_key = CompanyAnswerKey(**answer_key)
        save_answer_key(parsed_key)
        return {"success": True, "message": "Answer key saved"}
    except Exception as e:
        logger.error(f"Error saving answer key: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/testing/prompt/{doc_type}")
async def get_prompt_content(doc_type: str):
    """
    Get the current prompt content from LangSmith Hub.
    """
    if not TESTING_ENABLED:
        raise HTTPException(status_code=503, detail="Testing module not available")
    
    try:
        content = get_current_prompt_content(doc_type)
        return {"doc_type": doc_type, "content": content}
    except Exception as e:
        logger.error(f"Error getting prompt content: {e}")
        return {"doc_type": doc_type, "content": None, "error": str(e)}


# =============================================================================
# STARTUP/SHUTDOWN EVENTS
# =============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize on startup"""
    logger.info("Starting Bridge Financial Spreader API")
    logger.info(f"Upload directory: {UPLOAD_DIR}")
    
    # Check environment variables
    if not os.getenv("OPENAI_API_KEY"):
        logger.warning("OPENAI_API_KEY not set - spreading will fail!")
    
    if not os.getenv("LANGSMITH_API_KEY"):
        logger.warning("LANGSMITH_API_KEY not set - no tracing available")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down Bridge Financial Spreader API")
