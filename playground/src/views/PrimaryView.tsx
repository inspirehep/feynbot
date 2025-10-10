import { useFeedback } from "@/contexts/FeedbackContext";
import { usePDFCache } from "@/hooks/usePDFCache";
import { usePaperChatHistory } from "@/hooks/usePaperChatHistory";
import {
  convertInspirePaperToAppFormat,
  getPaperById,
} from "@/lib/inspire-api";
import { getInspireAiUrl, getPDFWithCache, getPaperUrl } from "@/lib/utils";
import PaperView from "@/views/PaperView";
import { ResponseView } from "@/views/ResponseView";
import { Search } from "lucide-react";
import { FormEvent, useEffect, useState } from "react";
import { toast } from "sonner";

import { PaperCard } from "@/components/PaperCard";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Loading } from "@/components/ui/loading";

import {
  BoundingBox,
  LLMCitation,
  LLMResponse,
  PaperDetails,
  QueryRequest,
} from "@/types";

import Logo from "../assets/inspire-logo.svg?react";

const PrimaryView = () => {
  const [query, setQuery] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [response, setResponse] = useState<LLMResponse | null>(null);
  const [activePaper, setActivePaper] = useState<PaperDetails | null>(null);
  const [activeBboxes, setActiveBboxes] = useState<BoundingBox[]>([]);

  const { clearAllHistories } = usePaperChatHistory();
  const { resetFeedback } = useFeedback();

  const {
    clearCache,
    getCachedPDF,
    cachePDF,
    getPendingRequest,
    setPendingRequest,
  } = usePDFCache();

  const [papers, setPapers] = useState<PaperDetails[]>([]);
  const [citations, setCitations] = useState<LLMCitation[]>([]);

  const handleSearch = async (e: FormEvent) => {
    e.preventDefault();
    await handleGeneralSearch();
  };

  const handleGeneralSearch = async () => {
    clearCache();
    resetFeedback();
    setActivePaper(null);
    clearAllHistories();
    setIsLoading(true);

    try {
      const requestBody: QueryRequest = { query: query };

      const llmResponse: LLMResponse = await fetch(
        `${getInspireAiUrl()}/v1/query-rag`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(requestBody),
        },
      ).then((res) => res.json());

      const uniquePaperIds = [
        ...new Set(llmResponse.citations.map((c) => c.control_number)),
      ];

      // Fetch papers in parallel
      const paperPromises = uniquePaperIds.map(async (paperId) => {
        try {
          const inspirePaper = await getPaperById(paperId);
          return convertInspirePaperToAppFormat(inspirePaper);
        } catch {
          toast.error(`Failed to fetch paper ${paperId}`);
          return null;
        }
      });

      const fetchedPapers = (await Promise.all(paperPromises)).filter(
        (paper): paper is PaperDetails => paper !== null,
      );

      setPapers(fetchedPapers);
      setCitations(llmResponse.citations);
      setResponse(llmResponse);
    } catch {
      toast.error("Something went wrong. Please try again later.");
    } finally {
      setIsLoading(false);
    }
  };

  const handlePaperClick = (paperId: number) => {
    setActivePaper(papers.find((p) => p.id === paperId) || null);
    setActiveBboxes([]);
  };

  const handleCitationClick = (paperId: number, bboxes: BoundingBox[]) => {
    setActivePaper(papers.find((p) => p.id === paperId) || null);
    setActiveBboxes(bboxes);
  };

  const renderSearchForm = () => (
    <form onSubmit={handleSearch} className="bg-background px-4 pt-4">
      <div className="flex gap-2">
        <div className="relative flex-1">
          <Search className="text-muted-foreground absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2" />
          <Input
            type="text"
            placeholder="Ask about high-energy physics..."
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
      const fetchPromises = papers.map(async (paper) => {
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

    if (papers.length > 0) {
      prefetchPDFs();
    }
  }, [papers, getCachedPDF, cachePDF, getPendingRequest, setPendingRequest]);

  if (activePaper) {
    return (
      <PaperView
        activePaper={activePaper}
        onClose={() => {
          setActivePaper(null);
          setActiveBboxes([]);
        }}
        papers={papers}
        citations={citations}
        onPaperClick={handlePaperClick}
        onCitationClick={handleCitationClick}
        generalResponse={response}
        activeBboxes={activeBboxes}
      />
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
              <Loading />
            </div>
          ) : (
            response && (
              <div>
                <ResponseView
                  response={response}
                  onCitationClick={handleCitationClick}
                  activePaper={activePaper}
                />
                <div className="mt-4 space-y-2">
                  <h3 className="text-lg font-semibold">Related Papers</h3>
                  <div className="grid grid-cols-1 gap-4 transition-all duration-300 md:grid-cols-2">
                    {papers.map((paper) => (
                      <div key={paper.id} className="h-full min-w-[300px]">
                        <PaperCard
                          paper={paper}
                          citations={citations.filter(
                            (c) => c.control_number === paper.id,
                          )}
                          onClick={() => handlePaperClick(paper.id)}
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
