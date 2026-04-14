/**
 * Telugu News Page — /telugu
 * Shows only articles that have telugu_title + telugu_content set.
 * All content displayed in Telugu script.
 */
import { useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "wouter";
import { Clock, Search, ArrowRight, Newspaper } from "lucide-react";
import { PremiumHeader } from "@/components/news/PremiumHeader";
import { PremiumFooter } from "@/components/news/PremiumFooter";
import { newsApi } from "@/lib/api";
import { BackToTop } from "@/components/news/BackToTop";
import type { ArticleListResponse, NewsArticle } from "@/types/news";
import { getImage, categoryPlaceholder, getSummary } from "@/types/news";
import { useDebounce } from "@/hooks/useDebounce";

const handleImgError = (e: React.SyntheticEvent<HTMLImageElement>) => {
  const el = e.currentTarget;
  if (!el.dataset.fallback) { el.dataset.fallback = "1"; el.src = categoryPlaceholder(el.dataset.category); }
};

const timeAgo = (d?: string) => {
  if (!d) return 'ఇప్పుడే';
  try {
    const mins = Math.floor((Date.now() - new Date(d).getTime()) / 60000);
    if (mins < 1) return 'ఇప్పుడే';
    if (mins < 60) return `${mins} నిమిషాల క్రితం`;
    if (mins < 1440) return `${Math.floor(mins/60)} గంటల క్రితం`;
    return `${Math.floor(mins/1440)} రోజుల క్రితం`;
  } catch { return ''; }
};

function TeluguCard({ article }: { article: NewsArticle }) {
  const title = article.telugu_title || article.rephrased_title || article.original_title;
  const content = article.telugu_content || article.rephrased_content || article.original_content || '';
  const summary = content.replace(/<[^>]*>/g,'').replace(/&nbsp;/g,' ').trim().slice(0,180);

  return (
    <Link href={`/telugu/${article.slug || article.id}`}>
      <div className="group cursor-pointer bg-white rounded-xl border border-gray-100 overflow-hidden hover:shadow-xl hover:-translate-y-1 transition-all duration-300 h-full flex flex-col">
        <div className="aspect-video relative overflow-hidden">
          <img src={getImage(article)} alt="" className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
            onError={handleImgError} data-category={article.category} />
          <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent" />
          {article.category && (
            <span className="absolute top-3 left-3 bg-gradient-to-r from-orange-500 to-orange-400 text-white px-3 py-1 text-[10px] font-bold rounded-full telugu">
              {article.category}
            </span>
          )}
        </div>
        <div className="p-5 flex flex-col flex-1">
          <h3 className="font-bold text-lg leading-snug text-gray-900 group-hover:text-orange-600 transition-colors mb-3 telugu line-clamp-2">
            {title}
          </h3>
          <p className="text-gray-600 text-sm leading-relaxed line-clamp-3 telugu flex-1">
            {summary}…
          </p>
          <div className="mt-4 pt-4 border-t border-gray-100 flex items-center justify-between">
            <span className="flex items-center gap-1.5 text-xs text-gray-400 telugu">
              <Clock className="w-3.5 h-3.5" />{timeAgo(article.published_at)}
            </span>
            <span className="flex items-center gap-1 text-xs font-bold text-orange-600 telugu">
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
    <div className="bg-white rounded-xl border border-gray-100 overflow-hidden">
      <div className="aspect-video skeleton" />
      <div className="p-5 space-y-3">
        <div className="skeleton h-5 w-full rounded" />
        <div className="skeleton h-4 w-4/5 rounded" />
        <div className="skeleton h-4 w-3/5 rounded" />
      </div>
    </div>
  );
}

export default function TeluguPage() {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebounce(search, 500);

  // Auto-switch Google Translate to Telugu for this page
  useEffect(() => {
    if (!document.cookie.includes('googtrans=/en/te')) {
      document.cookie = `googtrans=/en/te; path=/;`;
      window.location.reload(); // Force reload to apply translation now
    }
  }, []);

  const { data, isLoading } = useQuery<ArticleListResponse>({
    queryKey: ["telugu-articles", page, debouncedSearch],
    queryFn: () => newsApi.getTeluguArticles({ page, page_size: 24, keyword: debouncedSearch || undefined }),
    staleTime: 2 * 60 * 1000,
  });

  return (
    <div className="min-h-screen bg-gray-50">
      <PremiumHeader selectedCategory="Telugu" onCategoryChange={() => {}} searchQuery="" onSearchChange={() => {}} />

      {/* ── Telugu hero banner ── */}
      <div className="bg-gradient-to-r from-orange-600 via-orange-500 to-green-700 text-white py-10 px-4">
        <div className="max-w-5xl mx-auto text-center">
          <div className="tricolor-stripe mb-6 rounded" />
          <h1 className="text-4xl md:text-6xl font-black telugu mb-3 drop-shadow">
            తెలుగు వార్తలు
          </h1>
          <p className="text-white/90 text-lg telugu">
            అన్ని తాజా వార్తలు తెలుగులో చదవండి
          </p>
          <div className="mt-6 max-w-xl mx-auto relative">
            <input
              className="w-full px-5 py-3.5 rounded-full text-gray-900 text-base outline-none shadow-lg telugu placeholder-gray-400"
              placeholder="తెలుగు వార్తలు వెతకండి..."
              value={search}
              onChange={e => { setSearch(e.target.value); setPage(1); }}
            />
            <Search className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 w-5 h-5" />
          </div>
        </div>
      </div>

      <main className="max-w-7xl mx-auto px-4 py-10">
        {/* Header */}
        <div className="flex items-center justify-between mb-8 border-b-2 border-gray-200 pb-4">
          <div>
            <h2 className="text-2xl font-black text-gray-900 telugu">తాజా తెలుగు వార్తలు</h2>
            {data && <p className="text-sm text-gray-500 mt-1">మొత్తం {data.total} వార్తలు</p>}
          </div>
          {data && data.total_pages > 1 && (
            <div className="flex items-center gap-2">
              <button disabled={page<=1} onClick={()=>setPage(p=>p-1)}
                className="px-4 py-2 bg-white border border-gray-200 rounded-lg text-sm font-medium disabled:opacity-40 hover:bg-gray-50 transition-colors">
                ← వెనక
              </button>
              <span className="text-sm text-gray-600">{page} / {data.total_pages}</span>
              <button disabled={page>=data.total_pages} onClick={()=>setPage(p=>p+1)}
                className="px-4 py-2 bg-white border border-gray-200 rounded-lg text-sm font-medium disabled:opacity-40 hover:bg-gray-50 transition-colors">
                ముందు →
              </button>
            </div>
          )}
        </div>

        {isLoading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {Array.from({length:8}).map((_,i)=><SkeletonCard key={i}/>)}
          </div>
        ) : !data?.articles?.length ? (
          <div className="text-center py-24 text-gray-400">
            <Newspaper className="w-16 h-16 mx-auto mb-4 opacity-30" />
            <p className="text-xl telugu">తెలుగు వార్తలు అందుబాటులో లేవు</p>
            <p className="text-sm mt-2">కొంత సేపు తర్వాత మళ్ళీ చూడండి</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {data.articles.map(a => <TeluguCard key={a.id} article={a} />)}
          </div>
        )}
      </main>

      <PremiumFooter />
      <BackToTop />
    </div>
  );
}
