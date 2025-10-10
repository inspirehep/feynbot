import { cn, formatAuthors, getCitationsUrl } from "@/lib/utils";
import { Award, FileText } from "lucide-react";
import { MouseEvent } from "react";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

import { LLMCitation, PaperDetails } from "@/types";

interface PaperCardProps {
  paper: PaperDetails;
  citations?: LLMCitation[];
  onClick: () => void;
  displayType?: "full" | "footer";
  isActive?: boolean;
}

export function PaperCard({
  paper,
  citations = [],
  onClick,
  displayType = "full",
  isActive = false,
}: PaperCardProps) {
  const handleCitationsClick = (e: MouseEvent<HTMLButtonElement>) => {
    e.stopPropagation();
    window.open(getCitationsUrl(paper.id), "_blank");
  };

  return (
    <Card
      className={cn(
        "hover:border-primary cursor-pointer transition-all hover:shadow-md",
        isActive && "border-primary border-2",
        displayType === "full" ? "h-full" : "",
      )}
      onClick={onClick}
    >
      <CardHeader>
        <CardTitle className="flex items-center justify-between text-base">
          <span className="line-clamp-2">{paper.title}</span>
          {citations.length > 0 && (
            <span className="text-muted-foreground ml-2 self-start text-sm">
              {citations.map((c) => `#${c.doc_id}`).join(",")}
            </span>
          )}
        </CardTitle>
        <CardDescription className="flex items-center justify-between text-xs">
          <span className="flex items-center">
            {formatAuthors(
              paper.authors,
              paper.collaborations,
              displayType === "footer" ? 1 : undefined,
            )}{" "}
            • {paper.year}
          </span>
          <span className="flex items-center whitespace-nowrap">
            {paper.citation_count > 0 && (
              <Tooltip>
                <TooltipTrigger asChild>
                  <button
                    onClick={handleCitationsClick}
                    className="inline-flex items-center font-medium text-amber-600 hover:underline dark:text-amber-400"
                  >
                    <Award className="h-3 w-3" />
                    {paper.citation_count}
                  </button>
                </TooltipTrigger>
                <TooltipContent>See citations in Inspire</TooltipContent>
              </Tooltip>
            )}
          </span>
        </CardDescription>
      </CardHeader>
      {displayType === "full" && (
        <CardContent>
          {citations.length > 0 ? (
            <div className="line-clamp-3 text-sm italic">
              "{citations[0].snippet}"
            </div>
          ) : (
            paper.abstract &&
            paper.abstract !== "No abstract available" && (
              <p className="text-muted-foreground line-clamp-3 text-sm">
                {paper.abstract}
              </p>
            )
          )}
          <div className="text-muted-foreground mt-4 flex items-center justify-between text-xs">
            <span className="max-w-[70%] truncate">{paper.journal}</span>
            {paper.arxiv_id && (
              <span className="flex items-center gap-1">
                <FileText className="h-3 w-3" />
                arXiv:{paper.arxiv_id}
              </span>
            )}
          </div>
        </CardContent>
      )}
    </Card>
  );
}
