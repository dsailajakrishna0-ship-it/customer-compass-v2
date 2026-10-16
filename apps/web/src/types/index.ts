/**
 * Shared frontend types, extracted from main.tsx so API/hook/component
 * layers can import them without depending on the top-level component file.
 */

export type Company = {
  id: number;
  name: string;
  industry: string;
  relationship_status: string;
  deal_count: number;
  interaction_count: number;
};

export type Deal = {
  id: number;
  name: string;
  amount: string;
  status: string;
  expected_close_date: string | null;
};

export type Contact = {
  id: number;
  full_name: string;
  job_title: string | null;
  email: string;
};

export type Interaction = {
  id: number;
  interaction_type: string;
  subject: string;
  occurred_at: string;
  summary: string;
};

export type Detail = Company & {
  website: string | null;
  contacts: Contact[];
  deals: Deal[];
  interactions: Interaction[];
};

export type Citation = {
  number: number;
  documentId: number;
  title: string;
  sourcePath: string;
  docType: string;
  companyName: string | null;
  similarity: number;
  snippet: string;
};

/** Structured CRM facts returned by POST /api/v1/chat/crm (Stage 5). Note: camelCase fields, unlike Deal above. */
export type DealFact = {
  id: number;
  name: string;
  amount: string;
  status: string;
  expectedCloseDate: string | null;
};

export type CrmFact = {
  id: number;
  name: string;
  industry: string;
  relationshipStatus: string;
  openDeals: DealFact[];
  wonDealsCount: number;
  lostDealsCount: number;
};

export type LlmProvider = "ollama" | "cloud";

/** "general" = Stage 2 plain chat, "rag" = Stage 3 document-grounded chat, "crm" = Stage 5 facts + citations. */
export type ChatMode = "general" | "rag" | "crm";

/** Stage 7: per-request telemetry (which provider/model actually answered,
 * token counts, latency, a rough cost estimate, and whether automatic
 * cross-provider fallback kicked in) returned alongside every chat answer. */
export type ChatUsage = {
  provider: LlmProvider;
  model: string;
  tokensIn: number | null;
  tokensOut: number | null;
  latencyMs: number;
  estimatedCost: number | null;
  fallbackUsed: boolean;
  fallbackFrom: LlmProvider | null;
};

export type ChatMessage = {
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  facts?: CrmFact | null;
  scopedCompany?: string | null;
  provider?: LlmProvider;
  usage?: ChatUsage;
};

export type ModelOption = { id: string; name: string };
export type ModelCatalog = { free: ModelOption[]; paid: ModelOption[] };

export type IngestSummary = {
  documentsProcessed?: number;
  chunksCreated?: number;
  status?: string;
  error?: string;
};

export type ChatResponse = {
  message?: string;
  error?: string;
  citations?: Citation[];
  facts?: CrmFact | null;
  scopedCompany?: string | null;
  provider?: LlmProvider;
  usage?: ChatUsage;
};
