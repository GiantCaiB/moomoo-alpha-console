"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  TrendingUp,
  Eye,
  Briefcase,
  ListOrdered,
  ShieldAlert,
  FlaskConical,
  Settings,
} from "lucide-react";
import { useBrokerHealth } from "@/app/providers";

const links = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/signals", label: "Signals", icon: TrendingUp },
  { href: "/watchlist", label: "Watchlist", icon: Eye },
  { href: "/positions", label: "Positions", icon: Briefcase },
  { href: "/orders", label: "Orders", icon: ListOrdered },
  { href: "/risk", label: "Risk", icon: ShieldAlert },
  { href: "/backtests", label: "Backtests", icon: FlaskConical },
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
    modeLabel = connected ? "Moomoo Real (R/O)" : "Moomoo Disconnected";
    dotClass = connected ? "status-dot-green" : "status-dot-red";
  } else if (env === "moomoo_simulate") {
    modeLabel = connected ? "Moomoo Sim (R/O)" : "Moomoo Disconnected";
    dotClass = connected ? "status-dot-amber" : "status-dot-red";
  } else if (env === "moomoo_disconnected") {
    modeLabel = "Moomoo Disconnected";
    dotClass = "status-dot-red";
  } else if (env === "paper") {
    modeLabel = "Paper Mode";
    dotClass = "status-dot-amber";
  }

  return (
    <aside className="w-56 h-screen glassy border-l-0 border-t-0 border-b-0 flex flex-col py-6 px-3 fixed left-0 top-0 z-40">
      <div className="px-4 mb-8">
        <h1 className="text-lg font-bold text-accent-green font-mono tracking-tight">
          Moomoo<span className="text-text-primary"> Alpha</span>
        </h1>
        <p className="text-xs text-text-muted mt-0.5">Console v0.1.0</p>
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

      <div className="px-4 pt-4 border-t border-surface-border">
        <div className="flex items-center gap-2">
          <span className={`status-dot ${dotClass}`} />
          <span className="text-xs text-text-muted">{modeLabel}</span>
        </div>
      </div>
    </aside>
  );
}
