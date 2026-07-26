"use client";
import { useState } from "react";
import { FacebookIcon } from "@/components/icons/BrandIcons";
import { scrapeApi, jobsApi } from "@/lib/api";
import { JobTracker, URLInput } from "@/components/scrapers/JobTracker";
import { useToast } from "@/components/Providers";
import type { Job } from "@/types";

export default function FacebookPage() {
  const [url, setUrl] = useState("");
  const [maxPosts, setMaxPosts] = useState(30);
  const [includeReviews, setIncludeReviews] = useState(true);
  const [includeEvents, setIncludeEvents] = useState(true);
  const [loading, setLoading] = useState(false);
  const [job, setJob] = useState<Job | null>(null);
  const { addToast } = useToast();

  const handleStart = async () => {
    if (!url.trim()) { addToast("Please enter a Facebook URL", "error"); return; }
    setLoading(true);
    try {
      const res = await scrapeApi.facebook({ url: url.trim(), max_posts: maxPosts, include_reviews: includeReviews, include_events: includeEvents });
      if (res.success && res.data) { setJob(res.data as Job); addToast("Facebook scraper started!", "success"); }
      else addToast(res.message || "Failed", "error");
    } catch { addToast("Backend unreachable", "error"); }
    finally { setLoading(false); }
  };

  return (
    <div>
      <div className="page-header">
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{ width: 40, height: 40, borderRadius: 10, background: "#1877f2", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <FacebookIcon size={20} color="white" />
          </div>
          <div>
            <h1 className="page-title">Facebook Scraper</h1>
            <p className="page-subtitle">Extract page info, posts, reviews, events, and contact details</p>
          </div>
        </div>
      </div>
      <div className="page-body" style={{ display: "flex", flexDirection: "column", gap: 20 }}>
        <div className="card" style={{ padding: 24 }}>
          <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
            <URLInput value={url} onChange={setUrl} placeholder="https://www.facebook.com/pagename" label="Facebook Page URL" />
            <div>
              <label className="label">Max Posts</label>
              <input type="number" className="input" value={maxPosts} onChange={(e) => setMaxPosts(Number(e.target.value))} min={1} max={300} />
            </div>
            <div style={{ display: "flex", gap: 20 }}>
              <label className="checkbox-label">
                <input type="checkbox" checked={includeReviews} onChange={(e) => setIncludeReviews(e.target.checked)} />
                Include reviews & ratings
              </label>
              <label className="checkbox-label">
                <input type="checkbox" checked={includeEvents} onChange={(e) => setIncludeEvents(e.target.checked)} />
                Include events
              </label>
            </div>
            <button className="btn btn-primary btn-lg" onClick={handleStart} disabled={loading || !url} style={{ width: "100%", background: "#1877f2", boxShadow: "0 4px 15px rgba(24,119,242,0.3)" }}>
              {loading ? <><span className="pulse-dot" /> Starting…</> : <><FacebookIcon size={16} /> Scrape Facebook Page</>}
            </button>
          </div>
        </div>
        {job && <JobTracker job={job} onCancel={() => jobsApi.cancel(job.id)} onDelete={async () => { await jobsApi.delete(job.id); setJob(null); addToast("Job deleted.", "success"); }} />}
      </div>
    </div>
  );
}
