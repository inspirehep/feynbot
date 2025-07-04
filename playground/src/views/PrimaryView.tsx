import { usePDFCache } from "@/hooks/usePDFCache";
import { convertInspirePaperToAppFormat, getPaperById } from "@/lib/api";
import { getPDFWithCache, getPaperUrl } from "@/lib/utils";
import { ResponseView } from "@/views/ResponseView";
import { FileSearch2, Search } from "lucide-react";
import { FormEvent, useEffect, useRef, useState } from "react";
import { ImperativePanelGroupHandle } from "react-resizable-panels";
import { toast } from "sonner";

import { PaperCard } from "@/components/PaperCard";
import { PaperHeader } from "@/components/paper/PaperHeader";
import PDFManager from "@/components/pdf/PDFManager";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from "@/components/ui/resizable";

import { FormattedCitation, LLMResponse, PaperDetails } from "@/types";

import Logo from "../assets/inspire-logo.svg?react";

const PrimaryView = () => {
  const [query, setQuery] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [response, setResponse] = useState<LLMResponse | null>(null);
  const [activePaper, setActivePaper] = useState<PaperDetails | null>(null);
  const resizableGroup = useRef<ImperativePanelGroupHandle>(null);

  const {
    clearCache,
    getCachedPDF,
    cachePDF,
    getPendingRequest,
    setPendingRequest,
  } = usePDFCache();

  const inspireApiUrl = import.meta.env.DEV
    ? ""
    : window.location.hostname.includes("inspirehep.net")
      ? "https://inspirehep.net"
      : "https://inspirebeta.net";

  const [formattedCitations, setFormattedCitations] = useState<
    FormattedCitation[]
  >([]);

  const handleSearch = async (e: FormEvent) => {
    e.preventDefault();

    clearCache();
    setActivePaper(null);
    setIsLoading(true);

    try {
      const llmResponse: LLMResponse = await fetch(
        `${inspireApiUrl}/ai/v1/query-rag`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ query: query }),
        },
      ).then((res) => res.json());

      const paperCache: Record<
        number,
        {
          paper: PaperDetails;
          snippets: string[];
        }
      > = {};
      const allPromises: Promise<FormattedCitation | null>[] = [];

      for (const citation of Object.values(llmResponse.citations)) {
        const { doc_id, control_number, snippet } = citation;

        if (paperCache[control_number]) {
          // If paper is in cache, add the new snippet to its snippets array
          paperCache[control_number].snippets.push(snippet);
        } else {
          // If paper is not in cache, fetch it and it to cache with the paper data and snippet
          paperCache[control_number] = {
            paper: {} as PaperDetails,
            snippets: [snippet],
          };
          const fetchPaperPromise = getPaperById(control_number.toString())
            .then((paper) => {
              const appPaper = convertInspirePaperToAppFormat(paper, snippet);
              paperCache[control_number].paper = appPaper;
              return {
                id: control_number,
                display: doc_id,
                paper: appPaper,
                snippets: paperCache[control_number].snippets,
              } as FormattedCitation;
            })
            .catch((error) => {
              toast.error(`Failed to fetch paper ${control_number}:`, error);
              return null;
            });
          allPromises.push(fetchPaperPromise);
        }
      }

      const citationDetails = (await Promise.all(allPromises)).filter(
        (detail): detail is FormattedCitation => detail !== null,
      );

      setFormattedCitations(citationDetails);
      setResponse(llmResponse);
    } catch {
      toast.error("Something went wrong. Please try again later.");
    } finally {
      setIsLoading(false);
    }
  };

  const handlePaperClick = (paperId: number) => {
    setActivePaper(
      formattedCitations.find((p) => p.id === paperId)?.paper as PaperDetails,
    );
  };

  const renderSearchForm = () => (
    <form onSubmit={handleSearch} className="bg-background px-4 pt-4">
      <div className="flex gap-2">
        <div className="relative flex-1">
          {activePaper ? (
            <FileSearch2 className="text-muted-foreground absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2" />
          ) : (
            <Search className="text-muted-foreground absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2" />
          )}
          <Input
            type="text"
            placeholder={
              activePaper
                ? "Ask questions about the current paper"
                : "Ask about high-energy physics..."
            }
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="h-12 pl-10"
          />
        </div>
        <Button
          type="submit"
          className="h-12 px-6"
          disabled={isLoading || !query.trim()}
        >
          {isLoading ? "Searching..." : "Search"}
        </Button>
      </div>
      <p className="text-muted-foreground mt-3 text-center text-xs">
        INSPIRE Playground uses AI and can make mistakes.
      </p>
    </form>
  );

  // Pre-fetch all PDFs
  useEffect(() => {
    const prefetchPDFs = async () => {
      const fetchPromises = formattedCitations.map(async (citation) => {
        const paper = citation.paper;
        const pdfUrl = getPaperUrl(paper);

        if (pdfUrl) {
          await getPDFWithCache(
            pdfUrl,
            getCachedPDF,
            cachePDF,
            getPendingRequest,
            setPendingRequest,
          );
        }
      });

      await Promise.all(fetchPromises);
    };

    if (formattedCitations.length > 0) {
      prefetchPDFs();
    }
  }, [
    formattedCitations,
    getCachedPDF,
    cachePDF,
    getPendingRequest,
    setPendingRequest,
  ]);

  if (activePaper) {
    return (
      <div className="fixed inset-0 flex flex-col">
        <PaperHeader paper={activePaper} onClose={() => setActivePaper(null)} />

        <div className="mt-[5rem] h-[calc(100vh-15rem)]">
          <ResizablePanelGroup direction="horizontal" ref={resizableGroup}>
            <ResizablePanel defaultSize={50} minSize={25}>
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
              onDoubleClick={() => resizableGroup?.current?.setLayout([50, 50])}
            />
            <ResizablePanel defaultSize={50} minSize={25}>
              <div className="flex h-full flex-col">
                <div className="flex-1 overflow-y-auto">
                  {isLoading ? (
                    <div className="flex items-center justify-center py-12">
                      <div className="border-primary h-12 w-12 animate-spin rounded-full border-2 border-t-transparent" />
                    </div>
                  ) : (
                    response && (
                      <ResponseView
                        fullResponse={response}
                        onPaperClick={handlePaperClick}
                        activePaper={activePaper}
                      />
                    )
                  )}
                </div>
                {renderSearchForm()}
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
                  onClick={() => handlePaperClick(citation.id)}
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
  }

  return (
    <div className="flex flex-col items-center">
      <Logo className="h-auto max-w-xs self-center py-8" />
      {!response && (
        <div className="max-w-3xl">
          <h1 className="mb-8 text-center text-4xl">
            <span className="bg-gradient-to-r from-sky-400/60 via-sky-400 to-sky-400/60 bg-clip-text font-semibold text-transparent">
              Revolutionize{" "}
            </span>
            your High-Energy Physics research
          </h1>
          <p className="mb-8 text-center">
            Transform the way you conduct high energy physics{" "}
            <span className="font-semibold">research</span>. Let our AI guide
            you to the most relevant{" "}
            <span className="font-semibold">papers</span>, extract crucial{" "}
            <span className="font-semibold">insights</span> with verifiable{" "}
            <span className="font-semibold">sources</span> and propel your work
            forward <span className="font-semibold">faster</span> than ever
            before.
          </p>
        </div>
      )}
      <div className="mx-auto w-[80%]">
        {renderSearchForm()}
        <div className="p-4 pt-8">
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <div className="border-primary h-12 w-12 animate-spin rounded-full border-2 border-t-transparent" />
            </div>
          ) : (
            response && (
              <div>
                <ResponseView
                  fullResponse={response}
                  onPaperClick={handlePaperClick}
                  activePaper={activePaper}
                />
                <div className="mt-4 space-y-2">
                  <h3 className="text-lg font-semibold">Related Papers</h3>
                  <div className="grid grid-cols-1 gap-4 transition-all duration-300 md:grid-cols-2">
                    {formattedCitations.map((citation) => (
                      <div key={citation.id} className="h-full min-w-[300px]">
                        <PaperCard
                          formattedCitation={citation}
                          onClick={() => handlePaperClick(citation.id)}
                        />
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )
          )}
        </div>
      </div>
    </div>
  );
};

export default PrimaryView;
