"use client";

import { useState } from "react";

import { Zap, Globe, MapPin, ChevronRight, AlertCircle } from "lucide-react";
import { InstagramIcon, FacebookIcon, LinkedinIcon } from "@/components/icons/BrandIcons";
import { scrapeApi, jobsApi } from "@/lib/api";
import { JobTracker, URLInput } from "@/components/scrapers/JobTracker";
import { useToast } from "@/components/Providers";
import type { Job } from "@/types";

export default function GeneralScraperPage() {
  const [url, setUrl] = useState("");
  const [maxPages, setMaxPages] = useState(100);
  const [maxDepth, setMaxDepth] = useState(5);
  const [autoLaunch, setAutoLaunch] = useState(true);
  const [respectRobots, setRespectRobots] = useState(true);
  const [loading, setLoading] = useState(false);
  const [job, setJob] = useState<Job | null>(null);
  const { addToast } = useToast();

  const handleStart = async () => {
    if (!url.trim()) { addToast("Please enter a URL", "error"); return; }
    setLoading(true);
    try {
      const res = await scrapeApi.general({
        url: url.trim(),
        max_pages: maxPages,
        max_depth: maxDepth,
        auto_launch_social: autoLaunch,
        respect_robots: respectRobots,
      });
      if (res.success && res.data) {
        setJob(res.data as Job);
        addToast("General scraper started!", "success");
      } else {
        addToast(res.message || "Failed to start", "error");
      }
    } catch {
      addToast("Backend unreachable. Is the API running?", "error");
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = async () => {
    if (!job) return;
    await jobsApi.cancel(job.id);
    addToast("Job cancelled", "info");
  };

  const pipeline = [
    { icon: <Globe size={16} />, label: "Crawl Website", desc: "All pages recursively", color: "#06b6d4" },
    { icon: <AlertCircle size={16} />, label: "Detect Socials", desc: "Find all platform links", color: "#8b5cf6" },
    { icon: <InstagramIcon size={16} />, label: "Instagram", desc: "Profile & posts", color: "#e1306c" },
    { icon: <FacebookIcon size={16} />, label: "Facebook", desc: "Page & reviews", color: "#1877f2" },
    { icon: <LinkedinIcon size={16} />, label: "LinkedIn", desc: "Company info", color: "#0077b5" },
    { icon: <MapPin size={16} />, label: "Google Maps", desc: "Reviews & info", color: "#f43f5e" },
  ];

  return (
    <div>
      <div className="page-header">
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{
            width: 40, height: 40, borderRadius: 10,
            background: "var(--gradient-brand)",
            display: "flex", alignItems: "center", justifyContent: "center",
            boxShadow: "0 4px 12px var(--accent-blue-glow)",
          }}>
            <Zap size={20} color="white" />
          </div>
          <div>
            <h1 className="page-title">General Scraper</h1>
            <p className="page-subtitle">One URL → Full website crawl + auto social media scraping</p>
          </div>
        </div>
      </div>

      <div className="page-body" style={{ display: "flex", flexDirection: "column", gap: 20 }}>
        {/* Pipeline visualization */}
        <div className="card" style={{ padding: 20 }}>
          <div style={{ fontWeight: 600, color: "var(--text-secondary)", fontSize: 12, marginBottom: 16, textTransform: "uppercase", letterSpacing: "0.05em" }}>
            Automated Pipeline
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
            {pipeline.map((step, i) => (
              <div key={i} style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <div style={{
                  display: "flex", alignItems: "center", gap: 8,
                  padding: "8px 14px", borderRadius: 8,
                  background: "var(--bg-secondary)",
                  border: `1px solid ${step.color}33`,
                  color: step.color,
                }}>
                  {step.icon}
                  <div>
                    <div style={{ fontSize: 12, fontWeight: 600 }}>{step.label}</div>
                    <div style={{ fontSize: 10, color: "var(--text-muted)" }}>{step.desc}</div>
                  </div>
                </div>
                {i < pipeline.length - 1 && (
                  <ChevronRight size={16} style={{ color: "var(--text-muted)", flexShrink: 0 }} />
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Input form */}
        <div className="card" style={{ padding: 24 }}>
          <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
            <URLInput
              value={url}
              onChange={setUrl}
              placeholder="https://yourcompany.com"
              label="Website URL"
            />

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
              <div>
                <label className="label">Max Pages</label>
                <input
                  type="number"
                  className="input"
                  value={maxPages}
                  onChange={(e) => setMaxPages(Number(e.target.value))}
                  min={1} max={10000}
                />
              </div>
              <div>
                <label className="label">Max Crawl Depth</label>
                <input
                  type="number"
                  className="input"
                  value={maxDepth}
                  onChange={(e) => setMaxDepth(Number(e.target.value))}
                  min={1} max={20}
                />
              </div>
            </div>

            <div style={{ display: "flex", gap: 24 }}>
              <label className="checkbox-label">
                <input type="checkbox" checked={autoLaunch} onChange={(e) => setAutoLaunch(e.target.checked)} />
                Auto-launch social media scrapers
              </label>
              <label className="checkbox-label">
                <input type="checkbox" checked={respectRobots} onChange={(e) => setRespectRobots(e.target.checked)} />
                Respect robots.txt
              </label>
            </div>

            <div>
              <button
                className="btn btn-primary btn-lg"
                onClick={handleStart}
                disabled={loading || !url}
                style={{ width: "100%" }}
              >
                {loading ? (
                  <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <span className="pulse-dot" /> Starting…
                  </span>
                ) : (
                  <><Zap size={16} /> Start General Scan</>
                )}
              </button>
            </div>
          </div>
        </div>

        {/* Live tracker */}
        {job && (
          <JobTracker job={job} onCancel={handleCancel} onDelete={async () => { await jobsApi.delete(job.id); setJob(null); addToast("Job deleted.", "success"); }} />
        )}
      </div>
    </div>
  );
}
