import { useState, type FormEvent } from "react";
import { sendChat } from "../api/chat";
import { useChatSession } from "../context/ChatSessionContext";
import type { ChatMessage, LlmProvider } from "../types";

/** Chat input + send logic, wired to the active ChatSessionContext (mode/provider/model/history). */
export function useChat(): {
  question: string;
  setQuestion: (value: string) => void;
  isAsking: boolean;
  askQuestion: (event: FormEvent<HTMLFormElement>) => void;
} {
  const { chatMode, provider, cloudModel, messages, setMessages } = useChatSession();
  const [question, setQuestion] = useState("");
  const [isAsking, setIsAsking] = useState(false);

  function askQuestion(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const text = question.trim();
    if (!text || isAsking) return;
    const history = [...messages, { role: "user" as const, content: text }];
    setMessages(history);
    setQuestion("");
    setIsAsking(true);

    const requestBody: { messages: ChatMessage[]; provider: LlmProvider; model?: string } = {
      messages: history.slice(-12),
      provider,
    };
    if (provider === "cloud" && cloudModel) requestBody.model = cloudModel;

    sendChat(chatMode, requestBody)
      .then((body) => {
        setMessages((current) => [
          ...current,
          {
            role: "assistant",
            content: body.message ?? body.error ?? "Something went wrong.",
            citations: body.citations,
            facts: body.facts,
            scopedCompany: body.scopedCompany,
            provider: body.provider,
            usage: body.usage,
          },
        ]);
      })
      .catch(() => {
        setMessages((current) => [
          ...current,
          { role: "assistant", content: "I could not reach the API. Check that the local services are running." },
        ]);
      })
      .finally(() => setIsAsking(false));
  }

  return { question, setQuestion, isAsking, askQuestion };
}
