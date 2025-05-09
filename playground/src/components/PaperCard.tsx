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

import { FormattedCitation } from "@/types";

interface PaperCardProps {
  formattedCitation: FormattedCitation;
  onClick: () => void;
  displayType?: "full" | "footer";
  isActive?: boolean;
}

export function PaperCard({
  formattedCitation,
  onClick,
  displayType = "full",
  isActive = false,
}: PaperCardProps) {
  const { paper, display, snippets } = formattedCitation;

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
          <span className="text-muted-foreground ml-2 self-start text-sm">
            #{display}
          </span>
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
          {snippets.length > 0 && (
            <blockquote className="border-muted line-clamp-3 border-l-2 pl-3 text-sm italic">
              "{snippets[0]}"
            </blockquote>
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
