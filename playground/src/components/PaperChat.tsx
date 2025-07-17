import { usePaperChatHistory } from "@/hooks/usePaperChatHistory";
import { getInspireAiUrl } from "@/lib/utils";
import { FileSearch2, Lightbulb, Loader2, Send } from "lucide-react";
import { FormEvent, useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import Latex from "@/components/paper/Latex";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Loading } from "@/components/ui/loading";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";

import { ChatMessage, PaperDetails, QueryRequest } from "@/types";

interface PaperChatProps {
  activePaper: PaperDetails;
}

const PaperChat = ({ activePaper }: PaperChatProps) => {
  const [query, setQuery] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isPopoverOpen, setIsPopoverOpen] = useState(false);
  const scrollAreaRef = useRef<HTMLDivElement>(null);

  const { getChatHistory, updateChatHistory } = usePaperChatHistory();
  const chatHistory = getChatHistory(activePaper.id);

  const suggestedQuestions = [
    { label: "Summary", fullQuestion: "Provide a summary of this paper" },
    {
      label: "Contributions",
      fullQuestion: "What are the main contributions?",
    },
    { label: "Methodology", fullQuestion: "Explain the methodology used" },
    {
      label: "Limitations",
      fullQuestion: "What are the limitations mentioned?",
    },
    { label: "Conclusions", fullQuestion: "What are the key conclusions?" },
    {
      label: "Study Guide",
      fullQuestion: "Create a study guide for this paper",
    },
  ];

  useEffect(() => {
    if (scrollAreaRef.current) {
      scrollAreaRef.current.scrollTop = scrollAreaRef.current.scrollHeight;
    }
  }, [chatHistory]);

  const handlePaperSearch = async (searchQuery: string) => {
    if (!searchQuery.trim()) return;

    const userMessage: ChatMessage = {
      type: "user",
      content: searchQuery,
    };

    updateChatHistory(activePaper.id, [...chatHistory, userMessage]);
    setIsLoading(true);
    setQuery("");

    try {
      const requestBody: QueryRequest = {
        query: searchQuery,
        control_number: Number(activePaper.id),
        history: chatHistory,
      };

      const paperResponseData: { long_answer: string } = await fetch(
        `${getInspireAiUrl()}/v1/query-rag`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(requestBody),
        },
      ).then((res) => res.json());

      const assistantMessage: ChatMessage = {
        type: "assistant",
        content: paperResponseData.long_answer,
      };

      const updatedHistory = [...chatHistory, userMessage, assistantMessage];
      updateChatHistory(activePaper.id, updatedHistory);
    } catch {
      toast.error("Something went wrong. Please try again later.");
      updateChatHistory(activePaper.id, chatHistory);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSearch = async (e: FormEvent) => {
    e.preventDefault();
    await handlePaperSearch(query);
  };

  const handleSuggestedQuestion = async (question: string) => {
    setIsPopoverOpen(false);
    await handlePaperSearch(question);
  };

  const renderChatMessage = (message: ChatMessage, index: number) => (
    <div
      key={index}
      className={`mb-6 ${message.type === "user" ? "text-right" : "text-left"}`}
    >
      {message.type === "user" ? (
        <div className="bg-muted text-primary inline-block max-w-[80%] rounded-2xl px-4 py-3 text-sm">
          <div className="whitespace-pre-wrap">{message.content}</div>
        </div>
      ) : (
        <div className="max-w-[90%]">
          <div className="text-foreground prose prose-sm dark:prose-invert text-sm leading-relaxed">
            <Latex>{message.content}</Latex>
          </div>
        </div>
      )}
    </div>
  );

  const renderSuggestions = () => (
    <>
      <div className="mb-4 flex items-center justify-center gap-2">
        <Lightbulb className="h-4 w-4" />
        <h4 className="text-sm font-semibold">Quick Questions</h4>
      </div>
      <div className="grid grid-cols-2 gap-2">
        {suggestedQuestions.map((question, index) => (
          <Button
            key={index}
            type="button"
            variant="secondary"
            onClick={() => handleSuggestedQuestion(question.fullQuestion)}
            disabled={isLoading}
            className="font-normal"
          >
            {question.label}
          </Button>
        ))}
      </div>
    </>
  );

  return (
    <div className="flex h-full flex-col">
      <div className="flex-1 overflow-hidden">
        <div className="h-full overflow-y-auto p-4" ref={scrollAreaRef}>
          {chatHistory.length === 0 ? (
            <div className="flex h-full flex-col items-center justify-center gap-10 text-center">
              <div>
                <FileSearch2
                  className="mx-auto mb-4 h-12 w-12"
                  strokeWidth={1}
                />
                <p className="mb-1 text-base font-medium">
                  Ask questions about this paper
                </p>
                <p className="text-sm opacity-75">
                  Start a conversation to get specific insights and details
                </p>
              </div>
              <div className="rounded-xl border p-5">{renderSuggestions()}</div>
            </div>
          ) : (
            chatHistory.map(renderChatMessage)
          )}
          {isLoading && (
            <div className="mb-6">
              <Loading />
            </div>
          )}
        </div>
      </div>

      <form onSubmit={handleSearch} className="px-10 py-3">
        <div className="flex gap-2">
          <div className="relative flex-1">
            <Input
              type="text"
              placeholder="Ask questions about this paper..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className={`h-12 ${chatHistory.length > 0 ? "pr-12" : ""}`}
              disabled={isLoading}
            />
            {chatHistory.length > 0 && (
              <Popover open={isPopoverOpen} onOpenChange={setIsPopoverOpen}>
                <PopoverTrigger asChild>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    disabled={isLoading}
                    className="absolute top-1/2 right-2 h-8 w-8 -translate-y-1/2"
                  >
                    <Lightbulb className="h-4 w-4" />
                  </Button>
                </PopoverTrigger>
                <PopoverContent side="top" align="end" className="mb-4">
                  {renderSuggestions()}
                </PopoverContent>
              </Popover>
            )}
          </div>
          <Button
            type="submit"
            size="icon"
            disabled={isLoading || !query.trim()}
            className="h-12 w-12"
          >
            {isLoading ? <Loader2 className="animate-spin" /> : <Send />}
          </Button>
        </div>
      </form>
    </div>
  );
};

export default PaperChat;
