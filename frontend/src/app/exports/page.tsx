"use client";

import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { Download, FileJson, FileSpreadsheet, FileText, Archive, FileCode, File, Trash2, Tag } from "lucide-react";
import { exportsApi, jobsApi } from "@/lib/api";
import { useToast } from "@/components/Providers";
import type { ExportFormat, ExportFile } from "@/types";

const FORMAT_INFO: Record<ExportFormat, { icon: React.ReactNode; label: string; desc: string; color: string }> = {
  json:  { icon: <FileJson size={20} />,        label: "JSON",        desc: "Structured JSON format",         color: "#f59e0b" },
  csv:   { icon: <FileText size={20} />,         label: "CSV",         desc: "Spreadsheet-compatible",         color: "#10b981" },
  excel: { icon: <FileSpreadsheet size={20} />,  label: "Excel",       desc: "Multi-sheet .xlsx workbook",     color: "#3b82f6" },
  xml:   { icon: <FileCode size={20} />,         label: "XML",         desc: "XML with full nesting",          color: "#8b5cf6" },
  pdf:   { icon: <File size={20} />,             label: "PDF",         desc: "Formatted PDF report",           color: "#f43f5e" },
  zip:   { icon: <Archive size={20} />,          label: "ZIP",         desc: "Bundle: JSON + CSV in zip",      color: "#64748b" },
};

