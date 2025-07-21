import { ReactNode, createContext, useContext, useState } from "react";

type FeedbackState = {
  feedback: boolean | null;
  scoreId?: string;
  submittingFeedback: boolean;
  submittedComment: string;
};

type FeedbackContextType = {
  feedbackState: FeedbackState;
  setFeedback: (feedback: boolean | null) => void;
  setScoreId: (scoreId: string) => void;
  setSubmittingFeedback: (submitting: boolean) => void;
  setSubmittedComment: (comment: string) => void;
  resetFeedback: () => void;
};

// Using a context in order to share feedback state across components
// (i.e different instances of ResponseView)
const FeedbackContext = createContext<FeedbackContextType | undefined>(
  undefined,
);

const defaultFeedbackState: FeedbackState = {
  feedback: null,
  submittingFeedback: false,
  submittedComment: "",
};

interface FeedbackProviderProps {
  children: ReactNode;
}

export function FeedbackProvider({ children }: FeedbackProviderProps) {
  const [feedbackState, setFeedbackState] =
    useState<FeedbackState>(defaultFeedbackState);

  const setFeedback = (feedback: boolean | null) => {
    setFeedbackState((prev) => ({ ...prev, feedback }));
  };

  const setScoreId = (scoreId: string) => {
    setFeedbackState((prev) => ({ ...prev, scoreId }));
  };

  const setSubmittingFeedback = (submitting: boolean) => {
    setFeedbackState((prev) => ({ ...prev, submittingFeedback: submitting }));
  };

  const setSubmittedComment = (comment: string) => {
    setFeedbackState((prev) => ({ ...prev, submittedComment: comment }));
  };

  const resetFeedback = () => {
    setFeedbackState(defaultFeedbackState);
  };

  const value: FeedbackContextType = {
    feedbackState,
    setFeedback,
    setScoreId,
    setSubmittingFeedback,
    setSubmittedComment,
    resetFeedback,
  };

  return (
    <FeedbackContext.Provider value={value}>
      {children}
    </FeedbackContext.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useFeedback() {
  const context = useContext(FeedbackContext);
  if (context === undefined) {
    throw new Error("useFeedback must be used within a FeedbackProvider");
  }
  return context;
}
