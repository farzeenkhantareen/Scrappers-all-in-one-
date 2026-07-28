"use client";
import { useState } from "react";
import { LinkedinIcon } from "@/components/icons/BrandIcons";
import { scrapeApi, jobsApi } from "@/lib/api";
import { JobTracker, URLInput } from "@/components/scrapers/JobTracker";
import { useToast } from "@/components/Providers";
import type { Job } from "@/types";

export default function LinkedInPage() {
  const [url, setUrl] = useState("");
  const [maxPosts, setMaxPosts] = useState(20);
  const [includeJobs, setIncludeJobs] = useState(true);
  const [includeEmployees, setIncludeEmployees] = useState(true);
  const [loading, setLoading] = useState(false);
  const [job, setJob] = useState<Job | null>(null);
  const { addToast } = useToast();

  const handleStart = async () => {
    if (!url.trim()) { addToast("Please enter a LinkedIn URL", "error"); return; }
    setLoading(true);
    try {
      const res = await scrapeApi.linkedin({ url: url.trim(), max_posts: maxPosts, include_jobs: includeJobs, include_employees: includeEmployees });
      if (res.success && res.data) { setJob(res.data as Job); addToast("LinkedIn scraper started!", "success"); }
      else addToast(res.message || "Failed", "error");
    } catch { addToast("Backend unreachable", "error"); }
    finally { setLoading(false); }
  };

  return (
    <div>
      <div className="page-header">
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{ width: 40, height: 40, borderRadius: 10, background: "#0077b5", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <LinkedinIcon size={20} color="white" />
          </div>
          <div>
            <h1 className="page-title">LinkedIn Scraper</h1>
            <p className="page-subtitle">Extract company info, posts, employees, and job listings</p>
          </div>
        </div>
      </div>
      <div className="page-body" style={{ display: "flex", flexDirection: "column", gap: 20 }}>
        <div className="card" style={{ padding: 24 }}>
          <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
            <URLInput value={url} onChange={setUrl} placeholder="https://www.linkedin.com/company/example/" label="LinkedIn Company Page URL" />
            <div>
              <label className="label">Max Posts</label>
              <input type="number" className="input" value={maxPosts} onChange={(e) => setMaxPosts(Number(e.target.value))} min={1} max={200} />
            </div>
            <div style={{ display: "flex", gap: 20 }}>
              <label className="checkbox-label">
                <input type="checkbox" checked={includeJobs} onChange={(e) => setIncludeJobs(e.target.checked)} />
                Include job listings
              </label>
              <label className="checkbox-label">
                <input type="checkbox" checked={includeEmployees} onChange={(e) => setIncludeEmployees(e.target.checked)} />
                Include employee count
              </label>
            </div>
            <button className="btn btn-primary btn-lg" onClick={handleStart} disabled={loading || !url} style={{ width: "100%", background: "#0077b5", boxShadow: "0 4px 15px rgba(0,119,181,0.3)" }}>
              {loading ? <><span className="pulse-dot" /> Starting…</> : <><LinkedinIcon size={16} /> Scrape Company Page</>}
            </button>
          </div>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12 }}>
          {["Company Info", "About & Specialties", "Recent Posts", "Job Listings"].map((label) => (
            <div key={label} className="card" style={{ padding: 14, textAlign: "center", fontSize: 13, fontWeight: 500, color: "var(--text-secondary)" }}>{label}</div>
          ))}
        </div>
        {job && <JobTracker job={job} onCancel={() => jobsApi.cancel(job.id)} onDelete={async () => { await jobsApi.delete(job.id); setJob(null); addToast("Job deleted.", "success"); }} />}
      </div>
    </div>
  );
}
