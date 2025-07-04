import { getPaperUrl } from "@/lib/utils";

import PDFViewer from "@/components/pdf/PDFViewer";

import { PaperDetails } from "@/types";

interface PDFManagerProps {
  papers: PaperDetails[];
  activePaper: PaperDetails | null;
}

// Renders a PDF viewer for each paper in the list in order to pre-load them and speed up switching between them
const PDFManager = ({ papers, activePaper }: PDFManagerProps) => {
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
              highlight={
                isActive ? activePaper?.highlight?.slice(0, 15) : undefined
              }
            />
          </div>
        );
      })}
    </div>
  );
};

export default PDFManager;
