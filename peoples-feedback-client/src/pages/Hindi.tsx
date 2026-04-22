/**
 * Hindi News Page — /hindi
 * Shows articles sourced in Hindi (original_language=hi).
 * All content displayed in Hindi script.
 */
import { useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "wouter";
import { Clock, Search, ArrowRight, Newspaper, ChevronLeft, ChevronRight } from "lucide-react";
import { PremiumHeader } from "@/components/news/PremiumHeader";
import { PremiumFooter } from "@/components/news/PremiumFooter";
import { BackToTop } from "@/components/news/BackToTop";
import SEO from "@/components/shared/SEO";
import { newsApi } from "@/lib/api";
import type { ArticleListResponse, NewsArticle } from "@/types/news";
import { getImage, categoryPlaceholder, getSummary, getTitle } from "@/types/news";
import { useDebounce } from "@/hooks/useDebounce";

const handleImgError = (e: React.SyntheticEvent<HTMLImageElement>) => {
  const el = e.currentTarget;
  if (!el.dataset.fallback) { el.dataset.fallback = "1"; el.src = categoryPlaceholder(el.dataset.category); }
};

const timeAgoHindi = (d?: string) => {
  if (!d) return "अभी";
  try {
    const mins = Math.floor((Date.now() - new Date(d).getTime()) / 60000);
    if (mins < 1)    return "अभी";
    if (mins < 60)   return `${mins} मिनट पहले`;
    if (mins < 1440) return `${Math.floor(mins / 60)} घंटे पहले`;
    return `${Math.floor(mins / 1440)} दिन पहले`;
  } catch { return ""; }
};

function HindiCard({ article }: { article: NewsArticle }) {
  const [imgError, setImgError] = useState(false);
  // Hindi articles: use original content (original_language=hi)
  const title   = article.original_title || article.rephrased_title || "";
  const summary = (article.original_content || article.rephrased_content || "")
    .replace(/<[^>]*>/g, "").replace(/&nbsp;/g, " ").trim().slice(0, 180);
  const imgUrl  = imgError ? categoryPlaceholder(article.category) : getImage(article);

  return (
    <Link href={`/news/${article.slug || article.id}`}>
      <div className="group cursor-pointer bg-white rounded-2xl border border-gray-100 overflow-hidden hover:shadow-2xl hover:-translate-y-1 transition-all duration-300 h-full flex flex-col">
        <div className="aspect-video relative overflow-hidden bg-gray-100">
          <img
            src={imgUrl}
            alt=""
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
            onError={() => setImgError(true)}
            data-category={article.category}
          />
          <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent" />
          {article.category && (
            <span className="absolute top-3 left-3 bg-gradient-to-r from-orange-600 to-orange-500 text-white px-3 py-1 text-[10px] font-bold rounded-full shadow-lg z-10">
              {article.category}
            </span>
          )}
          <span className="absolute top-3 right-3 bg-[var(--pf-navy)] text-white px-2 py-0.5 text-[9px] font-black rounded-full tracking-wide z-10">
            हि
          </span>
        </div>
        <div className="p-4 flex flex-col flex-1">
          <h3 className="font-bold text-[15px] leading-snug text-gray-900 group-hover:text-orange-600 transition-colors mb-2 line-clamp-2">
            {title}
          </h3>
          {summary && (
            <p className="text-gray-500 text-sm leading-relaxed line-clamp-3 flex-1 mb-3">{summary}…</p>
          )}
          <div className="flex items-center justify-between pt-3 border-t border-gray-50">
            <span className="flex items-center gap-1.5 text-xs text-gray-400">
              <Clock className="w-3.5 h-3.5 shrink-0" />
              {timeAgoHindi(article.published_at)}
            </span>
            <span className="flex items-center gap-1 text-xs font-bold text-orange-600 group-hover:gap-2 transition-all">
              पढ़ें <ArrowRight className="w-3.5 h-3.5" />
            </span>
          </div>
        </div>
      </div>
    </Link>
  );
}

function SkeletonCard() {
  return (
    <div className="bg-white rounded-2xl border border-gray-100 overflow-hidden">
      <div className="aspect-video bg-gray-200 animate-pulse" />
      <div className="p-4 space-y-3">
        <div className="h-4 bg-gray-200 rounded animate-pulse w-full" />
        <div className="h-4 bg-gray-200 rounded animate-pulse w-5/6" />
        <div className="h-3 bg-gray-200 rounded animate-pulse w-4/5" />
      </div>
    </div>
  );
}

export default function HindiPage() {
  const [page, setPage]     = useState(1);
  const [search, setSearch] = useState("");
  const debouncedSearch     = useDebounce(search, 500);

  useEffect(() => {
    window.scrollTo({ top: 0, behavior: "smooth" });
  }, [page, debouncedSearch]);

  const { data, isLoading } = useQuery<ArticleListResponse>({
    queryKey: ["hindi-articles", page, debouncedSearch],
    queryFn: () => newsApi.getHindiArticles({ page, page_size: 24, keyword: debouncedSearch || undefined }),
    staleTime: 2 * 60 * 1000,
    refetchInterval: 15 * 60 * 1000,
  });

  const changePage = (n: number) => { setPage(n); window.scrollTo({ top: 0, behavior: "smooth" }); };

  return (
    <div className="min-h-screen bg-gray-50">
      <SEO
        title="हिंदी समाचार - ताज़ा खबरें"
        description="ताज़ा हिंदी समाचार: आज की मुख्य खबरें, राजनीति, खेल, मनोरंजन और अधिक। Peoples Feedback हिंदी न्यूज़ पोर्टल।"
        url="/hindi"
      />
      <PremiumHeader selectedCategory="Hindi" onCategoryChange={() => {}} searchQuery="" onSearchChange={() => {}} />

      {/* Hero banner */}
      <div className="bg-gradient-to-br from-orange-700 via-orange-600 to-orange-500 text-white py-12 px-4 relative overflow-hidden">
        <div className="absolute top-0 right-0 w-64 h-64 bg-white/10 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute bottom-0 left-0 w-48 h-48 bg-green-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="max-w-5xl mx-auto text-center relative z-10">
          <div className="flex items-center justify-center gap-3 mb-4">
            <span className="text-5xl">🇮🇳</span>
            <h1 className="text-4xl md:text-6xl font-black drop-shadow-lg">हिंदी समाचार</h1>
          </div>
          <p className="text-white/80 text-base mb-8">सभी ताज़ा खबरें हिंदी में पढ़ें · राजनीति · खेल · मनोरंजन · विश्व</p>
          <div className="max-w-xl mx-auto relative">
            <input
              className="w-full px-5 py-4 rounded-2xl text-gray-900 text-base outline-none shadow-2xl placeholder-gray-400 border-2 border-white/20 focus:border-white transition-colors"
              placeholder="हिंदी खबरें खोजें..."
              value={search}
              onChange={e => { setSearch(e.target.value); setPage(1); }}
            />
            <Search className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 w-5 h-5 pointer-events-none" />
          </div>
        </div>
      </div>

      <main className="max-w-7xl mx-auto px-4 py-10">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between mb-8 border-b-2 border-gray-200 pb-4 gap-3">
          <div>
            <h2 className="text-2xl font-black text-gray-900">ताज़ा हिंदी खबरें</h2>
            {data && (
              <p className="text-sm text-gray-500 mt-1">
                कुल <strong>{data.total}</strong> खबरें
                {debouncedSearch && ` · "${debouncedSearch}" के परिणाम`}
              </p>
            )}
          </div>
          {data && data.total_pages > 1 && (
            <div className="flex items-center gap-2 shrink-0">
              <button disabled={page <= 1} onClick={() => changePage(page - 1)}
                className="flex items-center gap-1 px-3 py-2 bg-white border border-gray-200 rounded-lg text-sm font-medium disabled:opacity-40 hover:border-orange-400 hover:text-orange-600 transition-colors">
                <ChevronLeft className="w-4 h-4" /> पिछला
              </button>
              <span className="text-sm font-bold text-gray-600 px-2">{page} / {data.total_pages}</span>
              <button disabled={page >= data.total_pages} onClick={() => changePage(page + 1)}
                className="flex items-center gap-1 px-3 py-2 bg-white border border-gray-200 rounded-lg text-sm font-medium disabled:opacity-40 hover:border-orange-400 hover:text-orange-600 transition-colors">
                अगला <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          )}
        </div>

        {isLoading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {Array.from({ length: 12 }).map((_, i) => <SkeletonCard key={i} />)}
          </div>
        ) : !data?.articles?.length ? (
          <div className="text-center py-24 text-gray-400">
            <Newspaper className="w-16 h-16 mx-auto mb-4 opacity-30" />
            <p className="text-xl mb-2">कोई हिंदी खबर उपलब्ध नहीं</p>
            <p className="text-sm text-gray-400">
              {debouncedSearch ? `"${debouncedSearch}" के लिए कोई परिणाम नहीं मिला` : "कुछ देर बाद फिर से देखें"}
            </p>
            {debouncedSearch && (
              <button onClick={() => { setSearch(""); setPage(1); }}
                className="mt-4 px-5 py-2 bg-orange-600 text-white font-bold rounded-full text-sm hover:bg-orange-700 transition-colors">
                खोज हटाएं
              </button>
            )}
          </div>
        ) : (
          <>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
              {data.articles.map(a => <HindiCard key={a.id} article={a} />)}
            </div>
            {data.total_pages > 1 && (
              <div className="flex items-center justify-center gap-4 mt-12 pt-6 border-t border-gray-100">
                <button disabled={page <= 1} onClick={() => changePage(page - 1)}
                  className="flex items-center gap-2 px-5 py-2.5 border-2 border-gray-200 rounded-lg font-bold text-sm disabled:opacity-40 hover:border-orange-400 hover:text-orange-600 transition-all">
                  <ChevronLeft className="w-4 h-4" /> पिछला
                </button>
                <span className="font-black text-sm text-gray-400 tracking-wider">{page} / {data.total_pages}</span>
                <button disabled={page >= data.total_pages} onClick={() => changePage(page + 1)}
                  className="flex items-center gap-2 px-5 py-2.5 border-2 border-gray-200 rounded-lg font-bold text-sm disabled:opacity-40 hover:border-orange-400 hover:text-orange-600 transition-all">
                  अगला <ChevronRight className="w-4 h-4" />
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
