/**
 * Home page — Top news + category browse.
 * FIX: Load More correctly accumulates articles across pages using useInfiniteQuery
 *      instead of replacing them with a new page.
 */
import { useState, useCallback } from "react";
import { useInfiniteQuery } from "@tanstack/react-query";
import { PremiumHeader } from "@/components/news/PremiumHeader";
import { PremiumFooter } from "@/components/news/PremiumFooter";
import { NewsLayout } from "@/components/news/NewsLayout";
import { BackToTop } from "@/components/news/BackToTop";
import { newsApi } from "@/lib/api";
import { useDebounce } from "@/hooks/useDebounce";
import type { ArticleListResponse, NewsArticle } from "@/types/news";

export default function Home() {
  const [search, setSearch] = useState("");
  const [cat, setCat]       = useState("All");
  const debouncedSearch     = useDebounce(search, 500);

  // ── Infinite query — accumulates articles correctly ──────────────────
  const {
    data,
    isLoading,
    isFetchingNextPage,
    fetchNextPage,
    hasNextPage,
  } = useInfiniteQuery<ArticleListResponse>({
    queryKey: ["home-articles", cat, debouncedSearch],
    initialPageParam: 1,
    queryFn: ({ pageParam = 1 }) =>
      newsApi.getArticles({
        page:      pageParam as number,
        page_size: 50,
        category:  cat === "All" ? undefined : cat,
        keyword:   debouncedSearch || undefined,
      }),
    getNextPageParam: (last) =>
      last.page < last.total_pages ? last.page + 1 : undefined,
    staleTime: 2 * 60 * 1000,
  });

  // Flatten all pages into one article array
  const articles: NewsArticle[] = data?.pages.flatMap(p => p.articles) ?? [];

  const handleCategoryChange = useCallback((c: string) => {
    setCat(c);
  }, []);

  return (
    <div className="min-h-screen bg-tricolor-light text-zinc-900">
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
          hasMore={!!hasNextPage}
          onLoadMore={fetchNextPage}
          isLoadingMore={isFetchingNextPage}
        />
      </main>

      <PremiumFooter />
      <BackToTop />
    </div>
  );
}
