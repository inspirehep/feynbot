import { usePDFCache } from "@/hooks/usePDFCache";
import { usePaperChatHistory } from "@/hooks/usePaperChatHistory";
import { convertInspirePaperToAppFormat, getPaperById } from "@/lib/api";
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
  FormattedCitation,
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

  const { clearAllHistories } = usePaperChatHistory();

  const {
    clearCache,
    getCachedPDF,
    cachePDF,
    getPendingRequest,
    setPendingRequest,
  } = usePDFCache();

  const [formattedCitations, setFormattedCitations] = useState<
    FormattedCitation[]
  >([]);

  const handleSearch = async (e: FormEvent) => {
    e.preventDefault();
    await handleGeneralSearch();
  };

  const handleGeneralSearch = async () => {
    clearCache();
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
      <PaperView
        activePaper={activePaper}
        onClose={() => {
          setActivePaper(null);
        }}
        formattedCitations={formattedCitations}
        onPaperClick={handlePaperClick}
        generalResponse={response}
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
