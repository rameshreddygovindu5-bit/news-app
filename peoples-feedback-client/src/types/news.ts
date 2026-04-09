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
}

/** GET /api/articles response */
export interface ArticleListResponse {
  articles: NewsArticle[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

/** GET /api/articles/by-category/{cat} response */
export interface CategoryArticlesResponse {
  articles: NewsArticle[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  category: string;
}

/** GET /api/categories response item */
export interface CategoryResponse {
  id: number;
  name: string;
  slug: string;
  description?: string;
  is_active: boolean;
  article_count: number;
}

// ─── Display helpers ───
export const getTitle = (a: NewsArticle): string =>
  stripHtmlWrapper(a.rephrased_title || a.original_title);

export const getContent = (a: NewsArticle): string => {
  const raw = a.rephrased_content || a.original_content || '';
  if (!raw) return '';
  
  // If it already looks like HTML (contains <p> or <br>), return as is
  if (/<(p|br|div|ul|li|b|strong)/i.test(raw)) return raw;
  
  // Otherwise, convert newlines to paragraphs/breaks for readability
  return raw
    .trim()
    .split(/\n\s*\n/)
    .map(p => p.trim())
    .filter(p => p.length > 0)
    .map(p => `<p class="font-medium text-black mb-4">${p.replace(/\n/g, '<br />')}</p>`)
    .join('');
};

export const getSummary = (a: NewsArticle, max = 180): string => {
  const content = a.rephrased_content || a.original_content || '';
  const raw = content.replace(/<[^>]*>/g, '').replace(/&nbsp;/g, ' ').trim();
  return raw.length > max ? raw.slice(0, max).trimEnd() + '…' : raw;
};

export const getImage = (a: NewsArticle): string =>
  a.image_url && a.image_url.trim() !== '' ? a.image_url : categoryPlaceholder(a.category);

/** Strip wrapping HTML tags but keep inner text */
function stripHtmlWrapper(s: string): string {
  if (!s) return '';
  return s.replace(/<\/?[^>]+(>|$)/g, '').trim();
}

/** Category-specific placeholder images — verified working Unsplash URLs */
function categoryPlaceholder(cat?: string): string {
  const map: Record<string, string> = {
    // Main DB categories
    home: 'https://images.unsplash.com/photo-1504711434969-e33886168d6c?w=800&q=80',
    world: 'https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=800&q=80',
    politics: 'https://images.unsplash.com/photo-1529107386315-e1a2ed48a620?w=800&q=80',
    business: 'https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=800&q=80',
    tech: 'https://images.unsplash.com/photo-1518770660439-4636190af475?w=800&q=80',
    technology: 'https://images.unsplash.com/photo-1518770660439-4636190af475?w=800&q=80',
    health: 'https://images.unsplash.com/photo-1576091160399-112ba8d25d1d?w=800&q=80',
    science: 'https://images.unsplash.com/photo-1507413245164-6160d8298b31?w=800&q=80',
    entertainment: 'https://images.unsplash.com/photo-1603190287605-e6ade32fa852?w=800&q=80',
    events: 'https://images.unsplash.com/photo-1540575467063-178a50c2df87?w=800&q=80',
    // Extended categories
    sports: 'https://images.unsplash.com/photo-1461896836934-bd45ba6b0e28?w=800&q=80',
    movies: 'https://images.unsplash.com/photo-1478720568477-152d9b164e26?w=800&q=80',
    education: 'https://images.unsplash.com/photo-1503676260728-1c00da094a0b?w=800&q=80',
    crime: 'https://images.unsplash.com/photo-1453873531674-2151bcd01707?w=800&q=80',
    international: 'https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=800&q=80',
    national: 'https://images.unsplash.com/photo-1532375810709-75b1da00537c?w=800&q=80',
    general: 'https://images.unsplash.com/photo-1504711434969-e33886168d6c?w=800&q=80',
    opinion: 'https://images.unsplash.com/photo-1457369804613-52c61a468e7d?w=800&q=80',
    lifestyle: 'https://images.unsplash.com/photo-1490750967868-88aa4f44baee?w=800&q=80',
    travel: 'https://images.unsplash.com/photo-1488646953014-85cb44e25828?w=800&q=80',
    food: 'https://images.unsplash.com/photo-1476224203421-9ac39bcb3327?w=800&q=80',
    environment: 'https://images.unsplash.com/photo-1441974231531-c6227db76b6e?w=800&q=80',
    finance: 'https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=800&q=80',
    space: 'https://images.unsplash.com/photo-1446776811953-b23d57bd21aa?w=800&q=80',
  };
  const key = (cat || '').toLowerCase().trim();
  return map[key] || 'https://images.unsplash.com/photo-1504711434969-e33886168d6c?w=800&q=80';
}

/** Default category list (fallback if API categories unavailable) */
export const DEFAULT_CATEGORIES = [
  'Home', 'World', 'Politics', 'Business', 'Tech',
  'Health', 'Science', 'Entertainment', 'Events'
] as const;

export { categoryPlaceholder };
