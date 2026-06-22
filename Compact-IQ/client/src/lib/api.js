export const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

export async function apiRequest(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: options.body instanceof FormData
      ? options.headers
      : { "Content-Type": "application/json", ...(options.headers || {}) },
  });

  if (!response.ok) {
    const text = await response.text();
    let message = text;
    try {
      const parsed = JSON.parse(text);
      message = parsed?.error?.message || parsed?.detail?.message || parsed?.detail || text;
    } catch {
      // Keep the plain-text response.
    }
    throw new Error(message || `Request failed: ${response.status}`);
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
}

export const documentApi = {
  list: () => apiRequest("/api/documents"),
  upload: (formData) => apiRequest("/api/documents/upload", { method: "POST", body: formData }),
  get: (documentId) => apiRequest(`/api/documents/${documentId}`),
  profile: (documentId) => apiRequest(`/api/documents/${documentId}/profile`, { method: "POST" }),
  extract: (documentId) => apiRequest(`/api/documents/${documentId}/extract`, { method: "POST" }),
  extractRules: (documentId) => apiRequest(`/api/documents/${documentId}/extract-rules`, { method: "POST" }),
  normalizeCandidates: (documentId) => apiRequest(`/api/documents/${documentId}/normalize-rule-candidates`, { method: "POST" }),
  runPipeline: (documentId) => apiRequest(`/api/documents/${documentId}/run-docintel-pipeline`, { method: "POST" }),
  chunks: (documentId, query = {}) => {
    const params = new URLSearchParams();
    Object.entries(query).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== "" && value !== "All") {
        params.set(key, value);
      }
    });
    const suffix = params.toString() ? `?${params.toString()}` : "";
    return apiRequest(`/api/documents/${documentId}/chunks${suffix}`);
  },
  candidates: (documentId) => apiRequest(`/api/documents/${documentId}/rule-candidates`),
  exports: (documentId) => apiRequest(`/api/documents/${documentId}/exports`),
  summary: (documentId) => apiRequest(`/api/documents/${documentId}/intelligence-summary`),
};

export const getDocuments = documentApi.list;
export const uploadDocument = documentApi.upload;
export const getDocument = documentApi.get;
export const getDocumentIntelligenceSummary = documentApi.summary;
export const runFullPipeline = documentApi.runPipeline;
export const profileDocument = documentApi.profile;
export const extractDocument = documentApi.extract;
export const extractRules = documentApi.extractRules;
export const getDocumentChunks = documentApi.chunks;
export const getDocumentRuleCandidates = documentApi.candidates;
export const getDocumentExports = documentApi.exports;

export const candidateApi = {
  list: () => apiRequest("/api/rule-candidates"),
  get: (candidateId) => apiRequest(`/api/rule-candidates/${candidateId}`),
  securityImpact: (payload) =>
    apiRequest("/api/security/cve-enrichment", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  review: (candidateId, reviewStatus, { notes = "", tier = null, auto_approved = null, rejection_reason = null } = {}) =>
    apiRequest(`/api/rule-candidates/${candidateId}/review`, {
      method: "PATCH",
      body: JSON.stringify({
        review_status: reviewStatus,
        reviewed_by: "document_intelligence_reviewer",
        notes,
        ...(tier !== null && { tier }),
        ...(auto_approved !== null && { auto_approved }),
        ...(rejection_reason !== null && { rejection_reason }),
      }),
    }),
  bulkReview: (updates) =>
    apiRequest(`/api/rule-candidates/bulk-review`, {
      method: "POST",
      body: JSON.stringify({ updates }),
    }),
};


export const updateCandidateReview = candidateApi.review;

export const chunkApi = {
  get: (chunkId) => apiRequest(`/api/chunks/${chunkId}`),
};
