"use client";

import { motion } from "framer-motion";
import { Pause, X, ExternalLink, Clock, Layers, FileText, Wifi, Trash2 } from "lucide-react";
import { useJobWebSocket } from "@/hooks/useJobWebSocket";
import type { Job, JobStatus } from "@/types";

// ── Progress tracker ──────────────────────────────────────────────────────────
interface JobTrackerProps {
  job: Job;
  onCancel?: () => void;
  onPause?: () => void;
  onDelete?: () => void;
}

export function JobTracker({ job, onCancel, onPause, onDelete }: JobTrackerProps) {
  const { progress, status, logs, isConnected } = useJobWebSocket(job.id);

  const currentStatus: JobStatus = status || job.status;
  const currentProgress = progress?.progress_pct ?? job.progress_pct ?? 0;

  const statusColors: Record<JobStatus, string> = {
    queued:    "var(--text-muted)",
    running:   "var(--accent-blue)",
    paused:    "var(--accent-amber)",
    completed: "var(--accent-emerald)",
    failed:    "var(--accent-rose)",
    cancelled: "var(--text-muted)",
  };

  const formatTime = (secs: number) => {
    if (secs < 60) return `${Math.round(secs)}s`;
    if (secs < 3600) return `${Math.floor(secs / 60)}m ${Math.round(secs % 60)}s`;
    return `${Math.floor(secs / 3600)}h ${Math.floor((secs % 3600) / 60)}m`;
  };

  return (
    <motion.div
      className="card"
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      style={{ overflow: "hidden" }}
    >
      {/* Header */}
      <div style={{
        padding: "14px 20px",
        borderBottom: "1px solid var(--border)",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <div style={{
            width: 8, height: 8, borderRadius: "50%",
            background: statusColors[currentStatus],
            boxShadow: `0 0 8px ${statusColors[currentStatus]}`,
            animation: currentStatus === "running" ? "pulse-dot 1.5s infinite" : "none",
          }} />
          <span style={{ fontWeight: 600, fontSize: 14 }}>Job {job.id.slice(0, 8)}…</span>
          <span className={`badge badge-${currentStatus}`}>{currentStatus}</span>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          {isConnected && (
            <div style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 11, color: "var(--accent-emerald)" }}>
              <Wifi size={10} />Live
            </div>
          )}
          {currentStatus === "running" && (
            <button className="btn btn-secondary btn-sm" onClick={onPause}>
              <Pause size={12} /> Pause
            </button>
          )}
          {(currentStatus === "running" || currentStatus === "queued") && (
            <button className="btn btn-danger btn-sm" onClick={onCancel}>
              <X size={12} /> Cancel
            </button>
          )}
          {(["completed", "failed", "cancelled"] as JobStatus[]).includes(currentStatus) && onDelete && (
            <button className="btn btn-danger btn-sm" onClick={onDelete} title="Delete this job">
              <Trash2 size={12} /> Delete
            </button>
          )}
        </div>
      </div>

      {/* Progress bar */}
      <div style={{ padding: "16px 20px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6, fontSize: 12 }}>
          <span style={{ color: "var(--text-secondary)" }}>
            {progress?.scraped_pages ?? 0} / {progress?.total_pages ?? "??"} pages
          </span>
          <span style={{ color: "var(--text-primary)", fontWeight: 600 }}>
            {currentProgress.toFixed(1)}%
          </span>
        </div>
        <div className="progress-track" style={{ height: 8 }}>
          <div className="progress-fill" style={{ width: `${currentProgress}%` }} />
        </div>

        {/* Stats row */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12, marginTop: 16 }}>
          {[
            { icon: <Layers size={13} />, label: "Items Found", value: progress?.items_found ?? 0 },
            { icon: <Clock size={13} />, label: "Elapsed", value: progress ? formatTime(progress.elapsed_seconds) : "—" },
            { icon: <FileText size={13} />, label: "Pages Scraped", value: progress?.scraped_pages ?? 0 },
            { icon: <ExternalLink size={13} />, label: "Total Pages", value: progress?.total_pages ?? "—" },
          ].map(({ icon, label, value }) => (
            <div key={label} style={{
              background: "var(--bg-secondary)",
              borderRadius: 8,
              padding: "10px 14px",
              border: "1px solid var(--border)",
            }}>
              <div style={{ display: "flex", alignItems: "center", gap: 5, color: "var(--text-muted)", marginBottom: 4 }}>
                {icon}
                <span style={{ fontSize: 10, textTransform: "uppercase", letterSpacing: "0.05em" }}>{label}</span>
              </div>
              <div style={{ fontSize: 16, fontWeight: 700, color: "var(--text-primary)" }}>{value}</div>
            </div>
          ))}
        </div>

        {/* Current URL */}
        {progress?.current_url && (
          <div style={{
            marginTop: 12, padding: "8px 12px",
            background: "var(--bg-secondary)",
            borderRadius: 6, border: "1px solid var(--border)",
            fontSize: 11, color: "var(--text-muted)",
            display: "flex", alignItems: "center", gap: 6,
          }}>
            <ExternalLink size={10} />
            <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {progress.current_url}
            </span>
          </div>
        )}
      </div>

      {/* Live log console */}
      <div style={{ padding: "0 20px 20px" }}>
        <div style={{ fontSize: 11, color: "var(--text-muted)", marginBottom: 6, textTransform: "uppercase", letterSpacing: "0.05em" }}>
          Live Logs
        </div>
        <div className="log-console">
          {logs.length === 0 ? (
            <div style={{ color: "var(--text-muted)", textAlign: "center", marginTop: 20 }}>
              Waiting for logs…
            </div>
          ) : (
            logs.map((log, i) => (
              <div key={i} className={`log-line ${log.level}`}>
                <span className="ts">{new Date(log.timestamp).toLocaleTimeString()}</span>
                <span className="level">[{log.level?.toUpperCase()}]</span>
                <span className="msg">{log.message}</span>
              </div>
            ))
          )}
        </div>
      </div>
    </motion.div>
  );
}

// ── Shared URL input component ────────────────────────────────────────────────
export function URLInput({
  value,
  onChange,
  placeholder = "https://example.com",
  label = "URL",
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  label?: string;
}) {
  return (
    <div>
      <label className="label">{label}</label>
      <input
        type="url"
        className="input input-lg"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        style={{ fontFamily: "var(--font-mono, monospace)" }}
      />
    </div>
  );
}
