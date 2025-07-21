import { useFeedback } from "@/contexts/FeedbackContext";
import { submitRagFeedback } from "@/lib/ai-api";
import { cn } from "@/lib/utils";
import {
  Check,
  Copy,
  MessageSquare,
  MessageSquareText,
  ThumbsDown,
  ThumbsUp,
} from "lucide-react";
import { useState } from "react";
import Latex from "react-latex-next";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Textarea } from "@/components/ui/textarea";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

import { LLMResponse, PaperDetails } from "@/types";

interface ResponseViewProps {
  response: LLMResponse;
  onPaperClick: (paperId: number) => void;
  activePaper: PaperDetails | null;
  isCollapsible?: boolean;
  isExpanded?: boolean;
}

export function ResponseView({
  response,
  onPaperClick,
  activePaper,
  isCollapsible = false,
  isExpanded = true,
}: ResponseViewProps) {
  const { brief_answer, long_answer, citations, trace_id } = response;

  // Replace citation references with clickable badges with the right number
  const renderTextWithCitations = (text: string) => {
    return text.split(/(\[\d+\])/g).map((part, index) => {
      const match = part.match(/\[(\d+)\]/);
      if (!match) return <Latex key={index}>{part}</Latex>;

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
    const [comment, setComment] = useState("");
    const [commentPopoverOpen, setCommentPopoverOpen] = useState(false);

    const {
      feedbackState,
      setFeedback,
      setScoreId,
      setSubmittingFeedback,
      setSubmittedComment,
    } = useFeedback();

    const { feedback, scoreId, submittingFeedback, submittedComment } =
      feedbackState;

    const copyToClipboard = () => {
      navigator.clipboard.writeText(long_answer.replace(/\s*\[(\d+)\]/g, ""));
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    };

    const handleFeedback = async (helpful?: boolean) => {
      if (submittingFeedback) return;

      setSubmittingFeedback(true);

      try {
        const helpfulValue = helpful ?? feedback ?? true;
        const isCommentSubmission = helpful === undefined;
        const commentValue = isCommentSubmission
          ? comment?.trim() || submittedComment
          : submittedComment;

        const response = await submitRagFeedback(
          trace_id,
          helpfulValue,
          commentValue,
          scoreId,
        );

        if (isCommentSubmission && comment?.trim()) {
          setSubmittedComment(comment.trim());
          setCommentPopoverOpen(false);
          setComment("");
        }

        toast.success(
          feedback == null
            ? "Thank you for your feedback!"
            : "Feedback updated",
        );
        setFeedback(helpfulValue);
        setScoreId(response.score_id);
      } catch {
        toast.error("Failed to submit feedback");
      } finally {
        setSubmittingFeedback(false);
      }
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
        <Popover open={commentPopoverOpen} onOpenChange={setCommentPopoverOpen}>
          <PopoverTrigger asChild>
            <Button variant="ghost" size="icon" disabled={!!submittedComment}>
              <MessageSquare
                className={cn(
                  "absolute h-4 w-4 transition-all duration-300",
                  submittedComment
                    ? "scale-50 opacity-0"
                    : "scale-100 opacity-100",
                )}
              />
              <MessageSquareText
                className={cn(
                  "absolute h-4 w-4 transition-all duration-300",
                  submittedComment
                    ? "scale-100 opacity-100"
                    : "scale-50 opacity-0",
                )}
              />
              <span className="sr-only">Submit a comment</span>
            </Button>
          </PopoverTrigger>
          <PopoverContent className="w-80">
            <div className="space-y-3">
              <h4 className="font-medium">Submit a comment</h4>
              <Textarea
                placeholder="Please share your thoughts about this response to help us improve"
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                className="min-h-[100px]"
              />
              <div className="flex justify-end gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setCommentPopoverOpen(false);
                    setComment("");
                  }}
                >
                  Cancel
                </Button>
                <Button
                  size="sm"
                  onClick={() => handleFeedback()}
                  disabled={submittingFeedback || !comment?.trim()}
                >
                  Submit
                </Button>
              </div>
            </div>
          </PopoverContent>
        </Popover>
        <Button
          variant="ghost"
          size="icon"
          className={cn(
            feedback === true &&
              "text-green-600 disabled:opacity-100 dark:text-green-400",
          )}
          onClick={() => handleFeedback(true)}
          disabled={submittingFeedback || feedback === true}
        >
          <ThumbsUp className="h-4 w-4" />
          <span className="sr-only">Helpful</span>
        </Button>
        <Button
          variant="ghost"
          size="icon"
          className={cn(
            feedback === false &&
              "text-red-600 disabled:opacity-100 dark:text-red-400",
          )}
          onClick={() => handleFeedback(false)}
          disabled={submittingFeedback || feedback === false}
        >
          <ThumbsDown className="h-4 w-4" />
          <span className="sr-only">Not helpful</span>
        </Button>
      </div>
    );
  };

  const TextContent = () => (
    <div className="prose prose-sm dark:prose-invert max-w-none">
      <div className="font-normal">{brief_answer}</div>
      {(!isCollapsible || isExpanded) && (
        <div className="mt-4">
          <p>{renderTextWithCitations(long_answer)}</p>
        </div>
      )}
    </div>
  );

  return (
    <div className="overflow-y-auto">
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
