"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, AreaChart, Area
} from "recharts";
import {
  Briefcase, Activity, CheckCircle2, XCircle,
  Globe, MapPin, Star, Users, FileText, TrendingUp, Trash2
} from "lucide-react";
import { InstagramIcon, LinkedinIcon, FacebookIcon } from "@/components/icons/BrandIcons";
import { dashboardApi, jobsApi } from "@/lib/api";
import { useToast } from "@/components/Providers";
import type { Job, JobType, JobStatus } from "@/types";
import { formatDistanceToNow } from "date-fns";

// ── Status badge ──────────────────────────────────────────────────────────────
function StatusBadge({ status }: { status: JobStatus }) {
  return <span className={`badge badge-${status}`}>{status}</span>;
}

// ── Type icon ─────────────────────────────────────────────────────────────────
const TYPE_ICONS: Record<JobType, React.ReactNode> = {
  general:     <Globe size={14} />,
  website:     <FileText size={14} />,
  google_maps: <MapPin size={14} />,
  instagram:   <InstagramIcon size={14} />,
  linkedin:    <LinkedinIcon size={14} />,
  facebook:    <FacebookIcon size={14} />,
};

const TYPE_COLORS: Record<string, string> = {
  general:     "#3b82f6",
  website:     "#06b6d4",
  google_maps: "#f43f5e",
  instagram:   "#e1306c",
  linkedin:    "#0077b5",
  facebook:    "#1877f2",
};

// ── Stat card ─────────────────────────────────────────────────────────────────
function StatCard({
  label, value, icon, color, sub
}: {
  label: string; value: number | string; icon: React.ReactNode;
  color: "blue" | "purple" | "emerald" | "rose" | "amber" | "cyan";
  sub?: string;
}) {
  return (
    <motion.div
      className={`stat-card ${color}`}
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 16 }}>
        <div style={{
          width: 40, height: 40, borderRadius: 10,
          background: `rgba(var(--accent-${color}-rgb, 59,130,246), 0.12)`,
          display: "flex", alignItems: "center", justifyContent: "center",
          color: `var(--accent-${color})`,
          border: `1px solid rgba(var(--accent-${color}-rgb, 59,130,246), 0.2)`,
        }}>
          {icon}
        </div>
      </div>
      <div style={{ fontSize: 28, fontWeight: 800, color: "var(--text-primary)", lineHeight: 1 }}>
        {typeof value === "number" ? value.toLocaleString() : value}
      </div>
      <div style={{ fontSize: 13, color: "var(--text-secondary)", marginTop: 6 }}>{label}</div>
      {sub && <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 4 }}>{sub}</div>}
    </motion.div>
  );
}

// ── Job row ───────────────────────────────────────────────────────────────────
function JobRow({ job, onDelete }: { job: Job; onDelete: (id: string) => void }) {
  const isDeletable = ["completed", "failed", "cancelled"].includes(job.status);
  return (
    <tr>
      <td>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ color: TYPE_COLORS[job.type] }}>{TYPE_ICONS[job.type]}</span>
          <span style={{ color: "var(--text-secondary)", textTransform: "capitalize" }}>
            {job.type.replace("_", " ")}
          </span>
        </div>
      </td>
      <td>
        <span style={{ maxWidth: 200, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", display: "block" }}>
          {job.target_url}
        </span>
      </td>
      <td><StatusBadge status={job.status} /></td>
      <td>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <div className="progress-track" style={{ width: 80 }}>
            <div className="progress-fill" style={{ width: `${job.progress_pct || 0}%` }} />
          </div>
          <span style={{ fontSize: 12, color: "var(--text-muted)" }}>{job.progress_pct?.toFixed(0) || 0}%</span>
        </div>
      </td>
      <td style={{ color: "var(--text-muted)", fontSize: 12 }}>
        {job.created_at ? formatDistanceToNow(new Date(job.created_at), { addSuffix: true }) : "—"}
      </td>
      <td>
        {isDeletable && (
          <button
            className="btn btn-danger btn-sm"
            onClick={() => onDelete(job.id)}
            title="Delete this job"
          >
            <Trash2 size={12} />
          </button>
        )}
      </td>
    </tr>
  );
}

