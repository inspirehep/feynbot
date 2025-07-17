// import "pdfjs-dist/build/pdf.worker.min.mjs";
import { usePDFCache } from "@/hooks/usePDFCache";
import { getPDFWithCache } from "@/lib/utils";
import {
  AnnotationLayer,
  CanvasLayer,
  HighlightLayer,
  Page,
  Pages,
  Root,
  Search,
  TextLayer,
} from "@anaralabs/lector";
import { GlobalWorkerOptions } from "pdfjs-dist";
import "pdfjs-dist/web/pdf_viewer.css";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import PDFSearch from "@/components/pdf/PDFSearch";
import { Loading } from "@/components/ui/loading";

GlobalWorkerOptions.workerSrc = new URL(
  "pdfjs-dist/build/pdf.worker.mjs",
  import.meta.url,
).toString();

const PDFViewer = ({
  pdfUrl,
  highlight,
}: {
  pdfUrl: string;
  highlight?: string;
}) => {
  const { getCachedPDF, cachePDF, getPendingRequest, setPendingRequest } =
    usePDFCache();
  const [effectivePdfUrl, setEffectivePdfUrl] = useState<string>("");

  // PDFs are already cached, otherwise fetch them
  useEffect(() => {
    (async () => {
      const blobUrl = await getPDFWithCache(
        pdfUrl,
        getCachedPDF,
        cachePDF,
        getPendingRequest,
        setPendingRequest,
      );

      if (blobUrl) {
        setEffectivePdfUrl(blobUrl);
      } else {
        toast.error("Failed to fetch PDF");
        setEffectivePdfUrl(pdfUrl);
      }
    })();
  }, [pdfUrl, getCachedPDF, cachePDF, getPendingRequest, setPendingRequest]);

  const LoadingSpinner = () => (
    <div className="absolute inset-0 flex items-center justify-center">
      <Loading text="Loading PDF..." />
    </div>
  );

  return (
    <div className="relative">
      <Root
        source={effectivePdfUrl}
        className="h-[calc(100vh-15rem)] overflow-y-auto"
        loader={<LoadingSpinner />}
        isZoomFitWidth
      >
        <Search>
          <PDFSearch highlight={highlight} />
        </Search>
        <Pages className="dark:brightness-[80%] dark:contrast-[228%] dark:hue-rotate-180 dark:invert-[94%]">
          <Page>
            <CanvasLayer />
            <TextLayer />
            <AnnotationLayer />
            <HighlightLayer className="bg-yellow-200/70" />
          </Page>
        </Pages>
      </Root>
    </div>
  );
};

export default PDFViewer;
