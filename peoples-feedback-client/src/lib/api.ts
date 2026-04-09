/**
 * API client synced with backend news-platform-final.
 * Public client ALWAYS passes flags=A,Y to only show published articles.
 */
const BASE = (import.meta as any)?.env?.VITE_API_URL || '';

async function get<T>(path: string, params?: Record<string, any>): Promise<T> {
  const url = new URL(path, BASE || window.location.origin);
  if (params) Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== '') url.searchParams.set(k, String(v));
  });
  const res = await fetch(url.toString());
  if (!res.ok) throw new Error(`API ${res.status}: ${res.statusText}`);
  return res.json();
}

export const newsApi = {
  /** List published articles (flag A or Y only). Supports category, keyword, pagination. */
  getArticles: (p: {
    page?: number; page_size?: number; category?: string; keyword?: string;
  }) => get<import('@/types/news').ArticleListResponse>('/api/articles', {
    ...p,
    flags: 'A,Y',  // CRITICAL: only show published content to public
  }),

  /** Top 100 ranked news (flag=Y) */
  getTopNews: (limit = 100) =>
    get<import('@/types/news').NewsArticle[]>('/api/articles/top-news', { limit }),

  /** Single article by ID */
  getArticle: (id: number | string) =>
    get<import('@/types/news').NewsArticle>(`/api/articles/${id}`),

  /** Articles by specific category (backend already filters A,Y) */
  getByCategory: (cat: string, p?: { page?: number; page_size?: number }) =>
    get<import('@/types/news').CategoryArticlesResponse>(
      `/api/articles/by-category/${encodeURIComponent(cat)}`, p),

  /** Fetch categories from backend DB (dynamic, not hardcoded) */
  getCategories: () =>
    get<import('@/types/news').CategoryResponse[]>('/api/categories'),
};