// ── Mock chart data (supplement real data) ────────────────────────────────────
const mockTimelineData = [
  { day: "Mon", jobs: 4, items: 234 },
  { day: "Tue", jobs: 7, items: 412 },
  { day: "Wed", jobs: 3, items: 189 },
  { day: "Thu", jobs: 9, items: 601 },
  { day: "Fri", jobs: 6, items: 377 },
  { day: "Sat", jobs: 2, items: 95 },
  { day: "Sun", jobs: 5, items: 310 },
];

// ── Dashboard page ────────────────────────────────────────────────────────────
export default function DashboardPage() {
  const { addToast } = useToast();
  const queryClient = useQueryClient();

  const { data: statsRes, isLoading } = useQuery({
    queryKey: ["dashboard-stats"],
    queryFn: () => dashboardApi.getStats(),
    refetchInterval: 10_000,
  });

  const deleteMutation = useMutation({
    mutationFn: (jobId: string) => jobsApi.delete(jobId),
    onSuccess: () => {
      addToast("Job deleted.", "success");
      queryClient.invalidateQueries({ queryKey: ["dashboard-stats"] });
    },
    onError: () => addToast("Failed to delete job.", "error"),
  });

  const stats = statsRes?.data;

  const pieData = stats
    ? Object.entries(stats.jobs_by_type || {}).map(([name, value]) => ({ name, value }))
    : [];

  const PIE_COLORS = Object.values(TYPE_COLORS);

  return (
    <div>
      {/* Header */}
      <div className="page-header">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <h1 className="page-title">Dashboard</h1>
            <p className="page-subtitle">Real-time overview of your data scraping operations</p>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, color: "var(--text-secondary)" }}>
            <span className="pulse-dot" />
            Live data
          </div>
        </div>
      </div>

      <div className="page-body" style={{ display: "flex", flexDirection: "column", gap: 24 }}>
        {/* Stats grid */}
        {isLoading ? (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 16 }}>
            {[...Array(8)].map((_, i) => (
              <div key={i} className="stat-card" style={{
                height: 120,
                background: "linear-gradient(90deg, var(--bg-card) 25%, var(--bg-card-hover) 50%, var(--bg-card) 75%)",
                backgroundSize: "200% 100%",
                animation: "shimmer 1.5s infinite",
              }} />
            ))}
          </div>
        ) : (
          <div className="grid-4">
            <StatCard label="Total Jobs" value={stats?.total_jobs || 0} icon={<Briefcase size={18} />} color="blue" />
            <StatCard label="Active Jobs" value={stats?.active_jobs || 0} icon={<Activity size={18} />} color="purple" sub="Currently running" />
            <StatCard label="Completed" value={stats?.completed_jobs || 0} icon={<CheckCircle2 size={18} />} color="emerald" />
            <StatCard label="Failed" value={stats?.failed_jobs || 0} icon={<XCircle size={18} />} color="rose" />
            <StatCard label="Pages Scraped" value={stats?.total_pages_scraped || 0} icon={<Globe size={18} />} color="cyan" />
            <StatCard label="Businesses" value={stats?.total_businesses || 0} icon={<MapPin size={18} />} color="amber" />
            <StatCard label="Reviews Collected" value={stats?.total_reviews || 0} icon={<Star size={18} />} color="blue" />
            <StatCard label="Social Profiles" value={stats?.total_social_profiles || 0} icon={<Users size={18} />} color="purple" />
          </div>
        )}

        {/* Charts row */}
        <div className="grid-2">
          {/* Activity timeline */}
          <div className="card" style={{ padding: 20 }}>
            <div style={{ fontWeight: 600, color: "var(--text-primary)", marginBottom: 16, fontSize: 15 }}>
              Scraping Activity (7 days)
            </div>
            <ResponsiveContainer width="100%" height={180}>
              <AreaChart data={mockTimelineData}>
                <defs>
                  <linearGradient id="blueGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <XAxis dataKey="day" tick={{ fill: "var(--text-secondary)", fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: "var(--text-secondary)", fontSize: 11 }} axisLine={false} tickLine={false} />
                <Tooltip
                  contentStyle={{ background: "var(--bg-card)", border: "1px solid var(--border)", borderRadius: 8 }}
                  labelStyle={{ color: "var(--text-primary)" }}
                />
                <Area type="monotone" dataKey="items" stroke="#3b82f6" fill="url(#blueGrad)" strokeWidth={2} dot={false} />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          {/* Jobs by platform */}
          <div className="card" style={{ padding: 20 }}>
            <div style={{ fontWeight: 600, color: "var(--text-primary)", marginBottom: 16, fontSize: 15 }}>
              Jobs by Platform
            </div>
            {pieData.length > 0 ? (
              <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
                <ResponsiveContainer width="50%" height={160}>
                  <PieChart>
                    <Pie data={pieData} cx="50%" cy="50%" innerRadius={40} outerRadius={70}
                      dataKey="value" paddingAngle={3}>
                      {pieData.map((_, i) => (
                        <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip contentStyle={{ background: "var(--bg-card)", border: "1px solid var(--border)", borderRadius: 8 }} />
                  </PieChart>
                </ResponsiveContainer>
                <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 8 }}>
                  {pieData.map((item, i) => (
                    <div key={item.name} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12 }}>
                      <div style={{ width: 8, height: 8, borderRadius: 2, background: PIE_COLORS[i % PIE_COLORS.length] }} />
                      <span style={{ color: "var(--text-secondary)", textTransform: "capitalize", flex: 1 }}>
                        {item.name.replace("_", " ")}
                      </span>
                      <span style={{ color: "var(--text-primary)", fontWeight: 600 }}>{item.value}</span>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="empty-state" style={{ padding: 40 }}>
                <TrendingUp size={32} />
                <span>No jobs yet. Start scraping!</span>
              </div>
            )}
          </div>
        </div>

        {/* Jobs by status bar chart */}
        <div className="card" style={{ padding: 20 }}>
          <div style={{ fontWeight: 600, color: "var(--text-primary)", marginBottom: 16, fontSize: 15 }}>
            Jobs by Status
          </div>
          <ResponsiveContainer width="100%" height={100}>
            <BarChart
              data={stats ? Object.entries(stats.jobs_by_status || {}).map(([name, value]) => ({ name, value })) : []}
              layout="vertical"
            >
              <XAxis type="number" tick={{ fill: "var(--text-secondary)", fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis dataKey="name" type="category" tick={{ fill: "var(--text-secondary)", fontSize: 11 }} axisLine={false} tickLine={false} width={80} />
              <Tooltip contentStyle={{ background: "var(--bg-card)", border: "1px solid var(--border)", borderRadius: 8 }} />
              <Bar dataKey="value" radius={4} fill="#3b82f6" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Recent jobs table */}
        <div className="card">
          <div style={{ padding: "16px 20px", borderBottom: "1px solid var(--border)", fontWeight: 600, color: "var(--text-primary)", fontSize: 15 }}>
            Recent Jobs
          </div>
          <div className="table-container" style={{ borderRadius: 0, border: "none" }}>
            <table>
              <thead>
                <tr>
                  <th>Type</th>
                  <th>Target URL</th>
                  <th>Status</th>
                  <th>Progress</th>
                  <th>Created</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {stats?.recent_jobs?.length ? (
                  stats.recent_jobs.map((job: Job) => (
                    <JobRow key={job.id} job={job} onDelete={(id) => deleteMutation.mutate(id)} />
                  ))
                ) : (
                  <tr>
                    <td colSpan={6}>
                      <div className="empty-state" style={{ padding: 40 }}>
                        <Briefcase size={32} />
                        <span>No jobs yet. Use the sidebar to start scraping.</span>
                      </div>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
