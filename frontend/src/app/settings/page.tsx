"use client";

import { useState } from "react";
import { Settings, Save, RefreshCw, Shield, Globe, Zap, Database } from "lucide-react";
import { useToast } from "@/components/Providers";

interface SettingsState {
  concurrency: number;
  delay_ms: number;
  timeout_sec: number;
  max_retries: number;
  max_crawl_depth: number;
  max_pages: number;
  headless_browser: boolean;
  respect_robots: boolean;
  user_agent: string;
  proxy_url: string;
  proxy_username: string;
  proxy_password: string;
  instagram_username: string;
  instagram_password: string;
  linkedin_username: string;
  linkedin_password: string;
}

function SettingSection({ title, icon, children }: { title: string; icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <div className="card" style={{ overflow: "hidden" }}>
      <div style={{ padding: "14px 20px", borderBottom: "1px solid var(--border)", display: "flex", alignItems: "center", gap: 8 }}>
        <span style={{ color: "var(--accent-blue)" }}>{icon}</span>
        <span style={{ fontWeight: 600, fontSize: 14 }}>{title}</span>
      </div>
      <div style={{ padding: 20, display: "flex", flexDirection: "column", gap: 16 }}>{children}</div>
    </div>
  );
}

function NumberField({ label, value, onChange, min, max, desc }: {
  label: string; value: number; onChange: (v: number) => void;
  min?: number; max?: number; desc?: string;
}) {
  return (
    <div>
      <label className="label">{label}</label>
      <input type="number" className="input" value={value} onChange={(e) => onChange(Number(e.target.value))} min={min} max={max} />
      {desc && <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 4 }}>{desc}</div>}
    </div>
  );
}

function TextField({ label, value, onChange, type, desc, placeholder }: {
  label: string; value: string; onChange: (v: string) => void;
  type?: string; desc?: string; placeholder?: string;
}) {
  return (
    <div>
      <label className="label">{label}</label>
      <input type={type || "text"} className="input" value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder} />
      {desc && <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 4 }}>{desc}</div>}
    </div>
  );
}

export default function SettingsPage() {
  const { addToast } = useToast();
  const [s, setS] = useState<SettingsState>({
    concurrency: 5,
    delay_ms: 1000,
    timeout_sec: 30,
    max_retries: 3,
    max_crawl_depth: 5,
    max_pages: 100,
    headless_browser: true,
    respect_robots: true,
    user_agent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    proxy_url: "",
    proxy_username: "",
    proxy_password: "",
    instagram_username: "",
    instagram_password: "",
    linkedin_username: "",
    linkedin_password: "",
  });

  const update = <K extends keyof SettingsState>(k: K, v: SettingsState[K]) =>
    setS((prev) => ({ ...prev, [k]: v }));

  const handleSave = () => {
    localStorage.setItem("scrapper_settings", JSON.stringify(s));
    addToast("Settings saved successfully!", "success");
  };

  const handleReset = () => {
    localStorage.removeItem("scrapper_settings");
    addToast("Settings reset to defaults", "info");
  };

  return (
    <div>
      <div className="page-header">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <div style={{ width: 40, height: 40, borderRadius: 10, background: "linear-gradient(135deg, #64748b, #475569)", display: "flex", alignItems: "center", justifyContent: "center" }}>
              <Settings size={20} color="white" />
            </div>
            <div>
              <h1 className="page-title">Settings</h1>
              <p className="page-subtitle">Configure scraper behavior, proxies, and credentials</p>
            </div>
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            <button className="btn btn-secondary" onClick={handleReset}>
              <RefreshCw size={14} /> Reset
            </button>
            <button className="btn btn-primary" onClick={handleSave}>
              <Save size={14} /> Save Settings
            </button>
          </div>
        </div>
      </div>

      <div className="page-body" style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        {/* Scraping behavior */}
        <SettingSection title="Scraping Behavior" icon={<Zap size={16} />}>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16 }}>
            <NumberField label="Concurrency" value={s.concurrency} onChange={(v) => update("concurrency", v)} min={1} max={20} desc="Parallel requests" />
            <NumberField label="Delay (ms)" value={s.delay_ms} onChange={(v) => update("delay_ms", v)} min={0} desc="Between requests" />
            <NumberField label="Timeout (s)" value={s.timeout_sec} onChange={(v) => update("timeout_sec", v)} min={5} max={120} />
            <NumberField label="Max Retries" value={s.max_retries} onChange={(v) => update("max_retries", v)} min={0} max={10} desc="On failure" />
            <NumberField label="Max Crawl Depth" value={s.max_crawl_depth} onChange={(v) => update("max_crawl_depth", v)} min={1} max={20} />
            <NumberField label="Max Pages" value={s.max_pages} onChange={(v) => update("max_pages", v)} min={1} max={10000} desc="Default per job" />
          </div>
          <div style={{ display: "flex", gap: 24 }}>
            <label className="checkbox-label">
              <input type="checkbox" checked={s.headless_browser} onChange={(e) => update("headless_browser", e.target.checked)} />
              Headless browser mode
            </label>
            <label className="checkbox-label">
              <input type="checkbox" checked={s.respect_robots} onChange={(e) => update("respect_robots", e.target.checked)} />
              Respect robots.txt by default
            </label>
          </div>
        </SettingSection>

        {/* User agent */}
        <SettingSection title="Browser & User Agent" icon={<Globe size={16} />}>
          <TextField
            label="Default User Agent"
            value={s.user_agent}
            onChange={(v) => update("user_agent", v)}
            desc="User-agent rotation is enabled automatically for all scraping jobs"
          />
        </SettingSection>

        {/* Proxy */}
        <SettingSection title="Proxy Settings" icon={<Shield size={16} />}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 16 }}>
            <TextField label="Proxy URL" value={s.proxy_url} onChange={(v) => update("proxy_url", v)} placeholder="http://proxy:port" desc="Leave blank to disable" />
            <TextField label="Proxy Username" value={s.proxy_username} onChange={(v) => update("proxy_username", v)} placeholder="Optional" />
            <TextField label="Proxy Password" value={s.proxy_password} onChange={(v) => update("proxy_password", v)} type="password" placeholder="Optional" />
          </div>
        </SettingSection>

        {/* Authentication */}
        <SettingSection title="Platform Credentials" icon={<Database size={16} />}>
          <div style={{ padding: 12, background: "rgba(245,158,11,0.08)", border: "1px solid rgba(245,158,11,0.2)", borderRadius: 8, fontSize: 12, color: "#fbbf24" }}>
            ⚠️ Credentials are stored in local storage. Use at your own risk. Credentials improve scrape success rates on authenticated platforms.
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
            <TextField label="Instagram Username" value={s.instagram_username} onChange={(v) => update("instagram_username", v)} placeholder="@username" />
            <TextField label="Instagram Password" value={s.instagram_password} onChange={(v) => update("instagram_password", v)} type="password" placeholder="••••••••" />
            <TextField label="LinkedIn Email" value={s.linkedin_username} onChange={(v) => update("linkedin_username", v)} placeholder="user@email.com" />
            <TextField label="LinkedIn Password" value={s.linkedin_password} onChange={(v) => update("linkedin_password", v)} type="password" placeholder="••••••••" />
          </div>
        </SettingSection>
      </div>
    </div>
  );
}
