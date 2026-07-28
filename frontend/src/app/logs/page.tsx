"use client";

import { useState, useEffect, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import { ScrollText, RefreshCw, Filter, AlertCircle, Info, AlertTriangle, Bug, X } from "lucide-react";
import { logsApi } from "@/lib/api";
import type { LogEntry, LogLevel } from "@/types";

const LEVEL_CONFIG: Record<LogLevel, { icon: React.ReactNode; color: string; bg: string }> = {
  debug:    { icon: <Bug size={11} />,           color: "#64748b", bg: "rgba(100,116,139,0.1)" },
  info:     { icon: <Info size={11} />,          color: "#60a5fa", bg: "rgba(59,130,246,0.1)"  },
  warning:  { icon: <AlertTriangle size={11} />, color: "#fbbf24", bg: "rgba(245,158,11,0.1)"  },
  error:    { icon: <AlertCircle size={11} />,   color: "#f87171", bg: "rgba(244,63,94,0.1)"   },
  critical: { icon: <AlertCircle size={11} />,   color: "#ef4444", bg: "rgba(239,68,68,0.15)"  },
};

const LEVELS: LogLevel[] = ["debug", "info", "warning", "error", "critical"];

export default function LogsPage() {
  const [filterLevel, setFilterLevel] = useState<LogLevel | "all">("all");
  const [search, setSearch] = useState("");
  const [autoScroll, setAutoScroll] = useState(true);
  const bottomRef = useRef<HTMLDivElement>(null);

  const { data: logsRes, refetch, isLoading } = useQuery({
    queryKey: ["all-logs", filterLevel],
    queryFn: () => logsApi.getAll({
      level: filterLevel === "all" ? undefined : filterLevel,
      limit: 500,
    }),
    refetchInterval: 5000,
  });

  const allLogs: LogEntry[] = logsRes?.data || [];
  const filtered = search
    ? allLogs.filter((l) => l.message.toLowerCase().includes(search.toLowerCase()))
    : allLogs;

  useEffect(() => {
    if (autoScroll && bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [filtered, autoScroll]);

  const levelCounts = LEVELS.reduce((acc, lvl) => {
    acc[lvl] = allLogs.filter((l) => l.level === lvl).length;
    return acc;
  }, {} as Record<LogLevel, number>);

  return (
    <div>
      <div className="page-header">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <div style={{ width: 40, height: 40, borderRadius: 10, background: "linear-gradient(135deg, #64748b, #94a3b8)", display: "flex", alignItems: "center", justifyContent: "center" }}>
              <ScrollText size={20} color="white" />
            </div>
            <div>
              <h1 className="page-title">System Logs</h1>
              <p className="page-subtitle">All scraper activity, errors, warnings, and debug info</p>
            </div>
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            <label className="checkbox-label" style={{ fontSize: 12 }}>
              <input type="checkbox" checked={autoScroll} onChange={(e) => setAutoScroll(e.target.checked)} />
              Auto-scroll
            </label>
            <button className="btn btn-secondary btn-sm" onClick={() => refetch()}>
              <RefreshCw size={12} /> Refresh
            </button>
          </div>
        </div>
      </div>

      <div className="page-body" style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        {/* Level filter pills */}
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <button
            className="btn btn-sm"
            onClick={() => setFilterLevel("all")}
            style={{
              background: filterLevel === "all" ? "var(--gradient-brand)" : "var(--bg-card)",
              color: filterLevel === "all" ? "white" : "var(--text-secondary)",
              border: "1px solid var(--border)",
            }}
          >
            All ({allLogs.length})
          </button>
          {LEVELS.map((lvl) => {
            const cfg = LEVEL_CONFIG[lvl];
            return (
              <button
                key={lvl}
                className="btn btn-sm"
                onClick={() => setFilterLevel(lvl)}
                style={{
                  background: filterLevel === lvl ? cfg.bg : "var(--bg-card)",
                  color: filterLevel === lvl ? cfg.color : "var(--text-secondary)",
                  border: `1px solid ${filterLevel === lvl ? cfg.color + "44" : "var(--border)"}`,
                  display: "flex",
                  alignItems: "center",
                  gap: 4,
                }}
              >
                {cfg.icon}
                {lvl.charAt(0).toUpperCase() + lvl.slice(1)} ({levelCounts[lvl] || 0})
              </button>
            );
          })}
        </div>

        {/* Search */}
        <div style={{ position: "relative" }}>
          <input
            type="text"
            className="input"
            placeholder="Search logs…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{ paddingLeft: 36 }}
          />
          <Filter size={14} style={{ position: "absolute", left: 12, top: "50%", transform: "translateY(-50%)", color: "var(--text-muted)" }} />
          {search && (
            <button
              onClick={() => setSearch("")}
              style={{ position: "absolute", right: 12, top: "50%", transform: "translateY(-50%)", background: "none", border: "none", cursor: "pointer", color: "var(--text-muted)" }}
            >
              <X size={14} />
            </button>
          )}
        </div>

        {/* Log console */}
        <div style={{
          background: "#040810",
          border: "1px solid var(--border)",
          borderRadius: 12,
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: 11.5,
          height: "calc(100vh - 320px)",
          overflowY: "auto",
          padding: 16,
        }}>
          {isLoading ? (
            <div style={{ color: "var(--text-muted)", textAlign: "center", paddingTop: 40 }}>Loading logs…</div>
          ) : filtered.length === 0 ? (
            <div style={{ color: "var(--text-muted)", textAlign: "center", paddingTop: 40 }}>
              No logs found. Start a scraping job to see activity here.
            </div>
          ) : (
            filtered.map((log, i) => {
              const cfg = LEVEL_CONFIG[log.level] || LEVEL_CONFIG.info;
              return (
                <div
                  key={i}
                  style={{
                    display: "flex",
                    gap: 10,
                    padding: "3px 0",
                    borderBottom: "1px solid #0d1117",
                    alignItems: "flex-start",
                  }}
                >
                  <span style={{ color: "#334155", flexShrink: 0, fontSize: 10 }}>
                    {log.timestamp ? new Date(log.timestamp).toLocaleTimeString() : "—"}
                  </span>
                  <span style={{
                    width: 64,
                    flexShrink: 0,
                    display: "flex",
                    alignItems: "center",
                    gap: 3,
                    color: cfg.color,
                    fontWeight: 700,
                    fontSize: 10,
                    letterSpacing: "0.03em",
                    textTransform: "uppercase",
                  }}>
                    {cfg.icon}
                    {log.level}
                  </span>
                  <span style={{ color: "#94a3b8", fontSize: 9, flexShrink: 0 }}>
                    {log.job_id?.slice(0, 8) || "global"}
                  </span>
                  <span style={{ color: "#c9d4e3", wordBreak: "break-all" }}>{log.message}</span>
                </div>
              );
            })
          )}
          <div ref={bottomRef} />
        </div>

        <div style={{ fontSize: 11, color: "var(--text-muted)", textAlign: "right" }}>
          Showing {filtered.length} of {allLogs.length} entries • Auto-refreshes every 5s
        </div>
      </div>
    </div>
  );
}
