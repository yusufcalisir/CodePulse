"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Terminal,
  GitBranch,
  Lightbulb,
  Zap,
  LogOut,
} from "lucide-react";

const navItems = [
  { href: "/dashboard", label: "Command Center", icon: Terminal },
  { href: "/repos", label: "Repositories", icon: GitBranch },
  { href: "/insights", label: "Decision Support", icon: Lightbulb },
];

/**
 * Sidebar navigation for the dashboard layout.
 */
export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside
      className="fixed left-0 top-0 h-screen w-[260px] flex flex-col border-r z-30"
      style={{
        background: "var(--surface-card)",
        borderColor: "var(--surface-border)",
      }}
    >
      {/* Brand */}
      <div className="p-6 pb-8">
        <Link href="/dashboard" className="flex items-center gap-3 group">
          <div
            className="w-9 h-9 rounded-xl flex items-center justify-center animate-pulse-glow"
            style={{
              background: "linear-gradient(135deg, var(--color-brand-500), var(--color-brand-400))",
            }}
          >
            <Zap size={18} className="text-white" />
          </div>
          <div>
            <span className="text-lg font-bold gradient-text">CodePulse</span>
            <span
              className="block text-[10px] font-medium uppercase tracking-widest"
              style={{ color: "var(--text-muted)" }}
            >
              Intelligence Layer
            </span>
          </div>
        </Link>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-4 space-y-1">
        <span
          className="block text-[10px] font-semibold uppercase tracking-widest px-4 mb-3"
          style={{ color: "var(--text-muted)" }}
        >
          Navigation
        </span>
        {navItems.map((item) => {
          const isActive =
            pathname === item.href || pathname.startsWith(item.href + "/");
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`sidebar-nav-item ${isActive ? "active" : ""}`}
            >
              <item.icon size={18} />
              {item.label}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="p-4 border-t" style={{ borderColor: "var(--surface-border)" }}>
        <button
          className="sidebar-nav-item w-full"
          onClick={() => {
            // Sign out will be handled by NextAuth
            window.location.href = "/api/auth/signout";
          }}
        >
          <LogOut size={18} />
          Sign Out
        </button>
      </div>
    </aside>
  );
}
