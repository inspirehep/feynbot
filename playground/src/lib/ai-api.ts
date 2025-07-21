/**
 * Service for interacting with the AI API
 */
import { getInspireAiUrl } from "@/lib/utils";

type FeedbackResponse = {
  score_id: string;
};

/**
 * Submit feedback for a RAG response
 */
export async function submitRagFeedback(
  traceId: string,
  helpful: boolean,
  comment?: string,
  scoreId?: string,
): Promise<FeedbackResponse> {
  const response = await fetch(`${getInspireAiUrl()}/v1/rag-feedback`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      trace_id: traceId,
      helpful,
      comment,
      score_id: scoreId,
    }),
  });

  if (!response.ok) {
    throw new Error(`Failed to submit feedback: ${response.statusText}`);
  }

  return response.json();
}
