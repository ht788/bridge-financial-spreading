import React, { useState } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import { ChevronLeft, ChevronRight, ZoomIn, ZoomOut } from 'lucide-react';
import 'react-pdf/dist/esm/Page/AnnotationLayer.css';
import 'react-pdf/dist/esm/Page/TextLayer.css';

// Configure PDF.js worker
pdfjs.GlobalWorkerOptions.workerSrc = `//cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjs.version}/pdf.worker.min.js`;

interface PDFViewerProps {
  pdfUrl: string;
}

export const PDFViewer: React.FC<PDFViewerProps> = ({ pdfUrl }) => {
  const [numPages, setNumPages] = useState<number>(0);
  const [pageNumber, setPageNumber] = useState<number>(1);
  const [scale, setScale] = useState<number>(1.0);

  function onDocumentLoadSuccess({ numPages }: { numPages: number }) {
    setNumPages(numPages);
    setPageNumber(1);
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

  const zoomIn = () => setScale((prev) => Math.min(prev + 0.2, 2.0));
  const zoomOut = () => setScale((prev) => Math.max(prev - 0.2, 0.5));

  return (
    <div className="flex flex-col h-full bg-gray-100">
      {/* Controls */}
      <div className="bg-white border-b border-gray-200 p-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <button
            onClick={() => changePage(-1)}
            disabled={pageNumber <= 1}
            className="p-2 rounded hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
            aria-label="Previous page"
          >
            <ChevronLeft className="w-5 h-5" />
          </button>
          <span className="text-sm text-gray-700">
            Page {pageNumber} of {numPages}
          </span>
          <button
            onClick={() => changePage(1)}
            disabled={pageNumber >= numPages}
            className="p-2 rounded hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
            aria-label="Next page"
          >
            <ChevronRight className="w-5 h-5" />
          </button>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={zoomOut}
            className="p-2 rounded hover:bg-gray-100"
            aria-label="Zoom out"
          >
            <ZoomOut className="w-5 h-5" />
          </button>
          <span className="text-sm text-gray-700 w-12 text-center">
            {Math.round(scale * 100)}%
          </span>
          <button
            onClick={zoomIn}
            className="p-2 rounded hover:bg-gray-100"
            aria-label="Zoom in"
          >
            <ZoomIn className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* PDF Display */}
      <div className="flex-1 overflow-auto p-4 flex justify-center">
        <Document
          file={pdfUrl}
          onLoadSuccess={onDocumentLoadSuccess}
          loading={
            <div className="flex items-center justify-center h-full">
              <div className="text-gray-500">Loading PDF...</div>
            </div>
          }
          error={
            <div className="flex items-center justify-center h-full">
              <div className="text-red-500">Error loading PDF</div>
            </div>
          }
        >
          <Page
            pageNumber={pageNumber}
            scale={scale}
            renderTextLayer={true}
            renderAnnotationLayer={true}
          />
        </Document>
      </div>
    </div>
  );
};
