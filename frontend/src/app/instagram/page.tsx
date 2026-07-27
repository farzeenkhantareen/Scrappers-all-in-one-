"use client";
import { useState } from "react";
import { InstagramIcon } from "@/components/icons/BrandIcons";
import { scrapeApi, jobsApi } from "@/lib/api";
import { JobTracker } from "@/components/scrapers/JobTracker";
import { useToast } from "@/components/Providers";
import type { Job } from "@/types";

export default function InstagramPage() {
  const [url, setUrl] = useState("");
  const [maxPosts, setMaxPosts] = useState(50);
  const [downloadMedia, setDownloadMedia] = useState(false);
  const [includeReels, setIncludeReels] = useState(true);
  const [loading, setLoading] = useState(false);
  const [job, setJob] = useState<Job | null>(null);
  const { addToast } = useToast();

  const handleStart = async () => {
    if (!url.trim()) { addToast("Please enter an Instagram Username or Profile URL", "error"); return; }
    setLoading(true);
    try {
      const res = await scrapeApi.instagram({ url: url.trim(), max_posts: maxPosts, download_media: downloadMedia, include_reels: includeReels });
      if (res.success && res.data) { setJob(res.data as Job); addToast("Instagram scraper started!", "success"); }
      else addToast(res.message || "Failed", "error");
    } catch { addToast("Backend unreachable", "error"); }
    finally { setLoading(false); }
  };

  const fields = ["Username & Display Name", "Bio & Contact Info", "Followers / Following / Posts", "Profile Picture", "External Links & Email", "Recent Posts & Captions", "Hashtags from Captions", "Post Images & Videos", "Reels (if enabled)", "Post Timestamps"];

  return (
    <div>
      <div className="page-header">
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{ width: 40, height: 40, borderRadius: 10, background: "linear-gradient(135deg, #e1306c, #f58529)", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <InstagramIcon size={20} color="white" />
          </div>
          <div>
            <h1 className="page-title">Instagram Scraper</h1>
            <p className="page-subtitle">Extract profile data, posts, reels, hashtags, and media</p>
          </div>
        </div>
      </div>
      <div className="page-body" style={{ display: "flex", flexDirection: "column", gap: 20 }}>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 280px", gap: 20 }}>
          <div className="card" style={{ padding: 24 }}>
            <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
              <div>
                <label className="label">Instagram Username or Profile URL</label>
                <input
                  type="text"
                  className="input input-lg"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  placeholder="e.g. cristiano or https://www.instagram.com/cristiano/"
                  style={{ fontFamily: "var(--font-mono, monospace)" }}
                />
              </div>
              <div>
                <label className="label">Max Posts to Scrape</label>
                <input type="number" className="input" value={maxPosts} onChange={(e) => setMaxPosts(Number(e.target.value))} min={1} max={500} />
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                <label className="checkbox-label">
                  <input type="checkbox" checked={includeReels} onChange={(e) => setIncludeReels(e.target.checked)} />
                  Include Reels
                </label>
                <label className="checkbox-label">
                  <input type="checkbox" checked={downloadMedia} onChange={(e) => setDownloadMedia(e.target.checked)} />
                  Download media files
                </label>
              </div>
              <button className="btn btn-primary btn-lg" onClick={handleStart} disabled={loading || !url} style={{ width: "100%" }}>
                {loading ? <><span className="pulse-dot" /> Starting…</> : <><InstagramIcon size={16} /> Scrape Profile</>}
              </button>
            </div>
          </div>
          <div className="card" style={{ padding: 20 }}>
            <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 12, color: "var(--text-secondary)", textTransform: "uppercase", letterSpacing: "0.05em" }}>Collected Fields</div>
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {fields.map((f) => (
                <div key={f} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12, color: "var(--text-secondary)" }}>
                  <div style={{ width: 5, height: 5, borderRadius: "50%", background: "#e1306c", flexShrink: 0 }} />
                  {f}
                </div>
              ))}
            </div>
          </div>
        </div>
        {job && <JobTracker job={job} onCancel={() => jobsApi.cancel(job.id)} onDelete={async () => { await jobsApi.delete(job.id); setJob(null); addToast("Job deleted.", "success"); }} />}
      </div>
    </div>
  );
}
