import { getPaperUrl } from "@/lib/utils";

import PDFViewer from "@/components/pdf/PDFViewer";

import { BoundingBox, PaperDetails } from "@/types";

interface PDFManagerProps {
  papers: PaperDetails[];
  activePaper: PaperDetails | null;
  activeBboxes?: BoundingBox[];
}

// Renders a PDF viewer for each paper in the list in order to pre-load them and speed up switching between them
const PDFManager = ({ papers, activePaper, activeBboxes }: PDFManagerProps) => {
  return (
    <div className="relative h-full w-full">
      {papers.map((paper) => {
        const pdfUrl = getPaperUrl(paper);
        if (!pdfUrl) return null;

        const isActive = activePaper?.id === paper.id;

        return (
          <div key={paper.id} className={`${isActive ? "block" : "hidden"}`}>
            <PDFViewer
              pdfUrl={pdfUrl}
              activeBboxes={isActive ? activeBboxes : undefined}
            />
          </div>
        );
      })}
    </div>
  );
};

export default PDFManager;
