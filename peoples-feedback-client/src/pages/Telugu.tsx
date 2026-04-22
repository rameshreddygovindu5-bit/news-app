/**
 * Telugu News Portal — /telugu
 * Designed like the Home page but with Telugu-specific content.
 */
import { useState, useEffect } from "react";
import { useQuery, useInfiniteQuery } from "@tanstack/react-query";
import { PremiumHeader } from "@/components/news/PremiumHeader";
import { PremiumFooter } from "@/components/news/PremiumFooter";
import { NewsLayout } from "@/components/news/NewsLayout";
import { BackToTop } from "@/components/news/BackToTop";
import SEO from "@/components/shared/SEO";
import { newsApi } from "@/lib/api";
import { useDebounce } from "@/hooks/useDebounce";
import type { ArticleListResponse, NewsArticle } from "@/types/news";

export default function TeluguPage() {
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const debouncedSearch = useDebounce(search, 500);

  // Reset to page 1 when search changes
  useEffect(() => { setPage(1); }, [debouncedSearch]);

  const {
    data,
    isLoading,
  } = useQuery<ArticleListResponse>({
    queryKey: ["telugu-articles", debouncedSearch, page],
    queryFn: () => {
      // Calculate date 30 days ago
      const thirtyDaysAgo = new Date();
      thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
      const dateFrom = thirtyDaysAgo.toISOString().split('T')[0]; 

      return newsApi.getTeluguArticles({ 
        page, 
        page_size: 24, // Use a standard grid size for pagination
        keyword: debouncedSearch || undefined,
        date_from: dateFrom
      });
    },
    staleTime: 60 * 1000,
    refetchInterval: 60 * 1000,
  });

  const articles = data?.articles ?? [];
  const totalPages = data?.total_pages ?? 1;


  return (
    <div className="min-h-screen bg-tricolor-light text-zinc-900">
      <SEO
        title="తెలుగు వార్తలు - పీపుల్స్ ఫీడ్‌బ్యాక్ | Peoples Feedback"
        description="India's authoritative Telugu news portal. నిజాయితీతో కూడిన వార్తలు, లోతైన విశ్లేషణలు."
        url="/telugu"
      />
      
      {/* Subtle Indian flag background blobs */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none" aria-hidden>
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-[var(--pf-saffron)]/10 rounded-full blur-3xl" />
        <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-[var(--pf-green)]/10 rounded-full blur-3xl" />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-[var(--pf-navy)]/5 rounded-full blur-3xl" />
      </div>

      <PremiumHeader
        selectedCategory="తెలుగు వార్తలు"
        onCategoryChange={() => {}}
        searchQuery={search}
        onSearchChange={setSearch}
      />

      <main className="w-full mx-auto px-2 md:px-4 py-8 min-h-[60vh] relative z-10">
        <NewsLayout
          articles={articles}
          isLoading={isLoading}
          selectedCategory="తెలుగు వార్తలు"
          lang="te"
          linkPrefix="telugu"
          onPageChange={setPage}
          currentPage={page}
          totalPages={totalPages}
        />
      </main>

      <PremiumFooter />
      <BackToTop />
    </div>
  );
}
