/**
 * Telugu News Page — /telugu
 * Shows articles that have telugu_title + telugu_content set.
 * All content displayed in Telugu script (native DB content — no Google Translate).
 * FIXED: Removed window.location.reload() useEffect that caused infinite reload loop.
 */
import { useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "wouter";
import { Clock, Search, ArrowRight, Newspaper, ChevronLeft, ChevronRight } from "lucide-react";
import { PremiumHeader } from "@/components/news/PremiumHeader";
import { PremiumFooter } from "@/components/news/PremiumFooter";
import { BackToTop } from "@/components/news/BackToTop";
import { newsApi } from "@/lib/api";
import type { ArticleListResponse, NewsArticle } from "@/types/news";
import { getImage, categoryPlaceholder } from "@/types/news";
import { useDebounce } from "@/hooks/useDebounce";

const handleImgError = (e: React.SyntheticEvent<HTMLImageElement>) => {
  const el = e.currentTarget;
  if (!el.dataset.fallback) { el.dataset.fallback = "1"; el.src = categoryPlaceholder(el.dataset.category); }
};

const timeAgo = (d?: string) => {
  if (!d) return "ఇప్పుడే";
  try {
    const mins = Math.floor((Date.now() - new Date(d).getTime()) / 60000);
    if (mins < 1)    return "ఇప్పుడే";
    if (mins < 60)   return `${mins} నిమిషాల క్రితం`;
    if (mins < 1440) return `${Math.floor(mins / 60)} గంటల క్రితం`;
    return `${Math.floor(mins / 1440)} రోజుల క్రితం`;
  } catch { return ""; }
};

function TeluguCard({ article }: { article: NewsArticle }) {
  const [imgError, setImgError] = useState(false);
  const title   = article.telugu_title || article.rephrased_title || article.original_title;
  const content = article.telugu_content || article.rephrased_content || article.original_content || "";
  const summary = content.replace(/<[^>]*>/g, "").replace(/&nbsp;/g, " ").trim().slice(0, 180);
  const imgUrl  = getImage(article);

  return (
    <Link href={`/telugu/${article.slug || article.id}`}>
      <div className="group cursor-pointer bg-white rounded-2xl border border-gray-100 overflow-hidden hover:shadow-2xl hover:-translate-y-1 transition-all duration-300 h-full flex flex-col card-shadow">
        {/* Image Container */}
        <div className="aspect-video relative overflow-hidden bg-gray-100 flex items-center justify-center">
          {!imgError ? (
            <>
              <img 
                src={imgUrl} 
                alt=""
                className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500 relative z-10"
                onError={() => setImgError(true)} 
              />
              <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-black/20 to-transparent z-20" />
            </>
          ) : (
            <div className="absolute inset-0 bg-gradient-to-br from-gray-100 to-gray-200 flex items-center justify-center">
              <div className="flex flex-col items-center gap-2 opacity-40">
                <Newspaper className="w-12 h-12 text-gray-400" />
                <span className="text-[10px] font-bold uppercase tracking-widest text-gray-400">{article.category || 'NEWS'}</span>
              </div>
              <div className="absolute inset-0 bg-gradient-to-t from-black/20 to-transparent z-20" />
            </div>
          )}
          
          {article.category && (
            <span className="absolute top-3 left-3 bg-gradient-to-r from-orange-500 to-orange-400 text-white px-3 py-1 text-[10px] font-bold rounded-full telugu shadow-lg z-30">
              {article.category}
            </span>
          )}
          {/* Telugu indicator */}
          <span className="absolute top-3 right-3 bg-[var(--pf-navy)] text-white px-2 py-0.5 text-[9px] font-black rounded-full tracking-wide z-30">
            తె
          </span>
        </div>

        {/* Content */}
        <div className="p-4 flex flex-col flex-1">
          <h3 className="font-bold text-[15px] leading-snug text-gray-900 group-hover:text-orange-600 transition-colors mb-2 telugu line-clamp-2">
            {title}
          </h3>
          {summary && (
            <p className="text-gray-500 text-sm leading-relaxed line-clamp-3 telugu flex-1 mb-3">
              {summary}…
            </p>
          )}
          <div className="flex items-center justify-between pt-3 border-t border-gray-50">
            <span className="flex items-center gap-1.5 text-xs text-gray-400 telugu">
              <Clock className="w-3.5 h-3.5 shrink-0" />
              {timeAgo(article.published_at)}
            </span>
            <span className="flex items-center gap-1 text-xs font-bold text-orange-600 group-hover:gap-2 transition-all telugu">
              చదవండి <ArrowRight className="w-3.5 h-3.5" />
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
      <div className="aspect-video skeleton" />
      <div className="p-4 space-y-3">
        <div className="skeleton h-4 w-full rounded" />
        <div className="skeleton h-4 w-5/6 rounded" />
        <div className="skeleton h-3 w-4/5 rounded" />
        <div className="skeleton h-3 w-3/5 rounded" />
      </div>
    </div>
  );
}

export default function TeluguPage() {
  const [page, setPage]     = useState(1);
  const [search, setSearch] = useState("");
  const debouncedSearch     = useDebounce(search, 500);

  // Set title and scroll on mount — NO Google Translate reload
  useEffect(() => {
    window.scrollTo({ top: 0, behavior: "smooth" });
    document.title = "తెలుగు వార్తలు — Peoples Feedback";
    return () => { document.title = "Peoples Feedback"; };
  }, []);

  const { data, isLoading } = useQuery<ArticleListResponse>({
    queryKey: ["telugu-articles", page, debouncedSearch],
    queryFn: () => newsApi.getTeluguArticles({ page, page_size: 24, keyword: debouncedSearch || undefined }),
    staleTime: 2 * 60 * 1000,
  });

  const changePage = (n: number) => {
    setPage(n);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <PremiumHeader selectedCategory="Telugu" onCategoryChange={() => {}} searchQuery="" onSearchChange={() => {}} />

      {/* Hero banner */}
      <div className="bg-gradient-to-br from-[var(--pf-navy)] via-[#1a237e] to-[#0d1575] text-white py-12 px-4 relative overflow-hidden">
        {/* Decorative blobs */}
        <div className="absolute top-0 right-0 w-64 h-64 bg-[var(--pf-saffron)]/10 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute bottom-0 left-0 w-48 h-48 bg-[var(--pf-green)]/10 rounded-full blur-3xl pointer-events-none" />

        <div className="max-w-5xl mx-auto text-center relative z-10">
          <div className="tricolor-stripe mb-6 rounded-full" />
          <div className="flex items-center justify-center gap-3 mb-4">
            <span className="text-5xl">🇮🇳</span>
            <h1 className="text-4xl md:text-6xl font-black telugu drop-shadow-lg">
              తెలుగు వార్తలు
            </h1>
          </div>
          <p className="text-white/80 text-base telugu mb-8">
            అన్ని తాజా వార్తలు తెలుగులో చదవండి · ఆంధ్రప్రదేశ్ · తెలంగాణ · జాతీయ
          </p>

          {/* Search */}
          <div className="max-w-xl mx-auto relative">
            <input
              className="w-full px-5 py-4 rounded-2xl text-gray-900 text-base outline-none shadow-2xl telugu placeholder-gray-400 border-2 border-white/20 focus:border-[var(--pf-saffron)] transition-colors"
              placeholder="తెలుగు వార్తలు వెతకండి..."
              value={search}
              onChange={e => { setSearch(e.target.value); setPage(1); }}
            />
            <Search className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 w-5 h-5 pointer-events-none" />
          </div>
        </div>
      </div>

      <main className="max-w-7xl mx-auto px-4 py-10">
        {/* Header row */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between mb-8 border-b-2 border-gray-200 pb-4 gap-3">
          <div>
            <h2 className="text-2xl font-black text-gray-900 telugu">తాజా తెలుగు వార్తలు</h2>
            {data && (
              <p className="text-sm text-gray-500 mt-1">
                మొత్తం <strong>{data.total}</strong> వార్తలు
                {debouncedSearch && ` · "${debouncedSearch}" కోసం ఫలితాలు`}
              </p>
            )}
          </div>

          {/* Pagination controls at top */}
          {data && data.total_pages > 1 && (
            <div className="flex items-center gap-2 shrink-0">
              <button disabled={page <= 1} onClick={() => changePage(page - 1)}
                className="flex items-center gap-1 px-3 py-2 bg-white border border-gray-200 rounded-lg text-sm font-medium disabled:opacity-40 hover:border-[var(--pf-saffron)] hover:text-[var(--pf-saffron)] transition-colors">
                <ChevronLeft className="w-4 h-4" /> వెనక
              </button>
              <span className="text-sm font-bold text-gray-600 px-2">{page} / {data.total_pages}</span>
              <button disabled={page >= data.total_pages} onClick={() => changePage(page + 1)}
                className="flex items-center gap-1 px-3 py-2 bg-white border border-gray-200 rounded-lg text-sm font-medium disabled:opacity-40 hover:border-[var(--pf-saffron)] hover:text-[var(--pf-saffron)] transition-colors">
                ముందు <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          )}
        </div>

        {/* Article grid */}
        {isLoading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {Array.from({ length: 12 }).map((_, i) => <SkeletonCard key={i} />)}
          </div>
        ) : !data?.articles?.length ? (
          <div className="text-center py-24 text-gray-400">
            <Newspaper className="w-16 h-16 mx-auto mb-4 opacity-30" />
            <p className="text-xl telugu mb-2">తెలుగు వార్తలు అందుబాటులో లేవు</p>
            <p className="text-sm text-gray-400">
              {debouncedSearch ? `"${debouncedSearch}" కోసం ఫలితాలు కనుగొనబడలేదు` : "కొంత సేపు తర్వాత మళ్ళీ చూడండి"}
            </p>
            {debouncedSearch && (
              <button onClick={() => { setSearch(""); setPage(1); }}
                className="mt-4 px-5 py-2 bg-[var(--pf-saffron)] text-white font-bold rounded-full text-sm hover:bg-[var(--pf-orange)] transition-colors">
                శోధన క్లియర్ చేయండి
              </button>
            )}
          </div>
        ) : (
          <>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
              {data.articles.map(a => <TeluguCard key={a.id} article={a} />)}
            </div>

            {/* Bottom pagination */}
            {data.total_pages > 1 && (
              <div className="flex items-center justify-center gap-4 mt-12 pt-6 border-t border-gray-100">
                <button disabled={page <= 1} onClick={() => changePage(page - 1)}
                  className="flex items-center gap-2 px-5 py-2.5 border-2 border-gray-200 rounded-lg font-bold text-sm disabled:opacity-40 hover:border-[var(--pf-saffron)] hover:text-[var(--pf-saffron)] transition-all">
                  <ChevronLeft className="w-4 h-4" /> వెనక
                </button>
                <span className="font-black text-sm text-gray-400 tracking-wider">{page} / {data.total_pages}</span>
                <button disabled={page >= data.total_pages} onClick={() => changePage(page + 1)}
                  className="flex items-center gap-2 px-5 py-2.5 border-2 border-gray-200 rounded-lg font-bold text-sm disabled:opacity-40 hover:border-[var(--pf-saffron)] hover:text-[var(--pf-saffron)] transition-all">
                  ముందు <ChevronRight className="w-4 h-4" />
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