function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1048576).toFixed(2)} MB`;
}

export default function ExportsPage() {
  const [selectedJobId, setSelectedJobId] = useState("");
  const [selectedFormat, setSelectedFormat] = useState<ExportFormat>("json");
  const [customName, setCustomName] = useState("");
  const { addToast } = useToast();


  const { data: exportFiles, refetch } = useQuery({
    queryKey: ["exports"],
    queryFn: () => exportsApi.list(),
    refetchInterval: 10_000,
  });

  const { data: jobsData } = useQuery({
    queryKey: ["jobs-list"],
    queryFn: () => jobsApi.list({ limit: 100 }),
  });

  const exportMutation = useMutation({
    mutationFn: () => exportsApi.create(selectedJobId, selectedFormat, customName),
    onSuccess: (res) => {
      if (res.success) {
        addToast(`Export created: ${res.data?.file}`, "success");
        setCustomName("");
        refetch();
      } else {
        addToast(res.message || "Export failed", "error");
      }
    },
    onError: () => addToast("Export failed. Is the API running?", "error"),
  });

  const clearMutation = useMutation({
    mutationFn: () => exportsApi.clear(),
    onSuccess: () => {
      addToast("Export history cleared successfully!", "success");
      refetch();
    },
    onError: () => addToast("Failed to clear export history.", "error"),
  });

  const files: ExportFile[] = exportFiles?.data || [];
  const jobs = (jobsData?.data as { jobs: { id: string; type: string; target_url: string; status: string }[] })?.jobs || [];
  const completedJobs = jobs.filter(j => j.status === "completed");

  // Auto-populate custom name from selected job
  const handleJobSelect = (jobId: string) => {
    setSelectedJobId(jobId);
    if (!customName) {
      const job = jobs.find(j => j.id === jobId);
      if (job) {
        // Suggest a name based on job type + URL slug
        const urlSlug = job.target_url
          .replace(/^https?:\/\/(www\.)?/, "")
          .split("/")[0]
          .split("?")[0]
          .replace(/[^a-zA-Z0-9]/g, "_")
          .replace(/_+/g, "_")
          .slice(0, 40);
        setCustomName(urlSlug || job.type);
      }
    }
  };

  return (
    <div>
      <div className="page-header">
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{ width: 40, height: 40, borderRadius: 10, background: "linear-gradient(135deg, #8b5cf6, #6366f1)", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <Download size={20} color="white" />
          </div>
          <div>
            <h1 className="page-title">Exported Data</h1>
            <p className="page-subtitle">Export scraping results in multiple formats</p>
          </div>
        </div>
      </div>

      <div className="page-body" style={{ display: "flex", flexDirection: "column", gap: 20 }}>
        {/* Create export */}
        <div className="card" style={{ padding: 24 }}>
          <div style={{ fontWeight: 600, fontSize: 15, marginBottom: 20 }}>Create New Export</div>

          {/* Format selector */}
          <div style={{ marginBottom: 20 }}>
            <label className="label">Export Format</label>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: 10 }}>
              {(Object.entries(FORMAT_INFO) as [ExportFormat, typeof FORMAT_INFO[ExportFormat]][]).map(([fmt, info]) => (
                <button
                  key={fmt}
                  onClick={() => setSelectedFormat(fmt)}
                  style={{
                    padding: "14px 10px",
                    borderRadius: 10,
                    border: `2px solid ${selectedFormat === fmt ? info.color : "var(--border)"}`,
                    background: selectedFormat === fmt ? `${info.color}15` : "var(--bg-secondary)",
                    color: selectedFormat === fmt ? info.color : "var(--text-secondary)",
                    cursor: "pointer",
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "center",
                    gap: 6,
                    transition: "all 0.2s",
                  }}
                >
                  {info.icon}
                  <span style={{ fontSize: 12, fontWeight: 600 }}>{info.label}</span>
                  <span style={{ fontSize: 10, color: "var(--text-muted)", textAlign: "center" }}>{info.desc}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Job selector */}
          <div style={{ marginBottom: 16 }}>
            <label className="label">Select Completed Job</label>
            <select
              className="input"
              value={selectedJobId}
              onChange={(e) => handleJobSelect(e.target.value)}
            >
              <option value="">-- Select a completed job --</option>
              {completedJobs.map((job) => (
                <option key={job.id} value={job.id}>
                  {job.type.replace("_", " ")} — {job.target_url.slice(0, 60)} ({job.id.slice(0, 8)})
                </option>
              ))}
              {jobs.filter(j => j.status !== "completed").length > 0 && (
                <>
                  <option disabled>──── Other Jobs ────</option>
                  {jobs.filter(j => j.status !== "completed").map((job) => (
                    <option key={job.id} value={job.id}>
                      [{job.status}] {job.type.replace("_", " ")} — {job.target_url.slice(0, 50)} ({job.id.slice(0, 8)})
                    </option>
                  ))}
                </>
              )}
            </select>
          </div>

          {/* Custom filename */}
          <div style={{ marginBottom: 20 }}>
            <label className="label" style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <Tag size={13} />
              Custom Filename
              <span style={{ fontSize: 11, color: "var(--text-muted)", fontWeight: 400 }}>(optional — leave blank for auto-generated name)</span>
            </label>
            <div style={{ position: "relative" }}>
              <input
                type="text"
                className="input"
                value={customName}
                onChange={(e) => setCustomName(e.target.value)}
                placeholder={`e.g. "Ensys_Technologies_Reviews" — default: auto-detected from scraped data`}
                style={{ paddingRight: 120 }}
                maxLength={80}
              />
              {customName && (
                <span style={{
                  position: "absolute", right: 12, top: "50%", transform: "translateY(-50%)",
                  fontSize: 11, color: "var(--text-muted)", pointerEvents: "none",
                }}>
                  → {customName.replace(/[^a-zA-Z0-9_\-]/g, "_").replace(/_+/g, "_").slice(0, 40)}_…
                </span>
              )}
            </div>
          </div>

          <button
            className="btn btn-primary"
            onClick={() => exportMutation.mutate()}
            disabled={!selectedJobId || exportMutation.isPending}
          >
            {exportMutation.isPending ? (
              <><span className="pulse-dot" /> Generating…</>
            ) : (
              <><Download size={14} /> Generate {selectedFormat.toUpperCase()} Export</>
            )}
          </button>
        </div>

        {/* Files table */}
        <div className="card">
          <div style={{
            padding: "16px 20px",
            borderBottom: "1px solid var(--border)",
            fontWeight: 600,
            fontSize: 15,
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center"
          }}>
            <span>Export History ({files.length})</span>
            {files.length > 0 && (
              <button
                className="btn btn-danger btn-sm"
                onClick={() => clearMutation.mutate()}
                disabled={clearMutation.isPending}
              >
                <Trash2 size={12} /> Clear History
              </button>
            )}
          </div>
          <div className="table-container" style={{ border: "none", borderRadius: 0 }}>
            <table>
              <thead>
                <tr>
                  <th>Filename</th>
                  <th>Format</th>
                  <th>Size</th>
                  <th>Created</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {files.length === 0 ? (
                  <tr>
                    <td colSpan={5}>
                      <div className="empty-state">
                        <Download size={32} />
                        <span>No exports yet. Create your first export above.</span>
                      </div>
                    </td>
                  </tr>
                ) : (
                  files.map((file) => {
                    const ext = file.filename.split(".").pop() as ExportFormat;
                    const info = FORMAT_INFO[ext] || FORMAT_INFO.json;
                    return (
                      <tr key={file.filename}>
                        <td style={{ display: "flex", alignItems: "center", gap: 8 }}>
                          <span style={{ color: info.color }}>{info.icon}</span>
                          {file.filename}
                        </td>
                        <td><span className="badge" style={{ background: `${info.color}15`, color: info.color, border: `1px solid ${info.color}33` }}>{ext?.toUpperCase()}</span></td>
                        <td>{formatBytes(file.size)}</td>
                        <td style={{ color: "var(--text-muted)", fontSize: 12 }}>
                          {new Date(file.created_at * 1000).toLocaleString()}
                        </td>
                        <td>
                          <a
                            href={exportsApi.downloadUrl(file.filename)}
                            download
                            className="btn btn-secondary btn-sm"
                            target="_blank"
                            rel="noreferrer"
                          >
                            <Download size={12} /> Download
                          </a>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
