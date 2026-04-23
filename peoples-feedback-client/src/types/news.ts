/**
 * Types synced with backend news-platform-final schema.
 * Field names match article_to_response() in articles.py EXACTLY.
 */

export interface NewsArticle {
  id: number;
  source_id: number;
  original_title: string;
  original_content?: string;
  original_url?: string;
  original_language?: string;
  ai_status?: string;  // AI_SUCCESS | LOCAL_PARAPHRASE | etc.
  published_at?: string;
  translated_title?: string;
  translated_content?: string;
  rephrased_title?: string;
  rephrased_content?: string;
  /** Telugu title — set after AI processing */
  telugu_title?: string;
  /** Telugu content (HTML) — set after AI processing */
  telugu_content?: string;
  category?: string;
  slug?: string;
  tags: string[];
  content_hash: string;
  is_duplicate: boolean;
  flag: 'P' | 'N' | 'A' | 'Y' | 'D';
  rank_score: number;
  image_url?: string;
  author?: string;
  submitted_by?: string;
  created_at: string;
  updated_at: string;
  processed_at?: string;
  source_name?: string;
  is_posted_fb?: boolean;
}

export interface ArticleListResponse {
  articles: NewsArticle[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface CategoryArticlesResponse {
  articles: NewsArticle[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  category: string;
}

export interface CategoryResponse {
  id: number;
  name: string;
  slug: string;
  description?: string;
  is_active: boolean;
  article_count: number;
}

// ── Display helpers ───────────────────────────────────────────────────

/** True if article has Telugu translation */
export const hasTelugu = (a: NewsArticle): boolean =>
  !!(a.telugu_title && a.telugu_title.trim() && a.telugu_content && a.telugu_content.trim());

/** Get display title for a given language */
const STRIP_SOURCES = /\b(Times of India|Al Jazeera|OneIndia|GreatAndhra|Great Andhra|Eenadu|Sakshi|TV9 Telugu|TV9|PrabhaNews|Prabha News|Telugu123|TeluguTimes|Telugu Times|Google News|ANI|PTI|IANS|Reuters|AFP|BBC|NDTV|Times Now|Republic|Zee News|ABP|India Today|News18)\b/gi;
function stripSourceNames(text: string): string {
  return text ? text.replace(STRIP_SOURCES, 'Peoples Feedback') : text;
}

export const getTitle = (a: NewsArticle, lang: 'en' | 'te' = 'en'): string => {
  if (lang === 'te') {
    // Telugu: prefer telugu_title, then original (for Telugu-source articles not yet AI processed)
    const teTitle = a.telugu_title?.trim();
    if (teTitle) return teTitle;
    // If article is from a Telugu source, show original_title as fallback
    if ((a as any).original_language === 'te') return stripHtml(a.original_title || '');
  }
  return stripSourceNames(stripHtml(a.rephrased_title || a.original_title || ''));
};

/** Get display content (HTML safe) for a given language */
export function sanitizeArticleHtml(html: string): string {
  if (!html || !html.trim()) return '';
  if (!/<[a-zA-Z]/.test(html)) {
    return html.trim().split(/\n\s*\n/).filter(Boolean)
      .map(p => `<p>${p.trim().replace(/\n/g, ' ')}</p>`).join('\n');
  }
  // Fix unclosed strong tags that make entire article bold
  html = html.replace(/<p><strong>((?:(?!<\/strong>).){200,})<\/p>/g,
    (_m, inner) => `<p><strong>${inner}</strong></p>`);
  // Remove empty list items
  html = html.replace(/<li><b>[^<]+:<\/b>\s*<\/li>/g, '');
  html = html.replace(/<ul>\s*<\/ul>/g, '');
  // Remove duplicate paragraphs
  const seen = new Set<string>();
  html = html.replace(/<p>(.*?)<\/p>/gs, (_m, inner) => {
    const key = inner.trim().toLowerCase().slice(0, 80);
    if (seen.has(key)) return '';
    seen.add(key);
    return `<p>${inner}</p>`;
  });
  return html.trim();
}

export const getContent = (a: NewsArticle, lang: 'en' | 'te' = 'en'): string => {
  let raw: string;
  if (lang === 'te') {
    // Telugu: prefer AI-generated Telugu, then original content for Telugu sources
    raw = a.telugu_content?.trim()
      ? a.telugu_content
      : ((a as any).original_language === 'te'
          ? (a.original_content || a.rephrased_content || '')
          : (a.rephrased_content || a.original_content || ''));
  } else {
    raw = a.rephrased_content || a.original_content || '';
  }
  if (!raw) return '';
  // Already HTML — sanitize and return
  if (/<(p|br|div|ul|li|b|strong)/i.test(raw)) {
    return stripSourceNames(sanitizeArticleHtml(raw));
  }
  // Plain text — wrap paragraphs
  return stripSourceNames(raw)
    .trim()
    .split(/\n\s*\n/)
    .map(p => p.trim())
    .filter(Boolean)
    .map(p => `<p>${p.replace(/\n/g, '<br />')}</p>`)
    .join('');
};

/** Plain-text excerpt */
export const getSummary = (a: NewsArticle, max = 180, lang: 'en' | 'te' = 'en'): string => {
  let raw = '';
  if (lang === 'te') {
    raw = (a.telugu_content || a.rephrased_content || a.original_content || '');
  } else {
    raw = (a.rephrased_content || a.original_content || '');
  }
  
  raw = stripSourceNames(raw)
    .replace(/<[^>]*>/g, '')
    .replace(/&nbsp;/g, ' ')
    .trim();
  return raw.length > max ? raw.slice(0, max).trimEnd() + '…' : raw;
};

import { API_BASE } from "@/lib/api";

/**
 * Resolve the display image for an article.
 *
 * The backend already applies USE_CUSTOM_IMAGES logic:
 *   - USE_CUSTOM_IMAGES=true  → article.image_url is always a /placeholders/ path
 *   - USE_CUSTOM_IMAGES=false → article.image_url is the real scraped URL (or placeholder fallback)
 *
 * Frontend behaviour:
 *   1. Relative /uploads/ path → prepend API base (our own upload)
 *   2. /placeholders/ path → return as-is (served from our public folder)
 *   3. External http(s) URL → return as-is (real scraped image)
 *   4. Empty / invalid → fall back to category placeholder
 */
export const getImage = (a: NewsArticle): string => {
  const u = a.image_url?.trim();
  if (!u || u === "null" || u === "undefined" || u === "") {
    return categoryPlaceholder(a.category);
  }
  // Placeholder path served from our public folder
  if (u.startsWith("/placeholders/")) return u;
  // Uploaded file on our own server
  if (u.startsWith("/uploads/") || u.startsWith("uploads/")) {
    const base = (API_BASE || "").replace(/\/$/, "");
    return `${base}/${u.replace(/^\//, "")}`;
  }
  // Real external URL
  if (u.startsWith("http://") || u.startsWith("https://")) return u;
  // Fallback
  return categoryPlaceholder(a.category);
};

/**
 * Force a category placeholder regardless of image_url.
 * Use this when you always want the branded category image.
 */
export const getCategoryImage = (a: NewsArticle): string =>
  categoryPlaceholder(a.category);

/** Strip HTML tags */
function stripHtml(s: string): string {
  return s ? s.replace(/<\/?[^>]+(>|$)/g, '').trim() : '';
}

/** Category-specific placeholder images */
export function categoryPlaceholder(cat?: string): string {
  const map: Record<string, string> = {
    home:          '/placeholders/general.png',
    general:       '/placeholders/general.png',
    politics:      '/placeholders/politics.png',
    andhra:        '/placeholders/politics.png',
    telangana:     '/placeholders/politics.png',
    world:         '/placeholders/world.png',
    business:      '/placeholders/business.png',
    tech:          '/placeholders/tech.png',
    technology:    '/placeholders/tech.png',
    sports:        '/placeholders/sports.png',
    entertainment: '/placeholders/entertainment.png',
    
    health:        '/placeholders/health.png',
    science:       '/placeholders/science.png',
    crime:         '/placeholders/general.png',
    weather:       '/placeholders/general.png',
    hindi:         '/placeholders/general.png',
    education:     '/placeholders/general.png',
    travel:        '/placeholders/general.png',
  };
  const key = (cat || '').toLowerCase().trim();
  return map[key] ?? map.general ?? map.home;
}

/** Canonical categories — MUST match backend config.py CATEGORIES */
export const CANONICAL_CATEGORIES = [
  'Home', 'World', 'Politics', 'Business', 'Tech',
  'Health', 'Science', 'Entertainment', 'Events', 'Sports',
  'Surveys', 'Polls',
] as const;

/** Default categories for fallback (if API unavailable) */
export const DEFAULT_CATEGORIES = [...CANONICAL_CATEGORIES] as string[];

/** Estimated read time (minutes) from HTML content */
export const readTime = (html: string): number => {
  const words = html.replace(/<[^>]*>/g, '').split(/\s+/).filter(Boolean).length;
  return Math.max(1, Math.ceil(words / 220));
};

/** Wish/Greeting item for birthday, festival, etc. */
export interface WishItem {
  id: number;
  title: string;
  message?: string;
  wish_type: string;          // birthday, festival, anniversary, custom
  person_name?: string;
  occasion_date?: string;
  image_url?: string;
  is_active: boolean;
  display_on_home: boolean;
  likes_count: number;
  created_by?: string;
  created_at: string;
  expires_at?: string;
}

/** Poll option */
export interface PollOption {
  id: number;
  option_text: string;
  votes_count: number;
}

/** Active poll */
export interface PollItem {
  id: number;
  question: string;
  options: PollOption[];
  is_active: boolean;
  created_at: string;
  expires_at?: string;
}
