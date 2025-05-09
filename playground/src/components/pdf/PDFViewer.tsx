import {
  CanvasLayer,
  HighlightLayer,
  Page,
  Pages,
  Root,
  Search,
  TextLayer,
} from "@anaralabs/lector";
import { Loader2 } from "lucide-react";
import { GlobalWorkerOptions } from "pdfjs-dist";
import "pdfjs-dist/web/pdf_viewer.css";

import PDFSearch from "./PDFSearch";

const PDF_URL = "https://export.arxiv.org/pdf/1708.08021";

GlobalWorkerOptions.workerSrc = new URL(
  "pdfjs-dist/build/pdf.worker.mjs",
  import.meta.url,
).toString();

const PDFViewer = ({ pdfUrl }: { pdfUrl: string }) => {
  return (
    <div className="relative">
      <Root
        source={pdfUrl || PDF_URL}
        className="h-[calc(100vh-15rem)] overflow-y-auto" // Subtract top and bottom bars
        loader={
          <div className="absolute inset-0 flex items-center justify-center">
            <Loader2 className="text-primary h-8 w-8 animate-spin" />
            <span className="ml-2">Loading...</span>
          </div>
        }
        isZoomFitWidth
      >
        <Search>
          <PDFSearch />
        </Search>
        <Pages className="dark:brightness-[80%] dark:contrast-[228%] dark:hue-rotate-180 dark:invert-[94%]">
          <Page>
            <CanvasLayer />
            <TextLayer />
            <HighlightLayer className="bg-yellow-200/70" />
          </Page>
        </Pages>
      </Root>
    </div>
  );
};

export default PDFViewer;
