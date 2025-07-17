import { useState } from "react";

import { ChatMessage } from "@/types";

interface UsePaperChatHistoryReturn {
  getChatHistory: (paperId: string) => ChatMessage[];
  updateChatHistory: (paperId: string, messages: ChatMessage[]) => void;
  clearHistory: (paperId: string) => void;
  clearAllHistories: () => void;
}

export const usePaperChatHistory = (): UsePaperChatHistoryReturn => {
  const [paperChatHistories, setPaperChatHistories] = useState<
    Record<string, ChatMessage[]>
  >({});

  const getChatHistory = (paperId: string): ChatMessage[] => {
    return paperChatHistories[paperId] || [];
  };

  const updateChatHistory = (paperId: string, messages: ChatMessage[]) => {
    setPaperChatHistories((prev) => ({
      ...prev,
      [paperId]: messages,
    }));
  };

  const clearHistory = (paperId: string) => {
    setPaperChatHistories((prev) => {
      const updated = { ...prev };
      delete updated[paperId];
      return updated;
    });
  };

  const clearAllHistories = () => {
    setPaperChatHistories({});
  };

  return {
    getChatHistory,
    updateChatHistory,
    clearHistory,
    clearAllHistories,
  };
};
