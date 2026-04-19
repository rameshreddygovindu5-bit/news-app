/**
 * Telugu Article Detail — /telugu/:idOrSlug
 * Displays article in Telugu script with English toggle.
 * FIXED: Removed window.location.reload() useEffect that caused reload loop.
 * IMPROVED: Better loading state, scroll-to-top, proper title update.
 */
import { useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { useRoute, Link } from "wouter";
import { Clock, ArrowLeft, ChevronRight } from "lucide-react";
import { motion, useScroll, useSpring } from "framer-motion";
import { PremiumHeader } from "@/components/news/PremiumHeader";
import { PremiumFooter } from "@/components/news/PremiumFooter";
import { ShareBar } from "@/components/news/ShareMenu";
import { BackToTop } from "@/components/news/BackToTop";
import { newsApi } from "@/lib/api";
import type { NewsArticle } from "@/types/news";
import { getImage, categoryPlaceholder, hasTelugu } from "@/types/news";

const handleImgError = (e: React.SyntheticEvent<HTMLImageElement>) => {
  const el = e.currentTarget;
  if (!el.dataset.fallback) { el.dataset.fallback = "1"; el.src = categoryPlaceholder(el.dataset.category); }
};

const fmtDate = (d?: string) => {
  if (!d) return "ఇటీవల";
  try {
    return new Intl.DateTimeFormat("te-IN", { day: "numeric", month: "long", year: "numeric" }).format(new Date(d));
  } catch { return "ఇటీవల"; }
};

function LoadingSkeleton() {
  return (
    <div className="min-h-screen bg-white">
      <div className="skeleton h-[50vh] w-full" />
      <div className="max-w-4xl mx-auto px-4 py-10 space-y-4">
        <div className="skeleton h-6 w-32 rounded" />
        <div className="skeleton h-10 w-full rounded" />
        <div className="skeleton h-8 w-4/5 rounded" />
        <div className="skeleton h-48 w-full rounded-xl" />
        {[1,2,3,4,5].map(i => (
          <div key={i} className="skeleton h-4 rounded" style={{ width: `${80 + (i % 3) * 8}%` }} />
        ))}
      </div>
    </div>
  );
}

export default function TeluguDetail() {
  const [, params] = useRoute("/telugu/:idOrSlug");
  const idOrSlug   = params?.idOrSlug;
  const [lang, setLang] = useState<"te" | "en">("te");

  const { scrollYProgress } = useScroll();
  const scaleX = useSpring(scrollYProgress, { stiffness: 100, damping: 30 });

  const { data: article, isLoading } = useQuery<NewsArticle>({
    queryKey: ["article", idOrSlug],
    queryFn: () => newsApi.getArticle(idOrSlug!),
    enabled: !!idOrSlug,
  });

  // Scroll to top when article changes — NO reload
  useEffect(() => {
    window.scrollTo({ top: 0, behavior: "smooth" });
  }, [idOrSlug]);

  // Update page title from article content
  useEffect(() => {
    if (article) {
      const t = article.telugu_title || article.rephrased_title || article.original_title;
      document.title = t ? `${t} — Peoples Feedback` : "తెలుగు వార్తలు — Peoples Feedback";
    }
    return () => { document.title = "Peoples Feedback"; };
  }, [article]);

  if (isLoading) return (
    <>
      <motion.div className="reading-progress" style={{ scaleX }} />
      <PremiumHeader selectedCategory="Telugu" onCategoryChange={() => {}} searchQuery="" onSearchChange={() => {}} />
      <LoadingSkeleton />
      <PremiumFooter />
    </>
  );

  if (!article) return (
    <div className="min-h-screen bg-white flex items-center justify-center">
      <div className="text-center px-4">
        <p className="text-6xl mb-6">📰</p>
        <p className="text-2xl telugu text-gray-600 mb-2">వార్త అందుబాటులో లేదు</p>
        <p className="text-gray-400 text-sm mb-6">The article may have been removed or the link is incorrect.</p>
        <Link href="/telugu">
          <span className="inline-flex items-center gap-2 px-6 py-3 bg-[var(--pf-saffron)] text-white font-bold rounded-full hover:bg-[var(--pf-orange)] transition-colors telugu">
            <ArrowLeft className="w-4 h-4" /> తిరిగి వెళ్ళండి
          </span>
        </Link>
      </div>
    </div>
  );

  const hasTE  = hasTelugu(article);
  const title  = lang === "te"
    ? (article.telugu_title || article.rephrased_title || article.original_title)
    : (article.rephrased_title || article.original_title);
  const content = lang === "te"
    ? (article.telugu_content || article.rephrased_content || article.original_content || "")
    : (article.rephrased_content || article.original_content || "");
  const contentClass = lang === "te" ? "article-content-telugu" : "article-content";

  return (
    <div className="min-h-screen bg-white">
      <motion.div className="reading-progress" style={{ scaleX }} />
      <PremiumHeader selectedCategory="Telugu" onCategoryChange={() => {}} searchQuery="" onSearchChange={() => {}} />

      {/* Hero */}
      <div className="relative w-full bg-gray-900 overflow-hidden">
        <img src={getImage(article)} alt="" className="w-full max-h-[60vh] object-cover opacity-55"
          onError={handleImgError} data-category={article.category} />
        <div className="absolute inset-0 bg-gradient-to-t from-gray-950 via-gray-900/60 to-transparent" />
        <div className="absolute bottom-0 left-0 right-0 p-6 md:p-12 max-w-5xl mx-auto">
          {article.category && (
            <span className="inline-block mb-4 bg-gradient-to-r from-orange-500 to-orange-400 text-white px-4 py-1.5 text-xs font-bold rounded-full uppercase tracking-wider shadow-lg">
              {article.category}
            </span>
          )}
          <h1 className={`text-2xl md:text-4xl lg:text-5xl font-black text-white leading-tight mb-4 ${lang === "te" ? "telugu" : ""}`}>
            {title}
          </h1>
          <div className="flex flex-wrap items-center gap-4 text-white/70 text-sm">
            <span className="flex items-center gap-1.5">
              <Clock className="w-4 h-4" />{fmtDate(article.published_at)}
            </span>
            {article.source_name && (
              <span className="flex items-center gap-1.5 bg-white/10 backdrop-blur-sm px-3 py-1 rounded-full text-xs font-medium">
                {article.source_name}
              </span>
            )}
          </div>
        </div>
      </div>


      {/* Content */}
      <div className="max-w-4xl mx-auto px-4 py-10">
        {/* Breadcrumb */}
        <nav className="flex items-center gap-1.5 text-sm text-gray-500 mb-8 flex-wrap">
          <Link href="/"><span className="hover:text-orange-600 transition-colors cursor-pointer">Home</span></Link>
          <ChevronRight className="w-3.5 h-3.5 shrink-0" />
          <Link href="/telugu"><span className="hover:text-orange-600 transition-colors cursor-pointer telugu">తెలుగు వార్తలు</span></Link>
          {article.category && (
            <><ChevronRight className="w-3.5 h-3.5 shrink-0" /><span className="text-gray-400">{article.category}</span></>
          )}
        </nav>

        {/* Language toggle */}
        {hasTE && (
          <div className="flex items-center gap-3 mb-8 p-4 bg-gradient-to-r from-orange-50 to-blue-50 border border-orange-100 rounded-2xl">
            <span className="text-sm font-bold text-gray-600 shrink-0">భాష:</span>
            <button onClick={() => setLang("te")}
              className={`px-5 py-2 rounded-xl text-sm font-bold transition-all telugu ${lang === "te" ? "bg-gradient-to-r from-orange-500 to-orange-400 text-white shadow-md scale-105" : "bg-white border border-gray-200 text-gray-600 hover:border-orange-300"}`}>
              తెలుగు
            </button>
            <button onClick={() => setLang("en")}
              className={`px-5 py-2 rounded-xl text-sm font-bold transition-all ${lang === "en" ? "bg-gradient-to-r from-[var(--pf-navy)] to-[var(--pf-blue)] text-white shadow-md scale-105" : "bg-white border border-gray-200 text-gray-600 hover:border-blue-300"}`}>
              English
            </button>
          </div>
        )}

        {/* Tags */}
        {(article.tags || []).length > 0 && (
          <div className="flex flex-wrap gap-2 mb-6">
            {(article.tags || []).map(t => (
              <span key={t} className="px-3 py-1 bg-gray-100 text-gray-600 text-xs font-medium rounded-full hover:bg-orange-50 hover:text-orange-700 transition-colors">
                #{t}
              </span>
            ))}
          </div>
        )}

        {/* Tricolor divider */}
        <div className="tricolor-stripe rounded-full mb-8" />

        {/* Article body */}
        <div className={contentClass} dangerouslySetInnerHTML={{ __html: content }} />


        {/* Tricolor divider */}
        <div className="tricolor-stripe-bottom rounded-full mt-10 mb-8" />

        {/* Share */}
        <ShareBar data={{ url: window.location.href, title, summary: content.replace(/<[^>]*>/g, "").slice(0, 200) }} />

        {/* Back link */}
        <div className="mt-10">
          <Link href="/telugu">
            <span className="back-btn telugu">
              <ArrowLeft className="w-4 h-4" /> మరిన్ని తెలుగు వార్తలు
            </span>
          </Link>
        </div>
      </div>

      <PremiumFooter />
      <BackToTop />
    </div>
  );
}
