import React, { useState, useRef, useEffect } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import { ChevronLeft, ChevronRight, ZoomIn, ZoomOut, Loader2 } from 'lucide-react';
import 'react-pdf/dist/esm/Page/AnnotationLayer.css';
import 'react-pdf/dist/esm/Page/TextLayer.css';

// Configure PDF.js worker
pdfjs.GlobalWorkerOptions.workerSrc = `//cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjs.version}/pdf.worker.min.js`;

interface PDFViewerProps {
  pdfUrl: string;
  compact?: boolean; // Compact mode for Answer Key Editor
}

export const PDFViewer: React.FC<PDFViewerProps> = ({ pdfUrl, compact = false }) => {
  const [numPages, setNumPages] = useState<number>(0);
  const [pageNumber, setPageNumber] = useState<number>(1);
  const [scale, setScale] = useState<number>(1.0);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Reset state when URL changes
  useEffect(() => {
    setPageNumber(1);
    setIsLoading(true);
    setError(null);
  }, [pdfUrl]);

  function onDocumentLoadSuccess({ numPages }: { numPages: number }) {
    setNumPages(numPages);
    setPageNumber(1);
    setIsLoading(false);
    setError(null);
  }

  function onDocumentLoadError(err: Error) {
    console.error('PDF load error:', err);
    setIsLoading(false);
    setError('Failed to load PDF');
  }

  // Handle missing PDF URL
  if (!pdfUrl) {
    return (
      <div className="flex flex-col h-full bg-gray-100 items-center justify-center">
        <div className="text-gray-500 text-center p-8">
          <div className="text-lg font-medium mb-2">No PDF file specified</div>
          <div className="text-sm text-gray-400">
            The document preview is not available for this file type.
          </div>
        </div>
      </div>
    );
  }

  const changePage = (offset: number) => {
    setPageNumber((prevPageNumber) => Math.max(1, Math.min(prevPageNumber + offset, numPages)));
  };

  const zoomIn = () => setScale((prev) => Math.min(prev + 0.2, 3.0));
  const zoomOut = () => setScale((prev) => Math.max(prev - 0.2, 0.4));

  return (
    <div className="flex flex-col h-full bg-gray-100" ref={containerRef}>
      {/* Compact Controls Bar */}
      <div className={`bg-white border-b border-gray-200 flex items-center justify-between ${compact ? 'px-2 py-1.5' : 'p-4'}`}>
        <div className="flex items-center gap-1">
          <button
            onClick={() => changePage(-1)}
            disabled={pageNumber <= 1}
            className={`rounded hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed ${compact ? 'p-1' : 'p-2'}`}
            aria-label="Previous page"
          >
            <ChevronLeft className={compact ? 'w-4 h-4' : 'w-5 h-5'} />
          </button>
          <span className={`text-gray-700 ${compact ? 'text-xs min-w-[70px] text-center' : 'text-sm'}`}>
            {pageNumber} / {numPages || '...'}
          </span>
          <button
            onClick={() => changePage(1)}
            disabled={pageNumber >= numPages}
            className={`rounded hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed ${compact ? 'p-1' : 'p-2'}`}
            aria-label="Next page"
          >
            <ChevronRight className={compact ? 'w-4 h-4' : 'w-5 h-5'} />
          </button>
        </div>

        <div className="flex items-center gap-1">
          <button
            onClick={zoomOut}
            className={`rounded hover:bg-gray-100 ${compact ? 'p-1' : 'p-2'}`}
            aria-label="Zoom out"
          >
            <ZoomOut className={compact ? 'w-4 h-4' : 'w-5 h-5'} />
          </button>
          <span className={`text-gray-700 text-center ${compact ? 'text-xs w-10' : 'text-sm w-12'}`}>
            {Math.round(scale * 100)}%
          </span>
          <button
            onClick={zoomIn}
            className={`rounded hover:bg-gray-100 ${compact ? 'p-1' : 'p-2'}`}
            aria-label="Zoom in"
          >
            <ZoomIn className={compact ? 'w-4 h-4' : 'w-5 h-5'} />
          </button>
        </div>
      </div>

      {/* PDF Display - Full Width */}
      <div className="flex-1 overflow-auto flex justify-center">
        {isLoading && (
          <div className="absolute inset-0 flex items-center justify-center bg-gray-100/80 z-10">
            <div className="flex items-center gap-2 text-gray-500">
              <Loader2 className="w-5 h-5 animate-spin" />
              <span>Loading PDF...</span>
            </div>
          </div>
        )}
        
        {error && (
          <div className="flex items-center justify-center h-full">
            <div className="text-red-500 text-center">
              <div className="font-medium">{error}</div>
              <div className="text-sm text-gray-400 mt-1">Check that the file exists</div>
            </div>
          </div>
        )}

        <Document
          file={pdfUrl}
          onLoadSuccess={onDocumentLoadSuccess}
          onLoadError={onDocumentLoadError}
          loading={null}
          error={null}
          className="flex justify-center"
        >
          <Page
            pageNumber={pageNumber}
            scale={scale}
            renderTextLayer={true}
            renderAnnotationLayer={true}
            className="shadow-lg"
            loading={null}
          />
        </Document>
      </div>
    </div>
  );
};
