"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Zap,
  Globe,
  MapPin,
  Download,
  ScrollText,
  Settings,
  ChevronRight,
  Bot,
} from "lucide-react";
import { InstagramIcon, FacebookIcon, LinkedinIcon } from "@/components/icons/BrandIcons";

const navItems = [
  { href: "/", icon: LayoutDashboard, label: "Dashboard", group: "Overview" },
  { href: "/ai-assistant", icon: Bot, label: "AI Reviews Chat", group: "Overview" },
  { href: "/general", icon: Zap, label: "General Scraper", group: "Scrapers", highlight: true },
  { href: "/website", icon: Globe, label: "Website Scraper", group: "Scrapers" },
  { href: "/google-maps", icon: MapPin, label: "Google Maps", group: "Scrapers" },
  { href: "/instagram", icon: InstagramIcon, label: "Instagram", group: "Scrapers" },
  { href: "/linkedin", icon: LinkedinIcon, label: "LinkedIn", group: "Scrapers" },
  { href: "/facebook", icon: FacebookIcon, label: "Facebook", group: "Scrapers" },
  { href: "/exports", icon: Download, label: "Exported Data", group: "Data" },
  { href: "/logs", icon: ScrollText, label: "Logs", group: "Data" },
  { href: "/settings", icon: Settings, label: "Settings", group: "System" },
];

const groups = ["Overview", "Scrapers", "Data", "System"];

export default function Sidebar() {
  const pathname = usePathname();

  const grouped = groups.map((g) => ({
    group: g,
    items: navItems.filter((i) => i.group === g),
  }));

  return (
    <aside className="sidebar">
      {/* Logo */}
      <div style={{
        padding: "20px 20px 16px",
        borderBottom: "1px solid var(--border)",
        display: "flex",
        alignItems: "center",
        gap: "12px",
      }}>
        <div style={{
          width: 36,
          height: 36,
          borderRadius: 10,
          background: "var(--gradient-brand)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          boxShadow: "0 4px 12px var(--accent-blue-glow)",
          flexShrink: 0,
        }}>
          <Bot size={18} color="white" />
        </div>
        <div>
          <div style={{ fontWeight: 700, fontSize: 15, color: "var(--text-primary)" }}>Scrappers</div>
          <div style={{ fontSize: 11, color: "var(--text-muted)" }}>Data Intelligence</div>
        </div>
      </div>

      {/* Navigation */}
      <nav style={{ flex: 1, padding: "12px 0", overflow: "auto" }}>
        {grouped.map(({ group, items }) => (
          <div key={group} style={{ marginBottom: 4 }}>
            <div style={{
              padding: "10px 24px 4px",
              fontSize: 10,
              fontWeight: 700,
              color: "var(--text-muted)",
              textTransform: "uppercase",
              letterSpacing: "0.1em",
            }}>
              {group}
            </div>
            {items.map((item) => {
              const isActive = pathname === item.href;
              const Icon = item.icon;
              return (
                <Link key={item.href} href={item.href} className={`nav-item ${isActive ? "active" : ""}`}>
                  <Icon size={16} />
                  <span style={{ flex: 1 }}>{item.label}</span>
                  {item.highlight && !isActive && (
                    <span style={{
                      fontSize: 9,
                      fontWeight: 700,
                      padding: "2px 6px",
                      borderRadius: 4,
                      background: "rgba(59,130,246,0.15)",
                      color: "var(--accent-blue)",
                      textTransform: "uppercase",
                      letterSpacing: "0.05em",
                    }}>Core</span>
                  )}
                  {isActive && <ChevronRight size={12} style={{ opacity: 0.5 }} />}
                </Link>
              );
            })}
          </div>
        ))}
      </nav>

      {/* Footer */}
      <div style={{
        padding: "12px 20px",
        borderTop: "1px solid var(--border)",
        fontSize: 11,
        color: "var(--text-muted)",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <span className="pulse-dot" style={{ background: "var(--accent-emerald)" }} />
          Backend connected
        </div>
        <div style={{ marginTop: 4 }}>v1.0.0</div>
      </div>
    </aside>
  );
}
