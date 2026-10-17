import type { ChatMessage } from "../../types";
import { CrmFactsPanel } from "./CrmFactsPanel";
import { CitationList } from "./CitationList";

/** Stage 7: renders the per-answer telemetry footer (provider/model, tokens,
 * latency, estimated cost) plus a visible note when automatic cross-provider
 * fallback kicked in, so a provider outage is obvious rather than silent. */
function UsageFootnote({ usage }: { usage: NonNullable<ChatMessage["usage"]> }) {
  const tokenPart =
    usage.tokensIn != null && usage.tokensOut != null ? `${usage.tokensIn}→${usage.tokensOut} tokens` : null;
  const costPart = usage.estimatedCost != null ? `$${usage.estimatedCost.toFixed(4)}` : null;
  const parts = [usage.model, `${usage.latencyMs}ms`, tokenPart, costPart].filter(Boolean);
  return (
    <>
      <p className="usage-tag">{parts.join(" · ")}</p>
      {usage.fallbackUsed && (
        <p className="usage-fallback-tag">
          ⚠ {usage.fallbackFrom === "cloud" ? "Cloud (OpenRouter)" : "Local (Ollama)"} was unavailable — answered via{" "}
          {usage.provider === "cloud" ? "Cloud (OpenRouter)" : "Local (Ollama)"} instead.
        </p>
      )}
    </>
  );
}

/** Stage 8: renders a visible warning when the prompt-injection guardrail
 * flagged and neutralized something (in the user's message or a retrieved
 * document), so a detected attempt is obvious rather than silently handled. */
function GuardrailWarning({ guardrail }: { guardrail: NonNullable<ChatMessage["guardrail"]> }) {
  if (!guardrail.flagged) return null;
  return (
    <p className="usage-fallback-tag" title={guardrail.reasons.join(", ")}>
      ⚠ Potential prompt injection detected and neutralized before answering.
    </p>
  );
}

/** A single chat bubble: message text, optional provider tag, optional CRM facts panel, optional citations. */
export function MessageBubble({ message }: { message: ChatMessage }) {
  return (
    <div className={`message ${message.role}`}>
      <p>{message.content}</p>
      {message.role === "assistant" && message.provider && (
        <p className="provider-tag">via {message.provider === "cloud" ? "Cloud (OpenRouter)" : "Local (Ollama)"}</p>
      )}
      {message.role === "assistant" && message.usage && <UsageFootnote usage={message.usage} />}
      {message.role === "assistant" && message.guardrail && <GuardrailWarning guardrail={message.guardrail} />}
      {message.scopedCompany && <p className="provider-tag">Scoped to: {message.scopedCompany}</p>}
      {message.facts && <CrmFactsPanel facts={message.facts} />}
      {message.citations && message.citations.length > 0 && <CitationList citations={message.citations} />}
    </div>
  );
}
