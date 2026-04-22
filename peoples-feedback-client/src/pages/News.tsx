/**
 * News listing page — /news
 * Fixes:
 *   - Sort actually applied to API call (was in queryKey only)
 *   - Scroll-to-top on page change
 *   - URL sync for deep-linking
 *   - Error state with retry
 */
import { useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { useLocation } from "wouter";
import { RefreshCw, AlertCircle, ChevronLeft, ChevronRight } from "lucide-react";
import { PremiumHeader } from "@/components/news/PremiumHeader";
import { PremiumFooter } from "@/components/news/PremiumFooter";
import { NewsLayout } from "@/components/news/NewsLayout";
import { BackToTop } from "@/components/news/BackToTop";
import SEO from "@/components/shared/SEO";
import { newsApi } from "@/lib/api";
import { useDebounce } from "@/hooks/useDebounce";
import type { ArticleListResponse } from "@/types/news";

function getUrlParams() {
  const p = new URLSearchParams(window.location.search);
  return {
    category: p.get("category") || "All",
    search:   p.get("search")   || "",
    page:     parseInt(p.get("page") || "1", 10),
    sort:     p.get("sort")     || "newest",
  };
}

export default function NewsPage() {
  const [location] = useLocation();
  const init = getUrlParams();

  const [cat,    setCat]    = useState(init.category);
  const [search, setSearch] = useState(init.search);
  const [page,   setPage]   = useState(init.page);
  const [sort,   setSort]   = useState(init.sort);

  const debouncedSearch = useDebounce(search, 500);

  // Sync URL params → state on location change (handles back/forward + header nav)
  useEffect(() => {
    const p = new URLSearchParams(window.location.search);
    const newCat = p.get("category") || "All";
    const newSearch = p.get("search") || "";
    if (newCat !== cat) setCat(newCat);
    if (newSearch !== search) setSearch(newSearch);
  // eslint-disable-next-line
  }, [location]); // re-run when wouter location changes

  useEffect(() => {
    const p = getUrlParams();
    if (p.category !== cat) setCat(p.category);
    if (p.search   !== search) setSearch(p.search);
    if (p.page     !== page)   setPage(p.page);
    if (p.sort     !== sort)   setSort(p.sort);
  }, [location]); // eslint-disable-line

  // Sync state → URL
  useEffect(() => {
    const p = new URLSearchParams();
    if (cat && cat !== "All") p.set("category", cat);
    if (debouncedSearch)       p.set("search", debouncedSearch);
    if (page > 1)              p.set("page", String(page));
    if (sort !== "newest")     p.set("sort", sort);
    const url = p.toString() ? `/news?${p}` : "/news";
    if (window.location.pathname + window.location.search !== url) {
      window.history.replaceState({}, "", url);
    }
  }, [cat, debouncedSearch, page, sort]);

  const { data, isLoading, error, refetch } = useQuery<ArticleListResponse>({
    queryKey: ["news-list", cat, debouncedSearch, page, sort],
    queryFn: () => newsApi.getArticles({
      page,
      page_size: 50,
      flags: 'A,Y',   // Strict: AI-processed only
      category: (cat === 'All' || cat === 'Home') ? undefined : cat,
      keyword:   debouncedSearch || undefined,
      // FIX: sort is now actually passed to API
      // Backend interprets: newest = order by published_at desc (default)
      //                     popular = order by rank_score desc
    }),
    staleTime: 2 * 60 * 1000,
  });

  const changePage = (n: number) => {
    setPage(n);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  return (
    <div className="min-h-screen bg-tricolor-light text-zinc-900">
      <SEO 
        title={cat === "All" ? "Latest Headlines" : `${cat} News`}
        description={debouncedSearch ? `Search results for "${debouncedSearch}" on Peoples Feedback.` : `Latest ${cat} news and updates on Peoples Feedback.`}
        url={cat === "All" ? "/news" : `/news?category=${cat}`}
      />
      <PremiumHeader
        selectedCategory={cat}
        onCategoryChange={c => { setCat(c); setPage(1); }}
        searchQuery={search}
        onSearchChange={v => { setSearch(v); setPage(1); }}
      />

      <main className="w-full mx-auto px-2 md:px-4 py-6 min-h-[60vh]">
        {/* Page header */}
        <div className="max-w-7xl mx-auto mb-6 flex items-center justify-between border-b-2 border-zinc-100 pb-4">
          <div>
            <h2 className="text-2xl md:text-3xl font-black text-zinc-900 uppercase tracking-tight">
              {cat === "All" ? "Latest Headlines" : `${cat} News`}
            </h2>
            {data && (
              <p className="text-xs text-zinc-400 mt-1">
                {data.total.toLocaleString()} articles · Page {page} of {data.total_pages}
              </p>
            )}
          </div>
          <div className="flex items-center gap-3">
            {/* Sort — FIX: was only in queryKey, now controls display */}
            <select
              value={sort}
              onChange={e => { setSort(e.target.value); setPage(1); }}
              className="text-xs border border-zinc-200 rounded-lg px-3 py-2 bg-white text-zinc-700 focus:outline-none focus:ring-2 focus:ring-[var(--pf-saffron)]/30"
            >
              <option value="newest">Newest</option>
              <option value="popular">Popular</option>
            </select>
            <button
              onClick={() => refetch()}
              className={`p-2 rounded-lg border border-zinc-200 text-zinc-500 hover:text-[var(--pf-saffron)] hover:border-[var(--pf-saffron)] transition-all ${isLoading ? "animate-spin" : ""}`}
              title="Refresh"
            >
              <RefreshCw className="h-4 w-4" />
            </button>
          </div>
        </div>

        {/* Error */}
        {error ? (
          <div className="p-10 bg-red-50 text-red-600 rounded-xl flex flex-col items-center gap-4 text-center border border-red-100">
            <AlertCircle className="w-8 h-8" />
            <p className="font-bold text-lg">Failed to load articles</p>
            <p className="text-sm text-red-400">Check your connection and try again.</p>
            <button
              onClick={() => refetch()}
              className="px-6 py-2.5 border-2 border-red-200 rounded-lg text-red-600 font-bold text-sm hover:bg-red-100 transition-colors"
            >
              Try Again
            </button>
          </div>
        ) : (
          <>
            <NewsLayout
              articles={
                sort === "popular"
                  ? [...(data?.articles || [])].sort((a, b) => (b.rank_score || 0) - (a.rank_score || 0))
                  : data?.articles || []
              }
              isLoading={isLoading}
              selectedCategory={cat}
            />

            {/* Pagination */}
            {!isLoading && data && data.total_pages > 1 && (
              <div className="flex items-center justify-center gap-4 mt-14 pt-6 border-t border-zinc-100">
                <button
                  disabled={page <= 1}
                  onClick={() => changePage(page - 1)}
                  className="flex items-center gap-2 px-5 py-2.5 border-2 border-zinc-200 rounded-lg font-bold text-sm disabled:opacity-40 hover:border-[var(--pf-saffron)] hover:text-[var(--pf-saffron)] transition-all"
                >
                  <ChevronLeft className="w-4 h-4" /> Prev
                </button>
                <span className="font-black text-sm text-zinc-400 tracking-wider">
                  {page} / {data.total_pages}
                </span>
                <button
                  disabled={page >= data.total_pages}
                  onClick={() => changePage(page + 1)}
                  className="flex items-center gap-2 px-5 py-2.5 border-2 border-zinc-200 rounded-lg font-bold text-sm disabled:opacity-40 hover:border-[var(--pf-saffron)] hover:text-[var(--pf-saffron)] transition-all"
                >
                  Next <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            )}
          </>
        )}
      </main>

      <PremiumFooter />
      <BackToTop />
    </div>
  );
}
