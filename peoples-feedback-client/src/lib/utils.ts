import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function getPlaceholderImage(category?: string | null) {
  const images: Record<string, string> = {
    world: "https://images.unsplash.com/photo-1522071820081-009f0129c71c?auto=format&fit=crop&q=80",
    business: "https://images.unsplash.com/photo-1611974765270-ca12586343bb?auto=format&fit=crop&q=80",
    tech: "https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&q=80",
    science: "https://images.unsplash.com/photo-1507413245164-6160d8298b31?auto=format&fit=crop&q=80",
    health: "https://images.unsplash.com/photo-1505751172876-fa1923c5c528?auto=format&fit=crop&q=80",
    default: "https://images.unsplash.com/photo-1504711434969-e33886168f5c?auto=format&fit=crop&q=80"
  };
  return images[(category || 'default').toLowerCase()] || images.default;
}

export function formatDate(dateStr?: string | Date) {
  if (!dateStr) return "Just Now";
  const date = new Date(dateStr);
  const now = new Date();
  const diff = now.getTime() - date.getTime();

  // If less than 24h, show hours ago
  if (diff < 86400000) {
    const hours = Math.floor(diff / 3600000);
    if (hours < 1) return "LIVE";
    return `${hours}H AGO`;
  }
  return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

export function getReadTime(article: any) {
  const words = (article.content || article.summary || "").split(" ").length;
  const minutes = Math.ceil(words / 200) || 3;
  return `${minutes} MIN`;
}
