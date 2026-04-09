import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
// import { TooltipProvider } from "@/components/ui/tooltip";
import { PremiumHeader } from "@/components/news/PremiumHeader";
import { PremiumFooter } from "@/components/news/PremiumFooter";
import { NewsLayout } from "@/components/news/NewsLayout";
import { newsApi } from "@/lib/api";
import { useDebounce } from "@/hooks/useDebounce";
import type { ArticleListResponse } from "@/types/news";

export default function Home() {
  const [search, setSearch] = useState("");
  const [cat, setCat] = useState("All");
  const [page, setPage] = useState(1);
  const debouncedSearch = useDebounce(search, 500);

  const { data, isLoading } = useQuery<ArticleListResponse>({
    queryKey: ["articles", cat, debouncedSearch, page],
    queryFn: () => newsApi.getArticles({
      page, page_size: 30,
      category: cat === "All" ? undefined : cat,
      keyword: debouncedSearch || undefined,
    }),
  });

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 via-white to-gray-100 text-zinc-900 relative">
      {/* Background decoration */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-gradient-to-br from-[var(--pf-orange)]/20 to-[var(--pf-pink)]/20 rounded-full blur-3xl"></div>
        <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-gradient-to-br from-[var(--pf-blue)]/20 to-[var(--pf-purple)]/20 rounded-full blur-3xl"></div>
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-gradient-to-br from-[var(--pf-green)]/10 to-[var(--pf-teal)]/10 rounded-full blur-3xl"></div>
      </div>
      
      <PremiumHeader
          selectedCategory={cat}
          onCategoryChange={c => { setCat(c); setPage(1); }}
          searchQuery={search}
          onSearchChange={setSearch}
        />
        <main className="w-full mx-auto px-2 md:px-4 py-8 min-h-[60vh] relative z-10">
          <NewsLayout
            articles={data?.articles || []}
            isLoading={isLoading}
            selectedCategory={cat}
            hasMore={(data?.total_pages || 1) > page}
            onLoadMore={() => setPage(p => p + 1)}
          />
        </main>
        <PremiumFooter />
    </div>
  );
}
