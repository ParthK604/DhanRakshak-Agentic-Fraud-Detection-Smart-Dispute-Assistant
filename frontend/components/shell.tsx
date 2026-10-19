"use client";

import { Activity, AlertTriangle, BarChart3, ChevronRight, CircleDollarSign, LayoutDashboard, Menu, Moon, ShieldCheck, Store, Sun } from "lucide-react";
import { useTheme } from "next-themes";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "@/lib/api";

const nav = [
  { href: "/", label: "Overview", icon: LayoutDashboard },
  { href: "/transactions", label: "Transactions", icon: CircleDollarSign },
  { href: "/disputes", label: "Disputes", icon: AlertTriangle },
  { href: "/merchants", label: "Merchants", icon: Store },
];

export function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { resolvedTheme, setTheme } = useTheme();
  const [mobileOpen, setMobileOpen] = useState(false);
  const health = useQuery({ queryKey: ["health"], queryFn: api.health, refetchInterval: 30_000 });
  const healthy = health.data?.status === "ok";
  return (
    <div className="app-shell">
      <aside className={`sidebar ${mobileOpen ? "sidebar-open" : ""}`}>
        <div className="brand"><span className="brand-mark"><ShieldCheck size={22} /></span><span>Dhan<span>Rakshak</span></span></div>
        <p className="eyebrow sidebar-label">COMMAND CENTER</p>
        <nav className="nav-list" aria-label="Primary navigation">
          {nav.map(({ href, label, icon: Icon }) => (
            <Link key={href} href={href} className={`nav-item ${pathname === href ? "active" : ""}`} onClick={() => setMobileOpen(false)}>
              <Icon size={18} /><span>{label}</span>{pathname === href && <ChevronRight className="nav-chevron" size={15} />}
            </Link>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="sidebar-note"><BarChart3 size={17} /><div><strong>Three layers. One shield.</strong><small>Risk, disputes, and merchant trust.</small></div></div>
          <div className="sidebar-build">PAYPAL AI HACKATHON · 2026</div>
        </div>
      </aside>
      {mobileOpen && <button className="mobile-scrim" aria-label="Close menu" onClick={() => setMobileOpen(false)} />}
      <main className="main-area">
        <header className="topbar">
          <button className="icon-button mobile-menu" aria-label="Open menu" onClick={() => setMobileOpen(true)}><Menu size={20} /></button>
          <div className="topbar-context"><span className="live-dot" />Protection is active</div>
          <div className="topbar-actions">
            <div className="health-pill" title="Backend service health">
              <Activity size={15} /><span className={healthy ? "health-good" : "health-bad"}>{health.isLoading ? "Checking systems" : healthy ? "All systems operational" : "System attention"}</span>
              <span className="health-dots"><i className={health.data?.services?.paypal?.ok ? "ok" : "bad"} /><i className={health.data?.services?.mongodb?.ok ? "ok" : "bad"} /><i className={health.data?.services?.groq?.ok ? "ok" : "bad"} /></span>
            </div>
            <button className="icon-button" aria-label="Toggle theme" onClick={() => setTheme(resolvedTheme === "dark" ? "light" : "dark")}>{resolvedTheme === "dark" ? <Sun size={18} /> : <Moon size={18} />}</button>
          </div>
        </header>
        <div className="content">{children}</div>
      </main>
    </div>
  );
}
