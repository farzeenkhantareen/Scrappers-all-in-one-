/**
 * Centralized API client using axios.
 * All requests go through the FastAPI backend at NEXT_PUBLIC_API_URL.
 */

import axios from "axios";
import type {
  APIResponse,
  DashboardStats,
  Job,
  JobsListResponse,
  GeneralScrapeRequest,
  WebsiteScrapeRequest,
  GoogleMapsScrapeRequest,
  InstagramScrapeRequest,
  LinkedInScrapeRequest,
  FacebookScrapeRequest,
  ExportFormat,
  ExportFile,
  LogEntry,
} from "@/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const api = axios.create({
  baseURL: API_URL,
  timeout: 180000, // 3 minutes for live scraping operations
  headers: { "Content-Type": "application/json" },
});

// ─────────────────────────────────────────────────────────────────────────────
// Helper
// ─────────────────────────────────────────────────────────────────────────────
async function request<T>(
  method: "get" | "post" | "delete",
  path: string,
  data?: unknown,
  params?: Record<string, unknown>
): Promise<APIResponse<T>> {
  const res = await api.request<APIResponse<T>>({ method, url: path, data, params });
  return res.data;
}

// ─────────────────────────────────────────────────────────────────────────────
// Dashboard
// ─────────────────────────────────────────────────────────────────────────────
export const dashboardApi = {
  getStats: () => request<DashboardStats>("get", "/api/jobs/stats"),
};

// ─────────────────────────────────────────────────────────────────────────────
// Jobs
// ─────────────────────────────────────────────────────────────────────────────
export const jobsApi = {
  list: (params?: { status?: string; type?: string; limit?: number; offset?: number }) =>
    request<JobsListResponse>("get", "/api/jobs", undefined, params),
  get: (jobId: string) => request<Job>("get", `/api/jobs/${jobId}`),
  cancel: (jobId: string) => request<void>("post", `/api/jobs/${jobId}/cancel`),
  pause: (jobId: string) => request<void>("post", `/api/jobs/${jobId}/pause`),
  resume: (jobId: string) => request<void>("post", `/api/jobs/${jobId}/resume`),
  delete: (jobId: string) => request<void>("delete", `/api/jobs/${jobId}`),
};

// ─────────────────────────────────────────────────────────────────────────────
// Scrapers
// ─────────────────────────────────────────────────────────────────────────────
export const scrapeApi = {
  general: (body: GeneralScrapeRequest) => request<Job>("post", "/api/scrape/general", body),
  website: (body: WebsiteScrapeRequest) => request<Job>("post", "/api/scrape/website", body),
  googleMaps: (body: GoogleMapsScrapeRequest) => request<Job>("post", "/api/scrape/google-maps", body),
  instagram: (body: InstagramScrapeRequest) => request<Job>("post", "/api/scrape/instagram", body),
  linkedin: (body: LinkedInScrapeRequest) => request<Job>("post", "/api/scrape/linkedin", body),
  facebook: (body: FacebookScrapeRequest) => request<Job>("post", "/api/scrape/facebook", body),
};

// ─────────────────────────────────────────────────────────────────────────────
// Results
// ─────────────────────────────────────────────────────────────────────────────
export const resultsApi = {
  get: (jobId: string) => request<unknown>("get", `/api/results/${jobId}`),
};

// ─────────────────────────────────────────────────────────────────────────────
// Exports
// ─────────────────────────────────────────────────────────────────────────────
export const exportsApi = {
  list: () => request<ExportFile[]>("get", "/api/exports"),
  create: (jobId: string, format: ExportFormat, customName?: string) =>
    request<{ file: string; path: string; size: number }>(
      "post",
      "/api/exports",
      undefined,
      { job_id: jobId, format, ...(customName?.trim() ? { custom_name: customName.trim() } : {}) }
    ),
  clear: () => request<void>("delete", "/api/exports/clear"),
  downloadUrl: (filename: string) => `${API_URL}/api/exports/download/${filename}`,
};

// ─────────────────────────────────────────────────────────────────────────────
// Logs
// ─────────────────────────────────────────────────────────────────────────────
export const logsApi = {
  getForJob: (jobId: string, params?: { level?: string; limit?: number }) =>
    request<LogEntry[]>("get", `/api/logs/${jobId}`, undefined, params),
  getAll: (params?: { level?: string; limit?: number }) =>
    request<LogEntry[]>("get", "/api/logs", undefined, params),
};

// ─────────────────────────────────────────────────────────────────────────────
// Health check
// ─────────────────────────────────────────────────────────────────────────────
export const healthApi = {
  check: () => request<{ status: string }>("get", "/api/health"),
};

// ─────────────────────────────────────────────────────────────────────────────
// AI Assistant
// ─────────────────────────────────────────────────────────────────────────────
export interface AIChatRequest {
  message: string;
  session_id?: string;
  max_reviews?: number;
}

export interface AIChatResponse {
  reply: string;
  session_id: string;
  scraped_place?: Record<string, any>;
  job_id?: string;
}

export const aiApi = {
  chat: (body: AIChatRequest) => request<AIChatResponse>("post", "/api/ai/chat", body),
};

export const WS_URL = API_URL.replace(/^http/, "ws");
