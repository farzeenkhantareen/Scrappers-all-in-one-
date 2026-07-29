"use client";

import { useState } from "react";
import { Globe } from "lucide-react";
import { scrapeApi, jobsApi } from "@/lib/api";
import { JobTracker, URLInput } from "@/components/scrapers/JobTracker";
import { useToast } from "@/components/Providers";
import type { Job } from "@/types";

const EXTRACT_OPTIONS = [
  ["extract_emails", "Email addresses"],
  ["extract_phones", "Phone numbers"],
  ["extract_addresses", "Physical addresses"],
  ["extract_schema_org", "Schema.org structured data"],
  ["extract_open_graph", "Open Graph metadata"],
  ["extract_social_links", "Social media links"],
  ["extract_headings", "Page headings (H1–H6)"],
  ["extract_blog_articles", "Blog articles"],
  ["extract_products", "Products"],
  ["extract_services", "Services"],
  ["extract_faqs", "FAQs"],
  ["extract_testimonials", "Testimonials"],
  ["extract_contacts", "Contact information"],
  ["download_images", "Download images"],
  ["download_pdfs", "Download PDFs"],
  ["follow_redirects", "Follow redirects"],
  ["respect_robots", "Respect robots.txt"],
];

export default function WebsiteScraperPage() {
  const [url, setUrl] = useState("");
  const [maxPages, setMaxPages] = useState(100);
  const [maxDepth, setMaxDepth] = useState(5);
  const [options, setOptions] = useState<Record<string, boolean>>({
    extract_emails: true,
    extract_phones: true,
    extract_addresses: true,
    extract_schema_org: true,
    extract_open_graph: true,
    extract_social_links: true,
    extract_headings: true,
    follow_redirects: true,
    respect_robots: true,
  });
  const [loading, setLoading] = useState(false);
  const [job, setJob] = useState<Job | null>(null);
  const { addToast } = useToast();

  const toggle = (key: string) => setOptions((p) => ({ ...p, [key]: !p[key] }));

  const handleStart = async () => {
    if (!url.trim()) { addToast("Please enter a URL", "error"); return; }
    setLoading(true);
    try {
      const res = await scrapeApi.website({ url: url.trim(), max_pages: maxPages, max_depth: maxDepth, ...options });
      if (res.success && res.data) {
        setJob(res.data as Job);
        addToast("Website scraper started!", "success");
      } else {
        addToast(res.message || "Failed", "error");
      }
    } catch {
      addToast("Backend unreachable", "error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div className="page-header">
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{ width: 40, height: 40, borderRadius: 10, background: "linear-gradient(135deg, #06b6d4, #3b82f6)", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <Globe size={20} color="white" />
          </div>
          <div>
            <h1 className="page-title">Website Scraper</h1>
            <p className="page-subtitle">Recursively crawl and extract all data from any website</p>
          </div>
        </div>
      </div>
      <div className="page-body" style={{ display: "flex", flexDirection: "column", gap: 20 }}>
        <div className="card" style={{ padding: 24 }}>
          <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
            <URLInput value={url} onChange={setUrl} placeholder="https://example.com" label="Website URL" />
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
              <div>
                <label className="label">Max Pages</label>
                <input type="number" className="input" value={maxPages} onChange={(e) => setMaxPages(Number(e.target.value))} min={1} max={10000} />
              </div>
              <div>
                <label className="label">Max Crawl Depth</label>
                <input type="number" className="input" value={maxDepth} onChange={(e) => setMaxDepth(Number(e.target.value))} min={1} max={20} />
              </div>
            </div>
            <div>
              <label className="label" style={{ marginBottom: 12 }}>Extraction Options</label>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 4 }}>
                {EXTRACT_OPTIONS.map(([key, label]) => (
                  <label key={key} className="checkbox-label">
                    <input type="checkbox" checked={!!options[key]} onChange={() => toggle(key)} />
                    {label}
                  </label>
                ))}
              </div>
            </div>
            <button className="btn btn-primary btn-lg" onClick={handleStart} disabled={loading || !url} style={{ width: "100%" }}>
              {loading ? <><span className="pulse-dot" /> Starting…</> : <><Globe size={16} /> Start Website Crawl</>}
            </button>
          </div>
        </div>
        {job && <JobTracker job={job} onCancel={() => jobsApi.cancel(job.id)} onDelete={async () => { await jobsApi.delete(job.id); setJob(null); addToast("Job deleted.", "success"); }} />}
      </div>
    </div>
  );
}
