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
export const getTitle = (a: NewsArticle, lang: 'en' | 'te' = 'en'): string => {
  if (lang === 'te' && a.telugu_title?.trim()) return a.telugu_title.trim();
  return stripHtml(a.rephrased_title || a.original_title || '');
};

/** Get display content (HTML safe) for a given language */
export const getContent = (a: NewsArticle, lang: 'en' | 'te' = 'en'): string => {
  const raw =
    lang === 'te' && a.telugu_content?.trim()
      ? a.telugu_content
      : a.rephrased_content || a.original_content || '';
  if (!raw) return '';
  // Already HTML — return as-is
  if (/<(p|br|div|ul|li|b|strong)/i.test(raw)) return raw;
  // Plain text — wrap paragraphs
  return raw
    .trim()
    .split(/\n\s*\n/)
    .map(p => p.trim())
    .filter(Boolean)
    .map(p => `<p>${p.replace(/\n/g, '<br />')}</p>`)
    .join('');
};

/** Plain-text excerpt */
export const getSummary = (a: NewsArticle, max = 180): string => {
  const raw = (a.rephrased_content || a.original_content || '')
    .replace(/<[^>]*>/g, '')
    .replace(/&nbsp;/g, ' ')
    .trim();
  return raw.length > max ? raw.slice(0, max).trimEnd() + '…' : raw;
};

import { API_BASE } from "@/lib/api";

/** Best available image URL */
export const getImage = (a: NewsArticle): string => {
  const u = a.image_url?.trim();
  if (!u) return categoryPlaceholder(a.category);
  if (u.startsWith('/uploads')) {
    const base = API_BASE.replace(/\/$/, '');
    return `${base}${u}`;
  }
  return u;
};

/** Strip HTML tags */
function stripHtml(s: string): string {
  return s ? s.replace(/<\/?[^>]+(>|$)/g, '').trim() : '';
}

/** Category-specific placeholder images */
export function categoryPlaceholder(cat?: string): string {
  const map: Record<string, string> = {
    home:          'https://images.unsplash.com/photo-1504711434969-e33886168d6c?w=800&q=80',
    world:         'https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=800&q=80',
    politics:      'https://images.unsplash.com/photo-1529107386315-e1a2ed48a620?w=800&q=80',
    business:      'https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=800&q=80',
    tech:          'https://images.unsplash.com/photo-1518770660439-4636190af475?w=800&q=80',
    technology:    'https://images.unsplash.com/photo-1518770660439-4636190af475?w=800&q=80',
    health:        'https://images.unsplash.com/photo-1576091160399-112ba8d25d1d?w=800&q=80',
    science:       'https://images.unsplash.com/photo-1507413245164-6160d8298b31?w=800&q=80',
    entertainment: 'https://images.unsplash.com/photo-1603190287605-e6ade32fa852?w=800&q=80',
    events:        'https://images.unsplash.com/photo-1540575467063-178a50c2df87?w=800&q=80',
    sports:        'https://images.unsplash.com/photo-1461896836934-bd45ba6b0e28?w=800&q=80',
    education:     'https://images.unsplash.com/photo-1503676260728-1c00da094a0b?w=800&q=80',
    environment:   'https://images.unsplash.com/photo-1441974231531-c6227db76b6e?w=800&q=80',
    travel:        'https://images.unsplash.com/photo-1488646953014-85cb44e25828?w=800&q=80',
    surveys:       'https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=800&q=80',
    polls:         'https://images.unsplash.com/photo-1540910419892-4a39d20b2944?w=800&q=80',
  };
  const key = (cat || '').toLowerCase().trim();
  return map[key] ?? map.home;
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
