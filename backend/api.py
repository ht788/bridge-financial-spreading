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

from spreader import spread_financials, spread_pdf
from models import IncomeStatement, BalanceSheet

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
    doc_type: str = Form(...),
    period: str = Form("Latest"),
    max_pages: Optional[int] = Form(None),
    dpi: int = Form(200)
):
    """
    Upload and process a financial statement PDF.
    
    Prompts are loaded from LangSmith Hub. If Hub is unavailable,
    the request will fail with a clear error message.
    
    Args:
        file: PDF file upload
        doc_type: Type of document ('income' or 'balance')
        period: Fiscal period to extract
        max_pages: Maximum pages to process
        dpi: DPI for PDF image conversion
        
    Returns:
        SpreadResponse with extracted financial data
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
    
    # Validate doc_type
    if doc_type not in ['income', 'balance']:
        await emit_log("error", f"Invalid doc_type: {doc_type}", "api", job_id, filename)
        raise HTTPException(
            status_code=400,
            detail="doc_type must be 'income' or 'balance'"
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
        await emit_log("info", f"Starting PDF processing with doc_type={doc_type}", "spreader", job_id, filename, {
            "doc_type": doc_type,
            "period": period,
            "max_pages": max_pages,
            "dpi": dpi,
            "prompt_source": "langsmith_hub"
        })
        
        # Broadcast progress via WebSocket
        await broadcast_progress(job_id, "processing", "Processing PDF...")
        
        # Process the file using vision-first spreader with reasoning loop
        # Prompts are loaded from LangSmith Hub (fail-fast if unavailable)
        # Enable multi-period mode to extract all periods in the document
        result = spread_financials(
            file_path=str(file_path),
            doc_type=doc_type,
            period=period,
            multi_period=True,  # Extract all periods for side-by-side comparison
            max_pages=max_pages,
            dpi=dpi
        )
        
        await emit_step(job_id, "process", "Processing PDF", "completed", end_time=datetime.utcnow().isoformat())
        
        # Step 3: Extract metadata
        await emit_step(job_id, "metadata", "Extracting Metadata", "running", datetime.utcnow().isoformat())
        
        # Convert Pydantic model to dict
        result_data = result.model_dump()
        
        # Calculate summary statistics
        metadata = calculate_extraction_metadata(result_data)
        metadata["original_filename"] = filename
        metadata["job_id"] = job_id
        metadata["pdf_url"] = f"/api/files/{job_id}_{filename}"
        
        await emit_log("info", "Extraction complete", "spreader", job_id, filename, {
            "total_fields": metadata.get("total_fields"),
            "high_confidence": metadata.get("high_confidence"),
            "extraction_rate": metadata.get("extraction_rate")
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


@app.post("/api/spread/batch", response_model=BatchSpreadResponse)
async def spread_batch(
    files: List[UploadFile] = File(...),
    doc_types: str = Form(...),  # JSON array string
    period: str = Form("Latest"),
    max_pages: Optional[int] = Form(None),
    dpi: int = Form(200)
):
    """
    Upload and process multiple financial statement PDFs.
    
    Prompts are loaded from LangSmith Hub. If Hub is unavailable,
    the request will fail with a clear error message.
    
    Args:
        files: List of PDF file uploads
        doc_types: JSON array of document types matching the files order
        period: Fiscal period to extract
        max_pages: Maximum pages per file
        dpi: DPI for PDF conversion
        
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
    
    await emit_log("info", f"Starting batch processing of {len(files)} files", "api", batch_id, details={
        "total_files": len(files),
        "filenames": [f.filename for f in files]
    })
    
    results: List[BatchFileResult] = []
    completed = 0
    failed = 0
    
    for idx, (file, doc_type) in enumerate(zip(files, doc_type_list)):
        job_id = f"{batch_id}_{idx}"
        filename = file.filename or f"file_{idx}.pdf"
        
        await emit_log("info", f"Processing file {idx + 1}/{len(files)}: {filename}", "api", job_id, filename)
        
        # Validate file type
        if not filename.endswith('.pdf'):
            await emit_log("warning", f"Skipping non-PDF file: {filename}", "api", job_id, filename)
            results.append(BatchFileResult(
                filename=filename,
                success=False,
                error="Only PDF files are supported",
                job_id=job_id
            ))
            failed += 1
            continue
        
        # Validate doc_type
        if doc_type not in ['income', 'balance']:
            await emit_log("warning", f"Invalid doc_type '{doc_type}' for {filename}", "api", job_id, filename)
            results.append(BatchFileResult(
                filename=filename,
                success=False,
                error="doc_type must be 'income' or 'balance'",
                job_id=job_id
            ))
            failed += 1
            continue
        
        try:
            # Save file
            file_path = UPLOAD_DIR / f"{job_id}_{filename}"
            content = await file.read()
            
            with open(file_path, "wb") as buffer:
                buffer.write(content)
            
            await emit_log("debug", f"File saved: {file_path.name}", "api", job_id, filename)
            
            # Process
            await emit_log("info", f"Processing {filename} as {doc_type}", "spreader", job_id, filename)
            
            # Enable multi-period mode to extract all periods in the document
            result = spread_financials(
                file_path=str(file_path),
                doc_type=doc_type,
                period=period,
                multi_period=True,  # Extract all periods for side-by-side comparison
                max_pages=max_pages,
                dpi=dpi
            )
            
            result_data = result.model_dump()
            metadata = calculate_extraction_metadata(result_data)
            metadata["original_filename"] = filename
            metadata["job_id"] = job_id
            metadata["pdf_url"] = f"/api/files/{job_id}_{filename}"
            
            await emit_log("info", f"Successfully processed {filename}", "spreader", job_id, filename, {
                "extraction_rate": metadata.get("extraction_rate"),
                "average_confidence": metadata.get("average_confidence")
            })
            
            results.append(BatchFileResult(
                filename=filename,
                success=True,
                data=result_data,
                metadata=metadata,
                job_id=job_id
            ))
            completed += 1
            
        except Exception as e:
            error_trace = traceback.format_exc()
            await emit_log("error", f"Failed to process {filename}: {str(e)}", "spreader", job_id, filename,
                          {"error_type": type(e).__name__}, error_trace)
            
            results.append(BatchFileResult(
                filename=filename,
                success=False,
                error=str(e),
                job_id=job_id
            ))
            failed += 1
        
        # Broadcast progress
        await broadcast_message({
            "type": "progress",
            "job_id": batch_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "payload": {
                "current": idx + 1,
                "total": len(files),
                "filename": filename,
                "status": "success" if results[-1].success else "error"
            }
        })
    
    await emit_log("info", f"Batch processing complete: {completed}/{len(files)} successful", "api", batch_id, details={
        "completed": completed,
        "failed": failed,
        "total": len(files)
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


@app.websocket("/ws/progress")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time progress updates and log streaming.
    """
    await websocket.accept()
    active_connections.append(websocket)
    
    await emit_log("debug", "WebSocket client connected", "websocket")
    
    # Send recent logs on connect
    recent_logs = list(log_buffer)[-50:]
    for log in recent_logs:
        try:
            await websocket.send_json({
                "type": "log",
                "job_id": log.get("job_id"),
                "timestamp": log.get("timestamp"),
                "payload": log
            })
        except Exception:
            pass
    
    try:
        while True:
            # Keep connection alive and handle client messages
            data = await websocket.receive_text()
            
            # Handle ping/pong
            if data == "ping":
                await websocket.send_text("pong")
                
    except WebSocketDisconnect:
        active_connections.remove(websocket)
        await emit_log("debug", "WebSocket client disconnected", "websocket")


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def calculate_extraction_metadata(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate metadata about the extraction quality.
    
    Supports both single-period and multi-period data structures.
    
    Args:
        data: Extracted financial data (single or multi-period)
        
    Returns:
        Dictionary with metadata statistics
    """
    high_confidence_count = 0
    medium_confidence_count = 0
    low_confidence_count = 0
    missing_count = 0
    total_fields = 0
    
    # Check if this is multi-period data
    if "periods" in data and isinstance(data["periods"], list):
        # Multi-period: aggregate stats across all periods
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


def calculate_average_confidence(data: Dict[str, Any]) -> float:
    """Calculate average confidence score across all fields.
    
    Supports both single-period and multi-period data structures.
    """
    confidences = []
    
    # Check if this is multi-period data
    if "periods" in data and isinstance(data["periods"], list):
        # Multi-period: aggregate confidences across all periods
        for period in data["periods"]:
            period_data = period.get("data", {})
            for field_value in period_data.values():
                if isinstance(field_value, dict) and "confidence" in field_value and "value" in field_value:
                    if field_value["value"] is not None:
                        confidences.append(field_value["confidence"])
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
            await connection.send_json(message)
        except Exception as e:
            logger.error(f"Error broadcasting to WebSocket: {e}")
            disconnected.append(connection)
    
    # Clean up disconnected connections
    for conn in disconnected:
        if conn in active_connections:
            active_connections.remove(conn)


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
