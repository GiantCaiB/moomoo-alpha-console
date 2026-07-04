"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  TrendingUp,
  Briefcase,
  ListOrdered,
  ShieldAlert,
  FlaskConical,
  Settings,
  Lock,
} from "lucide-react";
import { useBrokerHealth } from "@/app/providers";

const links = [
  { href: "/", label: "Cockpit", icon: LayoutDashboard },
  { href: "/signals", label: "Entry Signals", icon: TrendingUp },
  { href: "/positions", label: "Portfolio", icon: Briefcase },
  { href: "/orders", label: "Orders", icon: ListOrdered },
  { href: "/risk", label: "Risk", icon: ShieldAlert },
  { href: "/backtests", label: "Labs", icon: FlaskConical },
  { href: "/settings", label: "Settings", icon: Settings },
];

export default function Sidebar() {
  const pathname = usePathname();
  const { health } = useBrokerHealth();

  const env = health?.account_environment ?? "mock";
  const connected = health?.connected ?? true;

  let modeLabel = "Mock Mode";
  let dotClass = "status-dot-green";

  if (env === "moomoo_real") {
    modeLabel = connected ? "Real Account (R/O)" : "Moomoo Disconnected";
    dotClass = connected ? "status-dot-green" : "status-dot-red";
  } else if (env === "moomoo_simulate") {
    modeLabel = connected ? "Sim Account (R/O)" : "Moomoo Disconnected";
    dotClass = connected ? "status-dot-amber" : "status-dot-red";
  } else if (env === "moomoo_disconnected") {
    modeLabel = "Moomoo Disconnected";
    dotClass = "status-dot-red";
  } else if (env === "paper") {
    modeLabel = "Paper Mode";
    dotClass = "status-dot-amber";
  }

  return (
    <aside className="w-60 h-screen glassy border-l-0 border-t-0 border-b-0 flex flex-col py-6 px-3 fixed left-0 top-0 z-40">
      <div className="px-4 mb-8">
        <h1 className="text-xl font-semibold text-text-primary tracking-tight">
          Alpha <span className="text-accent-green">Cockpit</span>
        </h1>
        <p className="text-xs text-text-muted mt-1">Read-only research console</p>
      </div>

      <nav className="flex-1 space-y-1">
        {links.map((link) => {
          const isActive =
            pathname === link.href ||
            (link.href !== "/" && pathname.startsWith(link.href));
          const Icon = link.icon;
          return (
            <Link
              key={link.href}
              href={link.href}
              className={`sidebar-link ${isActive ? "sidebar-link-active" : ""}`}
            >
              <Icon size={18} />
              <span>{link.label}</span>
            </Link>
          );
        })}
      </nav>

      <div className="px-4 pt-4 border-t border-surface-border space-y-3">
        <div className="flex items-center gap-2">
          <span className={`status-dot ${dotClass}`} />
          <span className="text-xs text-text-muted">{modeLabel}</span>
        </div>
        <div className="flex items-center gap-2 rounded-lg border border-surface-border bg-surface-hover/40 px-3 py-2 text-xs text-text-secondary">
          <Lock size={12} className="text-accent-amber" />
          <span>Read-only active</span>
        </div>
      </div>
    </aside>
  );
}
