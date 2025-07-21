import { ResponseView } from "@/views/ResponseView";
import { ChevronDown } from "lucide-react";
import { useRef, useState } from "react";
import { ImperativePanelGroupHandle } from "react-resizable-panels";

import { PaperCard } from "@/components/PaperCard";
import PaperChat from "@/components/PaperChat";
import { PaperHeader } from "@/components/paper/PaperHeader";
import PDFManager from "@/components/pdf/PDFManager";
import { Button } from "@/components/ui/button";
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from "@/components/ui/resizable";

import { FormattedCitation, LLMResponse, PaperDetails } from "@/types";

interface PaperViewProps {
  activePaper: PaperDetails;
  onClose: () => void;
  formattedCitations: FormattedCitation[];
  onPaperClick: (paperId: number) => void;
  generalResponse: LLMResponse | null;
}

const PaperView = ({
  activePaper,
  onClose,
  formattedCitations,
  onPaperClick,
  generalResponse,
}: PaperViewProps) => {
  const resizableGroup = useRef<ImperativePanelGroupHandle>(null);
  const [isGeneralResponseExpanded, setIsGeneralResponseExpanded] =
    useState(true);

  return (
    <div className="fixed inset-0 flex flex-col">
      <PaperHeader paper={activePaper} onClose={onClose} />

      <div className="mt-[5rem] h-[calc(100vh-15rem)]">
        <ResizablePanelGroup direction="horizontal" ref={resizableGroup}>
          <ResizablePanel defaultSize={60} minSize={25}>
            <div className="relative h-full">
              <div className="after:from-background h-full after:absolute after:right-0 after:bottom-0 after:left-0 after:h-12 after:bg-gradient-to-t after:to-transparent">
                <PDFManager
                  papers={formattedCitations.map((c) => c.paper)}
                  activePaper={activePaper}
                />
              </div>
            </div>
          </ResizablePanel>
          <ResizableHandle
            withHandle
            onDoubleClick={() => resizableGroup?.current?.setLayout([60, 40])}
          />
          <ResizablePanel defaultSize={40} minSize={25}>
            <div className="flex h-full flex-col">
              {generalResponse ? (
                <div className="relative flex-none border-b pb-6">
                  <ResponseView
                    response={generalResponse}
                    onPaperClick={onPaperClick}
                    activePaper={activePaper}
                    isCollapsible={true}
                    isExpanded={isGeneralResponseExpanded}
                  />

                  <div className="absolute bottom-0 left-1/2 -translate-x-1/2 translate-y-1/2 transform">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() =>
                        setIsGeneralResponseExpanded(!isGeneralResponseExpanded)
                      }
                      className="bg-background h-5 w-7 shadow-sm transition-all duration-300"
                    >
                      <ChevronDown
                        className={`h-3 w-3 transition-transform duration-700 ease-in-out ${
                          isGeneralResponseExpanded ? "rotate-180" : ""
                        }`}
                      />
                    </Button>
                  </div>
                </div>
              ) : (
                <div className="flex-none border-b p-4">
                  <div className="text-muted-foreground text-center">
                    <p className="text-sm">
                      No general search result available
                    </p>
                  </div>
                </div>
              )}

              <div className="min-h-0 flex-1 pt-2">
                <PaperChat activePaper={activePaper} />
              </div>
            </div>
          </ResizablePanel>
        </ResizablePanelGroup>
      </div>

      <div className="relative px-4">
        <div className="flex gap-4 overflow-x-auto p-4">
          {formattedCitations.map((citation) => (
            <div key={citation.id} className="min-w-[300px]">
              <PaperCard
                formattedCitation={citation}
                isActive={activePaper?.id === citation.paper.id}
                onClick={() => onPaperClick(citation.id)}
                displayType="footer"
              />
            </div>
          ))}
        </div>
        <div className="from-background absolute inset-y-0 left-4 w-8 bg-gradient-to-r" />
        <div className="from-background absolute inset-y-0 right-4 w-8 bg-gradient-to-l" />
      </div>
    </div>
  );
};

export default PaperView;
