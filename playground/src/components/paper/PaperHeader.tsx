import { formatAuthors, getCitationsUrl, getInspireBaseUrl } from "@/lib/utils";
import { ArrowLeft, Award } from "lucide-react";
import { useEffect } from "react";

import { ThemeToggle } from "@/components/ThemeToggle";
import { AuthorsModal } from "@/components/paper/AuthorsModal";
import { CollaborationDisplay } from "@/components/paper/CollaborationDisplay";
import { Button } from "@/components/ui/button";

import { PaperDetails } from "@/types";

import ArxivSvg from "../../assets/arxiv.svg?react";
import InspireInSvg from "../../assets/inspire-in.svg?react";
import InspireSvg from "../../assets/inspire.svg?react";

interface PaperHeaderProps {
  paper: PaperDetails;
  onClose: () => void;
}

// TODO: This needs to be revisited once we fetch the full data from a paper
// then we will be able to properly extract and display author first and last names
// and link to their profiles
export function PaperHeader({ paper, onClose }: PaperHeaderProps) {
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
      }
    };

    document.addEventListener("keydown", handleKeyDown);

    return () => {
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [onClose]);

  return (
    <div className="bg-background/95 fixed top-0 right-0 left-0 h-[5rem] border-b py-4 pl-0 backdrop-blur">
      <div className="flex h-full items-center justify-between">
        <div className="flex items-center gap-4">
          <div>
            <Button
              variant="ghost"
              size="icon"
              onClick={onClose}
              className="h-[5rem] w-[5rem]"
              aria-label="Back"
            >
              <ArrowLeft className="size-10" strokeWidth={1.1} />
            </Button>

            <Button
              variant="ghost"
              size="icon"
              onClick={onClose}
              className="h-[5rem] w-[5rem]"
            >
              <InspireInSvg className="size-10" />
            </Button>
          </div>
          <div className="flex flex-col gap-2">
            <h2 className="line-clamp-1 text-xl font-semibold">
              {paper.title}
            </h2>
            <p className="text-muted-foreground flex items-center gap-0 text-sm">
              <span className="flex flex-wrap items-center [&>*+*]:before:mx-2 [&>*+*]:before:content-['•']">
                <span className="inline-flex items-center">
                  {paper.collaborations && paper.collaborations.length > 0 ? (
                    <CollaborationDisplay
                      collaborations={paper.collaborations}
                    />
                  ) : (
                    <>
                      {formatAuthors(paper.authors, paper.collaborations)}
                      {paper.authors.length > 2 && (
                        <AuthorsModal
                          authors={paper.authors}
                          collaborations={paper.collaborations}
                        />
                      )}
                    </>
                  )}
                </span>
                {paper.journal && <span>{paper.journal}</span>}
                {paper.year && <span>{paper.year}</span>}
                <span className="inline-flex items-center">
                  {paper.arxiv_id && (
                    <Button
                      variant="link"
                      size="sm"
                      className="h-4 px-2 text-xs text-[#B31B1B] dark:text-[#FF4444]"
                      asChild
                    >
                      <a
                        href={`https://arxiv.org/abs/${paper.arxiv_id}`}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        <ArxivSvg />
                        {paper.arxiv_id}
                      </a>
                    </Button>
                  )}
                  <Button
                    variant="link"
                    size="sm"
                    className="h-4 px-2 text-xs text-[#337AB7] dark:text-[#4993D1]"
                    asChild
                  >
                    <a
                      href={`${getInspireBaseUrl()}/literature/${paper.id}`}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      <InspireSvg />
                      {paper.id}
                    </a>
                  </Button>
                  {paper.citation_count > 0 && (
                    <Button
                      variant="link"
                      size="sm"
                      className="h-4 px-2 text-xs text-amber-600 dark:text-amber-400"
                      asChild
                    >
                      <a
                        href={getCitationsUrl(paper.id)}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        <Award />
                        {paper.citation_count} citations
                      </a>
                    </Button>
                  )}
                </span>
              </span>
            </p>
          </div>
        </div>
        <ThemeToggle className="text-muted-foreground m-5" />
      </div>
    </div>
  );
}
