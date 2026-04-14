/**
 * Telugu Article Detail Page — /telugu/:idOrSlug
 * Displays article in Telugu script with English toggle.
 */
import { useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { useRoute, Link } from "wouter";
import { Clock, ArrowLeft, ChevronRight } from "lucide-react";
import { motion, useScroll, useSpring } from "framer-motion";
import { PremiumHeader } from "@/components/news/PremiumHeader";
import { PremiumFooter } from "@/components/news/PremiumFooter";
import { ShareMenu, ShareBar } from "@/components/news/ShareMenu";
import { newsApi } from "@/lib/api";
import { BackToTop } from "@/components/news/BackToTop";
import type { NewsArticle } from "@/types/news";
import { getImage, categoryPlaceholder, hasTelugu } from "@/types/news";

const handleImgError = (e: React.SyntheticEvent<HTMLImageElement>) => {
  const el = e.currentTarget;
  if (!el.dataset.fallback) { el.dataset.fallback="1"; el.src=categoryPlaceholder(el.dataset.category); }
};

const fmtDate = (d?: string) => {
  if (!d) return "ఇటీవల";
  try {
    return new Intl.DateTimeFormat("te-IN", { day:"numeric",month:"long",year:"numeric" }).format(new Date(d));
  } catch { return "ఇటీవల"; }
};

export default function TeluguDetail() {
  const [,params] = useRoute("/telugu/:idOrSlug");
  const idOrSlug = params?.idOrSlug;
  const [lang, setLang] = useState<'te'|'en'>('te');

  const { scrollYProgress } = useScroll();
  const scaleX = useSpring(scrollYProgress, { stiffness:100, damping:30 });

  const { data: article, isLoading } = useQuery<NewsArticle>({
    queryKey: ["article", idOrSlug],
    queryFn: () => newsApi.getArticle(idOrSlug!),
    enabled: !!idOrSlug,
  });

  // Auto-switch Google Translate to Telugu for this page
  useEffect(() => {
    if (!document.cookie.includes('googtrans=/en/te')) {
      document.cookie = `googtrans=/en/te; path=/;`;
      window.location.reload();
    }
  }, []);

  if (isLoading) return (
    <div className="min-h-screen bg-white flex items-center justify-center">
      <div className="w-12 h-12 border-4 border-orange-500 border-t-transparent rounded-full animate-spin"/>
    </div>
  );
  if (!article) return (
    <div className="min-h-screen bg-white flex items-center justify-center">
      <div className="text-center"><p className="text-2xl telugu text-gray-600 mb-4">వార్త అందుబాటులో లేదు</p>
      <Link href="/telugu"><span className="text-orange-600 hover:underline telugu">తిరిగి వెళ్ళండి</span></Link></div>
    </div>
  );

  const title = lang==='te' ? (article.telugu_title||article.rephrased_title||article.original_title) : (article.rephrased_title||article.original_title);
  const content = lang==='te' ? (article.telugu_content||article.rephrased_content||article.original_content||'') : (article.rephrased_content||article.original_content||'');
  const contentClass = lang==='te' ? 'article-content-telugu' : 'article-content';
  const hasTE = hasTelugu(article);

  return (
    <div className="min-h-screen bg-white">
      <motion.div className="reading-progress" style={{ scaleX }} />
      <PremiumHeader selectedCategory="Telugu" onCategoryChange={()=>{}} searchQuery="" onSearchChange={()=>{}} />

      {/* Hero */}
      <div className="relative w-full bg-gray-900 overflow-hidden">
        <img src={getImage(article)} alt="" className="w-full max-h-[60vh] object-cover opacity-60"
          onError={handleImgError} data-category={article.category} />
        <div className="absolute inset-0 bg-gradient-to-t from-gray-900 via-gray-900/50 to-transparent"/>
        <div className="absolute bottom-0 left-0 right-0 p-6 md:p-12 max-w-5xl mx-auto">
          {article.category && (
            <span className="inline-block mb-4 bg-gradient-to-r from-orange-500 to-orange-400 text-white px-4 py-1.5 text-xs font-bold rounded-full uppercase tracking-wider">
              {article.category}
            </span>
          )}
          <h1 className={`text-2xl md:text-4xl lg:text-5xl font-black text-white leading-tight mb-4 ${lang==='te'?'telugu':''}`}
            style={{ fontFamily: lang==='en'?'var(--font-headline)':undefined }}>
            {title}
          </h1>
          <div className="flex items-center gap-4 text-white/70 text-sm">
            <span className="flex items-center gap-1.5"><Clock className="w-4 h-4"/>{fmtDate(article.published_at)}</span>
            {article.source_name && <span>• {article.source_name}</span>}
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-4xl mx-auto px-4 py-10">
        {/* Breadcrumb */}
        <div className="flex items-center gap-2 text-sm text-gray-500 mb-8">
          <Link href="/"><span className="hover:text-orange-600 transition-colors">Home</span></Link>
          <ChevronRight className="w-4 h-4"/>
          <Link href="/telugu"><span className="hover:text-orange-600 transition-colors telugu">తెలుగు వార్తలు</span></Link>
          {article.category && <><ChevronRight className="w-4 h-4"/><span>{article.category}</span></>}
        </div>

        {/* Language toggle */}
        {hasTE && (
          <div className="flex items-center gap-2 mb-8 p-4 bg-orange-50 border border-orange-100 rounded-xl">
            <span className="text-sm font-bold text-gray-700 mr-2">భాష ఎంచుకోండి:</span>
            <button onClick={()=>setLang('te')}
              className={`px-5 py-2 rounded-lg text-sm font-bold transition-all telugu ${lang==='te'?'bg-gradient-to-r from-orange-500 to-orange-400 text-white shadow-md':'bg-white border border-gray-200 text-gray-600 hover:border-orange-300'}`}>
              తెలుగు
            </button>
            <button onClick={()=>setLang('en')}
              className={`px-5 py-2 rounded-lg text-sm font-bold transition-all ${lang==='en'?'bg-gradient-to-r from-blue-600 to-blue-500 text-white shadow-md':'bg-white border border-gray-200 text-gray-600 hover:border-blue-300'}`}>
              English
            </button>
          </div>
        )}

        {/* Tags */}
        {(article.tags||[]).length>0 && (
          <div className="flex flex-wrap gap-2 mb-6">
            {(article.tags||[]).map(t=>(
              <span key={t} className="px-3 py-1 bg-gray-100 text-gray-600 text-xs font-medium rounded-full hover:bg-orange-50 hover:text-orange-700 transition-colors cursor-pointer">{t}</span>
            ))}
          </div>
        )}

        {/* Tricolor divider */}
        <div className="tricolor-stripe rounded-full mb-8"/>

        {/* Article body */}
        <div className={contentClass} dangerouslySetInnerHTML={{ __html: content }} />

        {/* Bottom tricolor */}
        <div className="tricolor-stripe-bottom rounded-full mt-10 mb-8"/>

        {/* Share */}
        <ShareBar data={{ url: window.location.href, title, summary: content.replace(/<[^>]*>/g,'').slice(0,200) }} />

        {/* Back */}
        <div className="mt-10">
          <Link href="/telugu">
            <span className="inline-flex items-center gap-2 text-orange-600 font-bold hover:gap-3 transition-all telugu">
              <ArrowLeft className="w-4 h-4"/> మరిన్ని తెలుగు వార్తలు
            </span>
          </Link>
        </div>
      </div>
      <PremiumFooter/>
      <BackToTop/>
    </div>
  );
}
