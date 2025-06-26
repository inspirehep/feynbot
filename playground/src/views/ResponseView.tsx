import { cn } from "@/lib/utils";
import { Check, Copy, ThumbsDown, ThumbsUp } from "lucide-react";
import { useState } from "react";
import Latex from "react-latex-next";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

import { LLMResponse, PaperDetails } from "@/types";

interface ResponseViewProps {
  fullResponse: LLMResponse;
  onPaperClick: (paperId: number) => void;
  activePaper: PaperDetails | null;
}

export function ResponseView({
  fullResponse,
  onPaperClick,
  activePaper,
}: ResponseViewProps) {
  const { brief_answer, long_answer, citations } = fullResponse;

  // Replace citation references with clickable badges with the right number
  const renderTextWithCitations = (text: string) => {
    return text.split(/(\[\d+\])/g).map((part, index) => {
      const match = part.match(/\[(\d+)\]/);
      if (!match) return <Latex>{part}</Latex>;

      const citation = citations[Number(match[1]) - 1];

      if (!citation) return part[0];

      return (
        <Tooltip delayDuration={300} key={index}>
          <TooltipTrigger asChild>
            <span>
              <Badge
                onClick={() => onPaperClick(citation.control_number)}
                className="text-primary cursor-pointer rounded-full font-medium hover:underline"
                variant="secondary"
              >
                {citation.doc_id}
              </Badge>
            </span>
          </TooltipTrigger>
          <TooltipContent className="max-w-2xs p-2">
            <div className="line-clamp-3 text-ellipsis">{citation.snippet}</div>
          </TooltipContent>
        </Tooltip>
      );
    });
  };

  const ActionButtons = () => {
    const [copied, setCopied] = useState(false);

    const copyToClipboard = () => {
      navigator.clipboard.writeText(
        long_answer.replace(/\s*\[(\d+:\d+)\]/g, ""),
      );
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    };

    return (
      <div className="flex items-center gap-2">
        <Button
          variant="ghost"
          size="icon"
          onClick={copyToClipboard}
          className="relative h-8 w-8"
        >
          <Copy
            className={cn(
              "absolute h-4 w-4 transition-all duration-300",
              copied ? "scale-50 opacity-0" : "scale-100 opacity-100",
            )}
          />
          <Check
            className={cn(
              "absolute h-4 w-4 transition-all duration-300",
              copied ? "scale-100 opacity-100" : "scale-50 opacity-0",
            )}
          />
          <span className="sr-only">{copied ? "Copied" : "Copy response"}</span>
        </Button>
        <Button variant="ghost" size="icon" className="h-8 w-8">
          <ThumbsUp className="h-4 w-4" />
          <span className="sr-only">Helpful</span>
        </Button>
        <Button variant="ghost" size="icon" className="h-8 w-8">
          <ThumbsDown className="h-4 w-4" />
          <span className="sr-only">Not helpful</span>
        </Button>
      </div>
    );
  };

  const TextContent = () => (
    <div className="prose prose-sm dark:prose-invert max-w-none">
      <div className="mb-4 font-normal">{brief_answer}</div>
      <p>{renderTextWithCitations(long_answer)}</p>
    </div>
  );

  return (
    <div className="overflow-y-auto pb-4">
      {activePaper ? (
        <div>
          <div className="flex flex-row items-start justify-between p-6">
            <h2 className="text-2xl font-semibold">Summary</h2>
            <ActionButtons />
          </div>
          <div className="px-6">
            <TextContent />
          </div>
        </div>
      ) : (
        <Card>
          <CardHeader className="flex flex-row items-start justify-between">
            <CardTitle className="self-center">Summary</CardTitle>
            <ActionButtons />
          </CardHeader>
          <CardContent>
            <TextContent />
          </CardContent>
        </Card>
      )}
    </div>
  );
}
