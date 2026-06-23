/** Utility functions for formatting and display. */

import { clsx, type ClassValue } from "clsx";

/**
 * Merge Tailwind class names with conflict resolution.
 * Since we don't have tailwind-merge installed, using simple clsx.
 */
export function cn(...inputs: ClassValue[]) {
  return clsx(inputs);
}

/**
 * Format hours into a human-readable duration string.
 * 0.5 → "30m", 2.3 → "2.3h", 48 → "2.0d"
 */
export function formatDuration(hours: number): string {
  if (hours < 1) {
    return `${Math.round(hours * 60)}m`;
  }
  if (hours < 24) {
    return `${hours.toFixed(1)}h`;
  }
  return `${(hours / 24).toFixed(1)}d`;
}

/**
 * Format a number with optional suffix.
 */
export function formatNumber(n: number, decimals = 1): string {
  if (n >= 1000) {
    return `${(n / 1000).toFixed(decimals)}k`;
  }
  return n.toFixed(n % 1 === 0 ? 0 : decimals);
}

/**
 * Calculate percentage change between two values.
 */
export function percentChange(current: number, previous: number): number {
  if (previous === 0) return 0;
  return ((current - previous) / previous) * 100;
}

/**
 * Format a timestamp as a relative time string.
 */
export function timeAgo(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const seconds = Math.floor((now.getTime() - date.getTime()) / 1000);

  if (seconds < 60) return "just now";
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  if (seconds < 604800) return `${Math.floor(seconds / 86400)}d ago`;
  return date.toLocaleDateString();
}

/**
 * Extract a short week label from ISO week format.
 * "2026-W20" → "W20"
 */
export function shortWeek(week: string): string {
  const match = week.match(/W(\d+)/);
  return match ? `W${match[1]}` : week;
}
