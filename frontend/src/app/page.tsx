import { Zap, GitPullRequest, BarChart3, Clock, ArrowRight } from "lucide-react";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "CodePulse — Engineering Intelligence Layer for GitHub Organizations",
  description:
    "Engineering intelligence layer for GitHub organizations. Track PR cycle time, review latency, throughput, and get AI-powered insights and decision support from your GitHub data.",
};

/**
 * Landing page with hero section and GitHub OAuth login.
 */
export default function LandingPage() {
  return (
    <div
      className="min-h-screen flex flex-col items-center justify-center px-6 relative overflow-hidden"
      style={{ background: "var(--surface-base)" }}
    >
      {/* Background gradient orbs */}
      <div
        className="absolute top-[-200px] left-[-100px] w-[500px] h-[500px] rounded-full blur-[120px] opacity-20"
        style={{ background: "var(--color-brand-500)" }}
      />
      <div
        className="absolute bottom-[-150px] right-[-100px] w-[400px] h-[400px] rounded-full blur-[120px] opacity-15"
        style={{ background: "var(--chart-3)" }}
      />

      {/* Content */}
      <div className="relative z-10 max-w-2xl text-center">
        {/* Badge */}
        <div
          className="inline-flex items-center gap-2 px-4 py-2 rounded-full text-xs font-medium mb-8"
          style={{
            background: "rgba(99, 102, 241, 0.1)",
            border: "1px solid rgba(99, 102, 241, 0.2)",
            color: "var(--color-brand-400)",
          }}
        >
          <Zap size={14} />
          Engineering Intelligence Layer
        </div>

        {/* Headline */}
        <h1 className="text-5xl sm:text-6xl font-bold tracking-tight leading-tight mb-6">
          Engineering Intelligence
          <br />
          <span className="gradient-text">for GitHub Organizations</span>
        </h1>

        {/* Subheadline */}
        <p
          className="text-lg mb-10 max-w-md mx-auto leading-relaxed"
          style={{ color: "var(--text-secondary)" }}
        >
          Not just a dashboard, but a complete decision support system. Get deep engineering insights and actionable guidance from your GitHub data.
        </p>

        {/* CTA */}
        <a
          href="/api/auth/signin"
          className="inline-flex items-center gap-3 px-8 py-4 rounded-2xl text-white font-semibold text-base transition-all duration-300 hover:scale-105 hover:shadow-lg"
          style={{
            background: "linear-gradient(135deg, var(--color-brand-600), var(--color-brand-500))",
            boxShadow: "0 4px 24px rgba(99, 102, 241, 0.3)",
          }}
          id="login-btn"
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z" />
          </svg>
          Continue with GitHub
          <ArrowRight size={18} />
        </a>

        {/* Features */}
        <div className="grid grid-cols-3 gap-6 mt-16">
          {[
            { icon: Clock, label: "Cycle Time", desc: "PR creation to merge" },
            { icon: GitPullRequest, label: "Review Latency", desc: "Time to first review" },
            { icon: BarChart3, label: "Throughput", desc: "Weekly merged PRs" },
          ].map((feature) => (
            <div
              key={feature.label}
              className="glass-card p-5 text-center"
            >
              <div
                className="w-10 h-10 rounded-xl flex items-center justify-center mx-auto mb-3"
                style={{
                  background: "linear-gradient(135deg, rgba(99, 102, 241, 0.2), rgba(99, 102, 241, 0.05))",
                }}
              >
                <feature.icon size={20} style={{ color: "var(--color-brand-400)" }} />
              </div>
              <h3 className="text-sm font-semibold mb-1" style={{ color: "var(--text-primary)" }}>
                {feature.label}
              </h3>
              <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                {feature.desc}
              </p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
