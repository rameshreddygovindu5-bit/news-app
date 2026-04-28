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
    search:   p.get("search")   || "",
    page:     parseInt(p.get("page") || "1", 10),
    sort:     p.get("sort")     || "newest",
  };
}

export default function MarketNewsPage() {
  const [location] = useLocation();
  const init = getUrlParams();

  const [search, setSearch] = useState(init.search);
  const [page,   setPage]   = useState(init.page);
  const [sort,   setSort]   = useState(init.sort);

  const debouncedSearch = useDebounce(search, 500);

  useEffect(() => {
    const p = getUrlParams();
    if (p.search   !== search) setSearch(p.search);
    if (p.page     !== page)   setPage(p.page);
    if (p.sort     !== sort)   setSort(p.sort);
  }, [location]);

  // Sync state -> URL
  useEffect(() => {
    const p = new URLSearchParams();
    if (debouncedSearch)       p.set("search", debouncedSearch);
    if (page > 1)              p.set("page", String(page));
    if (sort !== "newest")     p.set("sort", sort);
    const url = p.toString() ? `/market-news?${p}` : "/market-news";
    if (window.location.pathname + window.location.search !== url) {
      window.history.replaceState({}, "", url);
    }
  }, [debouncedSearch, page, sort]);

  const { data, isLoading, error, refetch } = useQuery<ArticleListResponse>({
    queryKey: ["market-news", debouncedSearch, page, sort],
    queryFn: () => newsApi.getArticles({
      page,
      page_size: 50,
      flags: 'A,Y',
      source_id: 18, // FINVIZ
      keyword:   debouncedSearch || undefined,
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
        title="Market News | Finviz Analysis"
        description="Latest market news and financial analysis from Finviz."
        url="/market-news"
      />
      <PremiumHeader
        selectedCategory="Market News"
        searchQuery={search}
        onSearchChange={v => { setSearch(v); setPage(1); }}
      />

      <main className="w-full mx-auto px-2 md:px-4 py-6 min-h-[60vh]">
        <div className="max-w-7xl mx-auto mb-6 flex items-center justify-between border-b-2 border-zinc-100 pb-4">
          <div>
            <h2 className="text-2xl md:text-3xl font-black text-zinc-900 uppercase tracking-tight">
              Market News
            </h2>
            {data && (
              <p className="text-xs text-zinc-400 mt-1">
                {data.total.toLocaleString()} financial insights · Page {page} of {data.total_pages}
              </p>
            )}
          </div>
          <div className="flex items-center gap-3">
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
            >
              <RefreshCw className="h-4 w-4" />
            </button>
          </div>
        </div>

        {error ? (
          <div className="p-10 bg-red-50 text-red-600 rounded-xl flex flex-col items-center gap-4 text-center border border-red-100">
            <AlertCircle className="w-8 h-8" />
            <p className="font-bold text-lg">Failed to load market news</p>
            <button
              onClick={() => refetch()}
              className="px-6 py-2.5 border-2 border-red-200 rounded-lg text-red-600 font-bold text-sm"
            >
              Try Again
            </button>
          </div>
        ) : (
          <>
            <NewsLayout
              articles={data?.articles || []}
              isLoading={isLoading}
              selectedCategory="Market News"
            />

            {!isLoading && data && data.total_pages > 1 && (
              <div className="flex items-center justify-center gap-4 mt-14 pt-6 border-t border-zinc-100">
                <button
                  disabled={page <= 1}
                  onClick={() => changePage(page - 1)}
                  className="flex items-center gap-2 px-5 py-2.5 border-2 border-zinc-200 rounded-lg font-bold text-sm disabled:opacity-40"
                >
                  <ChevronLeft className="w-4 h-4" /> Prev
                </button>
                <span className="font-black text-sm text-zinc-400 tracking-wider">
                  {page} / {data.total_pages}
                </span>
                <button
                  disabled={page >= data.total_pages}
                  onClick={() => changePage(page + 1)}
                  className="flex items-center gap-2 px-5 py-2.5 border-2 border-zinc-200 rounded-lg font-bold text-sm disabled:opacity-40"
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
