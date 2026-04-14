/**
 * API client — peoples-feedback-client
 * Synced with news-platform-final backend schema.
 * Public endpoints only. Always filters flag=A,Y.
 */
const BASE = (import.meta as any)?.env?.VITE_API_URL || '';

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

export const newsApi = {
  /** List published articles. Supports category, keyword, pagination. */
  getArticles: (p: { page?: number; page_size?: number; category?: string; keyword?: string; lang?: string }) =>
    get<import('@/types/news').ArticleListResponse>('/api/articles', { ...p, flags: 'A,Y' }),

  /** Top 100 ranked news (flag=Y) */
  getTopNews: (limit = 100) =>
    get<import('@/types/news').NewsArticle[]>('/api/articles/top-news', { limit }),

  /** Single article by id or slug */
  getArticle: (idOrSlug: number | string) =>
    get<import('@/types/news').NewsArticle>(`/api/articles/${idOrSlug}`),

  /** Articles by category — always published only */
  getByCategory: (cat: string, p?: { page?: number; page_size?: number }) =>
    get<import('@/types/news').CategoryArticlesResponse>(
      `/api/articles/by-category/${encodeURIComponent(cat)}`, p),

  /** Telugu-only articles (have telugu_title set) */
  getTeluguArticles: (p?: { page?: number; page_size?: number; keyword?: string }) =>
    get<import('@/types/news').ArticleListResponse>('/api/articles', {
      ...p, flags: 'A,Y', telugu_page: 'true',
    }),

  /** Categories from backend DB (dynamic) */
  getCategories: () =>
    get<import('@/types/news').CategoryResponse[]>('/api/categories'),
};
