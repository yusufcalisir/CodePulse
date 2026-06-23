"use client";

import { useState } from "react";
import Link from "next/link";
import {
  GitBranch,
  Plus,
  RefreshCw,
  Clock,
  ArrowRight,
} from "lucide-react";
import { timeAgo } from "@/lib/utils";
import type { Repository } from "@/types";

// ── Mock repos for MVP demo ──
const MOCK_REPOS: Repository[] = [
  {
    id: 1,
    github_id: 123456,
    name: "frontend",
    full_name: "codepulse/frontend",
    org: "codepulse",
    default_branch: "main",
    synced_at: "2026-06-23T14:30:00Z",
    created_at: "2026-06-01T10:00:00Z",
    updated_at: "2026-06-23T14:30:00Z",
  },
  {
    id: 2,
    github_id: 234567,
    name: "api",
    full_name: "codepulse/api",
    org: "codepulse",
    default_branch: "main",
    synced_at: "2026-06-23T12:00:00Z",
    created_at: "2026-06-01T10:00:00Z",
    updated_at: "2026-06-23T12:00:00Z",
  },
  {
    id: 3,
    github_id: 345678,
    name: "infra",
    full_name: "codepulse/infra",
    org: "codepulse",
    default_branch: "main",
    synced_at: null,
    created_at: "2026-06-10T10:00:00Z",
    updated_at: "2026-06-10T10:00:00Z",
  },
];

/**
 * Repository list page — shows all tracked repos with sync status.
 */
export default function ReposPage() {
  const [repos] = useState<Repository[]>(MOCK_REPOS);
  const [syncingRepo, setSyncingRepo] = useState<string | null>(null);
  const [showAddModal, setShowAddModal] = useState(false);
  const [newRepoName, setNewRepoName] = useState("");

  const handleSync = async (fullName: string) => {
    setSyncingRepo(fullName);
    // TODO: await syncRepository(fullName);
    setTimeout(() => setSyncingRepo(null), 2000);
  };

  const handleAddRepo = async () => {
    if (!newRepoName.includes("/")) return;
    // TODO: await syncRepository(newRepoName);
    setShowAddModal(false);
    setNewRepoName("");
  };

  return (
    <div className="max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Repositories</h1>
          <p className="text-sm mt-1" style={{ color: "var(--text-secondary)" }}>
            {repos.length} repositories tracked
          </p>
        </div>
        <button
          onClick={() => setShowAddModal(true)}
          className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold text-white transition-all duration-200 hover:scale-105"
          style={{
            background: "linear-gradient(135deg, var(--color-brand-600), var(--color-brand-500))",
            boxShadow: "0 2px 12px rgba(99, 102, 241, 0.25)",
          }}
          id="add-repo-btn"
        >
          <Plus size={16} />
          Add Repository
        </button>
      </div>

      {/* Repo Grid */}
      <div className="grid gap-4">
        {repos.map((repo, i) => (
          <div
            key={repo.id}
            className="glass-card p-5 flex items-center justify-between animate-fade-in-up opacity-0"
            style={{ animationDelay: `${i * 80}ms` }}
          >
            {/* Left: repo info */}
            <div className="flex items-center gap-4">
              <div
                className="w-11 h-11 rounded-xl flex items-center justify-center"
                style={{
                  background: "linear-gradient(135deg, rgba(99, 102, 241, 0.15), rgba(99, 102, 241, 0.05))",
                }}
              >
                <GitBranch size={20} style={{ color: "var(--color-brand-400)" }} />
              </div>
              <div>
                <h3 className="text-sm font-semibold">{repo.full_name}</h3>
                <div className="flex items-center gap-3 mt-1">
                  <span className="text-xs" style={{ color: "var(--text-muted)" }}>
                    {repo.default_branch}
                  </span>
                  {repo.synced_at && (
                    <span
                      className="flex items-center gap-1 text-xs"
                      style={{ color: "var(--text-muted)" }}
                    >
                      <Clock size={10} />
                      Synced {timeAgo(repo.synced_at)}
                    </span>
                  )}
                  {!repo.synced_at && (
                    <span
                      className="text-xs px-2 py-0.5 rounded-full"
                      style={{
                        color: "var(--color-warning)",
                        background: "rgba(245, 158, 11, 0.1)",
                      }}
                    >
                      Not synced
                    </span>
                  )}
                </div>
              </div>
            </div>

            {/* Right: actions */}
            <div className="flex items-center gap-3">
              <button
                onClick={() => handleSync(repo.full_name)}
                disabled={syncingRepo === repo.full_name}
                className="p-2.5 rounded-xl transition-all duration-200 hover:scale-105"
                style={{
                  background: "var(--surface-hover)",
                  color: "var(--text-secondary)",
                }}
                title="Sync now"
              >
                <RefreshCw
                  size={16}
                  className={syncingRepo === repo.full_name ? "animate-spin" : ""}
                />
              </button>
              <Link
                href={`/repos/${repo.id}`}
                className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-medium transition-all duration-200 hover:scale-105"
                style={{
                  background: "var(--surface-hover)",
                  color: "var(--text-secondary)",
                }}
              >
                View Metrics
                <ArrowRight size={14} />
              </Link>
            </div>
          </div>
        ))}
      </div>

      {/* Add Repo Modal */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div
            className="glass-card p-8 w-full max-w-md"
            style={{ background: "var(--surface-card)" }}
          >
            <h2 className="text-lg font-bold mb-2">Add Repository</h2>
            <p className="text-sm mb-6" style={{ color: "var(--text-secondary)" }}>
              Enter the full repository name (e.g., <code className="text-xs" style={{ color: "var(--color-brand-400)" }}>org/repo</code>)
            </p>
            <input
              type="text"
              value={newRepoName}
              onChange={(e) => setNewRepoName(e.target.value)}
              placeholder="owner/repository"
              className="w-full px-4 py-3 rounded-xl text-sm outline-none border transition-colors duration-200 focus:border-[var(--color-brand-500)]"
              style={{
                background: "var(--surface-elevated)",
                borderColor: "var(--surface-border)",
                color: "var(--text-primary)",
              }}
              id="repo-input"
              autoFocus
            />
            <div className="flex gap-3 mt-6 justify-end">
              <button
                onClick={() => setShowAddModal(false)}
                className="px-5 py-2.5 rounded-xl text-sm font-medium transition-colors"
                style={{ color: "var(--text-secondary)" }}
              >
                Cancel
              </button>
              <button
                onClick={handleAddRepo}
                disabled={!newRepoName.includes("/")}
                className="px-5 py-2.5 rounded-xl text-sm font-semibold text-white transition-all duration-200 hover:scale-105 disabled:opacity-40 disabled:hover:scale-100"
                style={{
                  background: "linear-gradient(135deg, var(--color-brand-600), var(--color-brand-500))",
                }}
                id="confirm-add-btn"
              >
                Start Sync
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
