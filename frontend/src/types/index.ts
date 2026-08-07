/**
 * TypeScript types for the entire Scrappers Dashboard application.
 */

// ─────────────────────────────────────────────────────────────────────────────
// Enums
// ─────────────────────────────────────────────────────────────────────────────
export type JobStatus = "queued" | "running" | "paused" | "completed" | "failed" | "cancelled";
export type JobType = "general" | "website" | "google_maps" | "instagram" | "linkedin" | "facebook";
export type ExportFormat = "csv" | "json" | "excel" | "xml" | "pdf" | "zip";
export type LogLevel = "debug" | "info" | "warning" | "error" | "critical";
export type SortOrder = "newest" | "highest" | "lowest" | "relevant";

// ─────────────────────────────────────────────────────────────────────────────
// Job
// ─────────────────────────────────────────────────────────────────────────────
export interface Job {
  id: string;
  type: JobType;
  status: JobStatus;
  target_url: string;
  config: Record<string, unknown>;
  progress_pct: number;
  scraped_pages?: number;
  total_pages?: number;
  items_found: number;
  current_url?: string;
  elapsed_seconds?: number;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  error_message?: string;
  celery_task_id?: string;
  parent_job_id?: string;
}

export interface JobsListResponse {
  jobs: Job[];
  total: number;
  limit: number;
  offset: number;
}

// ─────────────────────────────────────────────────────────────────────────────
// Dashboard
// ─────────────────────────────────────────────────────────────────────────────
export interface DashboardStats {
  total_jobs: number;
  active_jobs: number;
  completed_jobs: number;
  failed_jobs: number;
  queued_jobs: number;
  total_pages_scraped: number;
  total_businesses: number;
  total_reviews: number;
  total_social_profiles: number;
  jobs_by_type: Record<string, number>;
  jobs_by_status: Record<string, number>;
  recent_jobs: Job[];
}

// ─────────────────────────────────────────────────────────────────────────────
// Scraper Requests
// ─────────────────────────────────────────────────────────────────────────────
export interface GeneralScrapeRequest {
  url: string;
  max_pages?: number;
  max_depth?: number;
  auto_launch_social?: boolean;
  download_images?: boolean;
  download_pdfs?: boolean;
  respect_robots?: boolean;
}

export interface WebsiteScrapeRequest {
  url: string;
  max_pages?: number;
  max_depth?: number;
  follow_redirects?: boolean;
  download_images?: boolean;
  download_pdfs?: boolean;
  extract_emails?: boolean;
  extract_phones?: boolean;
  extract_addresses?: boolean;
  extract_schema_org?: boolean;
  extract_open_graph?: boolean;
  extract_social_links?: boolean;
  extract_headings?: boolean;
  extract_blog_articles?: boolean;
  extract_products?: boolean;
  extract_services?: boolean;
  extract_faqs?: boolean;
  extract_testimonials?: boolean;
  extract_contacts?: boolean;
  respect_robots?: boolean;
}

export interface GoogleMapsScrapeRequest {
  url: string;
  business_name?: string;
  place_id?: string;
  max_reviews?: number;
  sort_order?: SortOrder;
  include_owner_replies?: boolean;
}

export interface InstagramScrapeRequest {
  url: string;
  max_posts?: number;
  download_media?: boolean;
  include_reels?: boolean;
}

export interface LinkedInScrapeRequest {
  url: string;
  max_posts?: number;
  include_jobs?: boolean;
  include_employees?: boolean;
}

export interface FacebookScrapeRequest {
  url: string;
  max_posts?: number;
  include_reviews?: boolean;
  include_events?: boolean;
}

// ─────────────────────────────────────────────────────────────────────────────
// Results
// ─────────────────────────────────────────────────────────────────────────────
export interface ScrapedPage {
  url: string;
  title: string;
  meta_title?: string;
  meta_description?: string;
  h1?: string;
  emails: string[];
  phones: string[];
  social_links: Record<string, string[]>;
  images: Array<{ src: string; alt: string }>;
  word_count: number;
  crawl_depth: number;
  status_code?: number;
}

export interface Review {
  reviewer_name: string;
  reviewer_photo?: string;
  rating: number;
  text: string;
  review_date: string;
  owner_reply?: string;
  images?: string[];
}

export interface Business {
  name: string;
  category: string;
  rating?: number;
  total_reviews?: number;
  address?: string;
  phone?: string;
  website?: string;
  opening_hours?: Record<string, string>;
  reviews?: Review[];
}

export interface SocialProfile {
  platform: string;
  profile_url: string;
  username?: string;
  display_name?: string;
  bio?: string;
  followers?: number;
  following?: number;
  posts_count?: number;
  profile_picture?: string;
  posts?: unknown[];
}

// ─────────────────────────────────────────────────────────────────────────────
// Logs
// ─────────────────────────────────────────────────────────────────────────────
export interface LogEntry {
  id?: string;
  job_id: string;
  level: LogLevel;
  message: string;
  context?: Record<string, unknown>;
  timestamp: string;
}

// ─────────────────────────────────────────────────────────────────────────────
// WebSocket Events
// ─────────────────────────────────────────────────────────────────────────────
export interface WSProgressEvent {
  type: "progress";
  job_id: string;
  progress_pct: number;
  scraped_pages: number;
  total_pages: number;
  items_found: number;
  current_url: string;
  elapsed_seconds: number;
}

export interface WSStatusEvent {
  type: "status";
  job_id: string;
  status: JobStatus;
  error?: string;
}

export interface WSLogEvent extends LogEntry {
  type: "log";
}

export type WSEvent = WSProgressEvent | WSStatusEvent | WSLogEvent;

// ─────────────────────────────────────────────────────────────────────────────
// API Response wrapper
// ─────────────────────────────────────────────────────────────────────────────
export interface APIResponse<T = unknown> {
  success: boolean;
  message: string;
  data: T | null;
}

// ─────────────────────────────────────────────────────────────────────────────
// Exports
// ─────────────────────────────────────────────────────────────────────────────
export interface ExportFile {
  filename: string;
  size: number;
  created_at: number;
  format?: ExportFormat;
}
