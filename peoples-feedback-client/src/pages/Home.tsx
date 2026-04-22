/**
 * Home page — Top news + category browse.
 * FIX: Load More correctly accumulates articles across pages using useInfiniteQuery
 *      instead of replacing them with a new page.
 */
import { useState, useCallback, useEffect, useRef } from "react";
import { useInfiniteQuery, useQuery } from "@tanstack/react-query";
import { PremiumHeader } from "@/components/news/PremiumHeader";
import { PremiumFooter } from "@/components/news/PremiumFooter";
import { NewsLayout } from "@/components/news/NewsLayout";
import { BackToTop } from "@/components/news/BackToTop";
import SEO from "@/components/shared/SEO";
import { newsApi } from "@/lib/api";
import { useDebounce } from "@/hooks/useDebounce";
import type { ArticleListResponse, NewsArticle } from "@/types/news";

export default function Home() {
  const [search, setSearch] = useState("");
  const [cat, setCat]       = useState("Home");  // "Home" = show all (no category filter)
  const debouncedSearch     = useDebounce(search, 500);

  // ── Infinite query — accumulates articles correctly ──────────────────
  const isHomeFeed = cat === "All" || cat === "Home";

  // ── Home / Top-news feed ─────────────────────────────────────────
  const {
    data: topData,
    isLoading: topLoading,
    refetch: refetchTop,
  } = useQuery<NewsArticle[]>({
    queryKey: ["top-news", cat],
    queryFn: () => newsApi.getTopNews(200),
    enabled: isHomeFeed,
    staleTime: 60 * 1000,          // 1 min
    refetchInterval: 20 * 1000,    // auto-refresh every 20s for near-realtime updates
    retry: 3,
  });

  // ── Category / search feed ───────────────────────────────────────
  const {
    data: catData,
    isLoading: catLoading,
    isFetchingNextPage,
    fetchNextPage,
    hasNextPage,
  } = useInfiniteQuery<ArticleListResponse>({
    queryKey: ["cat-articles", cat, debouncedSearch],
    initialPageParam: 1,
    queryFn: ({ pageParam = 1 }) => newsApi.getArticles({
      page:      pageParam as number,
      page_size: 50,
      category:  isHomeFeed ? undefined : cat,
      keyword:   debouncedSearch || undefined,
      flags:     "A,Y",
    }),
    getNextPageParam: (last) => last.page < last.total_pages ? last.page + 1 : undefined,
    enabled: !isHomeFeed || !!debouncedSearch,
    staleTime: 60 * 1000,
    refetchInterval: 20 * 1000,  // 20s refresh
    retry: 3,
  });

  const isLoading = isHomeFeed ? topLoading : catLoading;

  // Derive article list — home uses topData, else category pages
  const articles: NewsArticle[] = isHomeFeed && !debouncedSearch
    ? (Array.isArray(topData) ? topData : [])
    : (catData?.pages.flatMap(p => p.articles) ?? []);

  // Auto-refetch more aggressively when there are 0 articles (pipeline still running)
  const noArticles = !isLoading && articles.length === 0;
  const refetchTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  useEffect(() => {
    if (noArticles) {
      refetchTimerRef.current = setInterval(() => {
        refetchTop();
      }, 10 * 1000); // retry every 10s when empty
    } else {
      if (refetchTimerRef.current) clearInterval(refetchTimerRef.current);
    }
    return () => { if (refetchTimerRef.current) clearInterval(refetchTimerRef.current); };
  }, [noArticles, refetchTop]);

  const handleCategoryChange = useCallback((c: string) => {
    setCat(c);
  }, []);
  
  return (
    <div className="min-h-screen bg-tricolor-light text-zinc-900">
      <SEO 
        title={(cat === "All" || cat === "Home") ? "Latest News" : `${cat} News`}
        description="Stay updated with the latest news, in-depth reports, and community perspectives on Peoples Feedback. Your voice, your news."
        url={(cat === "All" || cat === "Home") ? "/" : `/news?category=${cat}`}
      />
      {/* Subtle Indian flag background blobs */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none" aria-hidden>
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-[var(--pf-saffron)]/10 rounded-full blur-3xl" />
        <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-[var(--pf-green)]/10 rounded-full blur-3xl" />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-[var(--pf-navy)]/5 rounded-full blur-3xl" />
      </div>

      <PremiumHeader
        selectedCategory={cat}
        onCategoryChange={handleCategoryChange}
        searchQuery={search}
        onSearchChange={setSearch}
      />

      <main className="w-full mx-auto px-2 md:px-4 py-8 min-h-[60vh] relative z-10">
        <NewsLayout
          articles={articles}
          isLoading={isLoading}
          selectedCategory={cat}
          hasMore={isHomeFeed ? false : !!hasNextPage}
          onLoadMore={isHomeFeed ? undefined : fetchNextPage}
          isLoadingMore={isFetchingNextPage}
        />
      </main>

      <PremiumFooter />
      <BackToTop />
    </div>
  );
}
