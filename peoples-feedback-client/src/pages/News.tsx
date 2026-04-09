import { useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { useLocation } from "wouter";
import { TooltipProvider } from "@/components/ui/tooltip";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { RefreshCw, AlertCircle, ChevronLeft, ChevronRight } from "lucide-react";
import { PremiumHeader } from "@/components/news/PremiumHeader";
import { PremiumFooter } from "@/components/news/PremiumFooter";
import { NewsLayout } from "@/components/news/NewsLayout";
import { newsApi } from "@/lib/api";
import { useDebounce } from "@/hooks/useDebounce";
import type { ArticleListResponse } from "@/types/news";

export default function NewsPage() {
  const [location] = useLocation();

  const getParams = () => {
    const p = new URLSearchParams(window.location.search);
    return {
      category: p.get("category") || "All",
      search: p.get("search") || "",
      page: parseInt(p.get("page") || "1"),
    };
  };

  const init = getParams();
  const [cat, setCat] = useState(init.category);
  const [search, setSearch] = useState(init.search);
  const [page, setPage] = useState(init.page);
  const [sort, setSort] = useState("newest");
  const debouncedSearch = useDebounce(search, 500);

  // Sync URL → state on back/forward navigation
  useEffect(() => {
    const p = getParams();
    if (p.category !== cat) setCat(p.category);
    if (p.search !== search) setSearch(p.search);
    if (p.page !== page) setPage(p.page);
  }, [location]);

  // Sync state → URL
  useEffect(() => {
    const p = new URLSearchParams();
    if (cat && cat !== "All") p.set("category", cat);
    if (debouncedSearch) p.set("search", debouncedSearch);
    if (page > 1) p.set("page", String(page));
    const url = p.toString() ? `/news?${p}` : "/news";
    if (window.location.pathname + window.location.search !== url) {
      window.history.replaceState({}, "", url);
    }
  }, [cat, debouncedSearch, page]);

  const { data, isLoading, error, refetch } = useQuery<ArticleListResponse>({
    queryKey: ["news", cat, debouncedSearch, page, sort],
    queryFn: () => newsApi.getArticles({
      page, page_size: 20,
      category: cat === "All" ? undefined : cat,
      keyword: debouncedSearch || undefined,
    }),
  });

  return (
    <div className="min-h-screen bg-white text-zinc-900">
      <TooltipProvider>
        <PremiumHeader
          selectedCategory={cat}
          onCategoryChange={c => { setCat(c); setPage(1); }}
          searchQuery={search}
          onSearchChange={setSearch}
        />

        <main className="w-full mx-auto px-2 md:px-4 py-6 min-h-[60vh]">
          <div className="max-w-7xl mx-auto mb-6 flex items-center justify-between border-b border-zinc-100 pb-3">
            <h2 className="text-2xl md:text-3xl font-[900] text-zinc-900 uppercase tracking-tight">
              {cat === "All" ? "Latest Headlines" : `${cat} News`}
            </h2>
            <div className="flex items-center gap-3">
              <Select value={sort} onValueChange={setSort}>
                <SelectTrigger className="w-[120px] rounded-none border-zinc-200 text-xs">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="newest">Newest</SelectItem>
                  <SelectItem value="popular">Popular</SelectItem>
                </SelectContent>
              </Select>
              <Button variant="ghost" size="icon" onClick={() => refetch()} className={isLoading ? "animate-spin" : ""}>
                <RefreshCw className="h-4 w-4" />
              </Button>
            </div>
          </div>

          {error ? (
            <div className="p-8 bg-red-50 text-red-600 rounded-sm flex flex-col items-center gap-4 text-center border border-red-100">
              <AlertCircle className="w-6 h-6" />
              <span className="font-bold">Failed to load news.</span>
              <Button variant="outline" onClick={() => refetch()} className="border-red-200 text-red-600">
                Try Again
              </Button>
            </div>
          ) : (
            <>
              <NewsLayout
                articles={data?.articles || []}
                isLoading={isLoading}
                selectedCategory={cat}
              />

              {!isLoading && data && data.total_pages > 1 && (
                <div className="flex items-center justify-center gap-6 mt-14 pt-6 border-t border-zinc-100">
                  <Button variant="outline" disabled={page <= 1}
                    onClick={() => { setPage(p => p - 1); window.scrollTo({ top: 0, behavior: "smooth" }); }}
                    className="w-28 font-bold rounded-none">
                    <ChevronLeft className="w-4 h-4 mr-1" /> Prev
                  </Button>
                  <span className="font-black text-sm text-zinc-400">
                    PAGE {page} / {data.total_pages}
                  </span>
                  <Button variant="outline" disabled={page >= data.total_pages}
                    onClick={() => { setPage(p => p + 1); window.scrollTo({ top: 0, behavior: "smooth" }); }}
                    className="w-28 font-bold rounded-none">
                    Next <ChevronRight className="w-4 h-4 ml-1" />
                  </Button>
                </div>
              )}
            </>
          )}
        </main>

        <PremiumFooter />
      </TooltipProvider>
    </div>
  );
}
