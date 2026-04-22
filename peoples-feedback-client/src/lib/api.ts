/**
 * API client — peoples-feedback-client
 * Synced with news-platform-final backend schema.
 * Public endpoints only. Always filters flag=A,Y.
 */
export const API_BASE = (import.meta as any)?.env?.VITE_API_URL || '';
const BASE = API_BASE;

async function get<T>(path: string, params?: Record<string, any>): Promise<T> {
  const url = new URL(path, BASE || window.location.origin);
  if (params) Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== '') url.searchParams.set(k, String(v));
  });
  const res = await fetch(url.toString(), {
    headers: { 'Accept': 'application/json' },
  });
  if (!res.ok) throw new Error(`API ${res.status}: ${res.statusText}`);
  return res.json();
}

async function post<T>(path: string, body?: any): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(`API ${res.status}: ${res.statusText}`);
  return res.json();
}

export const newsApi = {
  /** List published articles. Supports category, keyword, flags/flag, pagination.
   *  - flags (multi): "A,Y" | "Y" — preferred, matches backend `flags` param
   *  - flag  (single): "Y" | "N" etc — for admin use
   *  - Default: flags="A,Y" (all published articles)
   */
  getArticles: (p: {
    page?: number; page_size?: number; category?: string; keyword?: string;
    lang?: string; flag?: string; flags?: string; telugu_page?: string;
  }) => {
    const { flag, flags: explicitFlags, ...rest } = p;
    // Explicit `flags` wins → else single `flag` → else default A,Y
    const resolvedFlags = explicitFlags || (flag ? flag : 'A,Y');  // Default = AI-processed only
    return get<import('@/types/news').ArticleListResponse>('/api/articles', {
      ...rest,
      flags: resolvedFlags,
    });
  },

  /** Top 500 ranked news (flag=Y) */
  getTopNews: (limit = 200) =>
    get<import('@/types/news').NewsArticle[]>('/api/articles/top-news', { limit }),  // Home feed: max 200

  /** Single article by id or slug */
  getArticle: (idOrSlug: number | string) =>
    get<import('@/types/news').NewsArticle>(`/api/articles/${idOrSlug}`),

  /** Articles by category — always published only */
  getByCategory: (cat: string, p?: { page?: number; page_size?: number }) =>
    get<import('@/types/news').CategoryArticlesResponse>(
      `/api/articles/by-category/${encodeURIComponent(cat)}`, { page_size: 50, ...p }),  // Category: 50 per page

  /** Telugu articles — articles with Telugu content OR from Telugu sources */
  getTeluguArticles: (p?: { page?: number; page_size?: number; keyword?: string; date_from?: string; date_to?: string }) =>
    get<import('@/types/news').ArticleListResponse>('/api/articles', {
      ...p, flags: 'A,Y', lang: 'te',   // Strict: AI-processed only (flag A or Y)
    }),

  /** Hindi articles — original_language=hi */
  getHindiArticles: (p?: { page?: number; page_size?: number; keyword?: string }) =>
    get<import('@/types/news').ArticleListResponse>('/api/articles', {
      ...p, flags: 'A,Y', lang: 'hi',
    }),

  /** English-only articles (default home/news pages) */
  getEnglishArticles: (p?: { page?: number; page_size?: number; category?: string; keyword?: string }) =>
    get<import('@/types/news').ArticleListResponse>('/api/articles', {
      ...p, flags: 'A,Y', lang: 'en',
    }),

  /** Categories from backend DB (dynamic) */
  getCategories: () =>
    get<import('@/types/news').CategoryResponse[]>('/api/categories'),

  /** Active wishes for public display */
  getActiveWishes: (wish_type?: string) =>
    get<import('@/types/news').WishItem[]>('/api/wishes/active', { wish_type }),

  /** Wishes marked for homepage display */
  getHomeWishes: () =>
    get<import('@/types/news').WishItem[]>('/api/wishes/home'),

  /** Like a wish */
  likeWish: (id: number) =>
    post<{ success: boolean; likes_count: number }>(`/api/wishes/${id}/like`),

  /** Active polls for public display */
  getPolls: () =>
    get<import('@/types/news').PollItem[]>('/api/polls/'),

  /** Vote on a poll option */
  voteOnPoll: (pollId: number, optionId: number) =>
    post<{ success: boolean; total_votes: number }>(`/api/polls/${pollId}/vote`, { option_id: optionId }),
};
