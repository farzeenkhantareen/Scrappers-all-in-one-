"use client";

import { useState } from "react";
import { MapPin } from "lucide-react";
import { scrapeApi, jobsApi } from "@/lib/api";
import { JobTracker, URLInput } from "@/components/scrapers/JobTracker";
import { useToast } from "@/components/Providers";
import type { Job, SortOrder } from "@/types";

export default function GoogleMapsPage() {
  const [url, setUrl] = useState("");
  const [businessName, setBusinessName] = useState("");
  const [maxReviews, setMaxReviews] = useState(100);
  const [sortOrder, setSortOrder] = useState<SortOrder>("newest");
  const [includeReplies, setIncludeReplies] = useState(true);
  const [loading, setLoading] = useState(false);
  const [job, setJob] = useState<Job | null>(null);
  const { addToast } = useToast();

  const handleStart = async () => {
    if (!url.trim()) { addToast("Please enter a Google Maps URL", "error"); return; }
    setLoading(true);
    try {
      const res = await scrapeApi.googleMaps({
        url: url.trim(),
        business_name: businessName || undefined,
        max_reviews: maxReviews,
        sort_order: sortOrder,
        include_owner_replies: includeReplies,
      });
      if (res.success && res.data) {
        setJob(res.data as Job);
        addToast("Google Maps scraper started!", "success");
      } else addToast(res.message || "Failed", "error");
    } catch { addToast("Backend unreachable", "error"); }
    finally { setLoading(false); }
  };

  return (
    <div>
      <div className="page-header">
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{ width: 40, height: 40, borderRadius: 10, background: "linear-gradient(135deg, #f43f5e, #fb7185)", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <MapPin size={20} color="white" />
          </div>
          <div>
            <h1 className="page-title">Google Maps Reviews</h1>
            <p className="page-subtitle">Extract all reviews, business info, ratings, and owner replies</p>
          </div>
        </div>
      </div>
      <div className="page-body" style={{ display: "flex", flexDirection: "column", gap: 20 }}>
        <div className="card" style={{ padding: 24 }}>
          <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
            <URLInput value={url} onChange={setUrl} placeholder="https://maps.google.com/..." label="Google Maps URL" />
            <div>
              <label className="label">Business Name (optional)</label>
              <input type="text" className="input" value={businessName} onChange={(e) => setBusinessName(e.target.value)} placeholder="e.g. Starbucks Downtown" />
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
              <div>
                <label className="label">Max Reviews</label>
                <input type="number" className="input" value={maxReviews} onChange={(e) => setMaxReviews(Number(e.target.value))} min={1} max={5000} />
              </div>
              <div>
                <label className="label">Sort Order</label>
                <select className="input" value={sortOrder} onChange={(e) => setSortOrder(e.target.value as SortOrder)}>
                  <option value="newest">Newest First</option>
                  <option value="highest">Highest Rating</option>
                  <option value="lowest">Lowest Rating</option>
                  <option value="relevant">Most Relevant</option>
                </select>
              </div>
            </div>
            <label className="checkbox-label">
              <input type="checkbox" checked={includeReplies} onChange={(e) => setIncludeReplies(e.target.checked)} />
              Include owner replies
            </label>
            <button className="btn btn-primary btn-lg" onClick={handleStart} disabled={loading || !url} style={{ width: "100%" }}>
              {loading ? <><span className="pulse-dot" /> Starting…</> : <><MapPin size={16} /> Scrape Reviews</>}
            </button>
          </div>
        </div>

        {/* Info cards */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12 }}>
          {[
            { label: "Business Name", desc: "Company name, category, address" },
            { label: "Ratings & Reviews", desc: "All reviews with pagination support" },
            { label: "Business Details", desc: "Phone, website, hours, coordinates" },
          ].map((item) => (
            <div key={item.label} className="card" style={{ padding: 16 }}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 4 }}>{item.label}</div>
              <div style={{ fontSize: 12, color: "var(--text-muted)" }}>{item.desc}</div>
            </div>
          ))}
        </div>

        {job && <JobTracker job={job} onCancel={() => jobsApi.cancel(job.id)} onDelete={async () => { await jobsApi.delete(job.id); setJob(null); addToast("Job deleted.", "success"); }} />}
      </div>
    </div>
  );
}
