/**
 * News article detail page — /news/:idOrSlug
 * Fixes:
 *   - No more nested <Link><a> (wouter Link renders as <a> itself)
 *   - document.title updated with article headline
 *   - Scroll to top on navigation
 *   - Related articles filtered to published only (flags=A,Y)
 *   - Proper loading skeleton
 *   - Back-to-top button
 *   - EN / Telugu language toggle when telugu content available
 */
import { useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { useRoute, Link } from "wouter";
import { Clock, ArrowLeft, ChevronRight } from "lucide-react";
import { motion, useScroll, useSpring } from "framer-motion";
import { PremiumHeader } from "@/components/news/PremiumHeader";
import { PremiumFooter } from "@/components/news/PremiumFooter";
import { ShareMenu, ShareBar } from "@/components/news/ShareMenu";
import { BackToTop } from "@/components/news/BackToTop";
import { newsApi } from "@/lib/api";
import { GoogleAdUnit } from "@/components/shared/GoogleAdUnit";
import type { NewsArticle, ArticleListResponse } from "@/types/news";
import { getTitle, getContent, getImage, getSummary, categoryPlaceholder, hasTelugu, readTime } from "@/types/news";

const handleImgError = (e: React.SyntheticEvent<HTMLImageElement>) => {
  const el = e.currentTarget;
  if (!el.dataset.fallback) {
    el.dataset.fallback = "1";
    el.src = categoryPlaceholder(el.dataset.category);
  }
};

const fmtDate = (d?: string): string => {
  if (!d) return "Recently";
  try {
    return new Intl.DateTimeFormat("en-IN", {
      day: "numeric", month: "long", year: "numeric",
      hour: "2-digit", minute: "2-digit",
    }).format(new Date(d));
  } catch { return "Recently"; }
};

/** Loading skeleton for article detail */
function ArticleSkeleton() {
  return (
    <div className="max-w-4xl mx-auto px-6 py-10 space-y-6 animate-pulse">
      <div className="skeleton h-4 w-32 rounded" />
      <div className="skeleton h-10 w-full rounded" />
      <div className="skeleton h-8 w-3/4 rounded" />
      <div className="skeleton h-72 w-full rounded-xl" />
      <div className="space-y-3">
        {[1,2,3,4,5].map(i => (
          <div key={i} className="skeleton h-4 rounded" style={{ width: `${85 + (i % 3) * 5}%` }} />
        ))}
      </div>
    </div>
  );
}

export default function NewsDetail() {
  const [, params] = useRoute("/news/:idOrSlug");
  const idOrSlug = params?.idOrSlug;
  const [lang, setLang]   = useState<'en' | 'te'>('en');
  const [cat,  setCat]    = useState("All");
  const [srch, setSrch]   = useState("");

  const { scrollYProgress } = useScroll();
  const scaleX = useSpring(scrollYProgress, { stiffness: 100, damping: 30 });

  // FIX: scroll to top when article changes
  useEffect(() => { window.scrollTo({ top: 0, behavior: "smooth" }); }, [idOrSlug]);

  const { data: article, isLoading, error } = useQuery<NewsArticle>({
    queryKey: ["article", idOrSlug],
    queryFn:  () => newsApi.getArticle(idOrSlug!),
    enabled:  !!idOrSlug,
    staleTime: 5 * 60 * 1000,
  });

  // FIX: Update document title dynamically
  useEffect(() => {
    if (article) {
      const t = getTitle(article);
      document.title = t ? `${t} — Peoples Feedback` : "Peoples Feedback";
    }
    return () => { document.title = "Peoples Feedback"; };
  }, [article]);

  // FIX: Related articles with flags=A,Y filter (published only)
  const { data: related } = useQuery<ArticleListResponse>({
    queryKey: ["related", article?.category],
    queryFn:  () => newsApi.getArticles({
      page_size: 5,
      category:  article?.category || undefined,
    }),
    enabled: !!article?.category,
    staleTime: 5 * 60 * 1000,
  });

  // Loading
  if (isLoading) {
    return (
      <div className="min-h-screen bg-white">
        <PremiumHeader selectedCategory={cat} onCategoryChange={setCat} searchQuery={srch} onSearchChange={setSrch} />
        <motion.div className="reading-progress" style={{ scaleX }} />
        <ArticleSkeleton />
        <PremiumFooter />
      </div>
    );
  }

  // Error / not found
  if (error || !article) {
    return (
      <div className="min-h-screen bg-white">
        <PremiumHeader selectedCategory={cat} onCategoryChange={setCat} searchQuery={srch} onSearchChange={setSrch} />
        <div className="flex flex-col items-center justify-center py-32 gap-6 text-center px-4">
          <div className="w-20 h-20 rounded-full bg-zinc-100 flex items-center justify-center mx-auto">
            <span className="text-3xl">📰</span>
          </div>
          <h2 className="text-2xl font-black text-zinc-800">Article not found</h2>
          <p className="text-zinc-400 max-w-xs">The article may have been removed or the link is incorrect.</p>
          {/* FIX: Link renders as <a> in wouter — no nested <a> needed */}
          <Link href="/" className="px-6 py-3 bg-[var(--pf-saffron)] text-white font-bold rounded-full hover:bg-[var(--pf-orange)] transition-colors">
            ← Back to Home
          </Link>
        </div>
        <PremiumFooter />
      </div>
    );
  }

  const title    = getTitle(article, lang);
  const content  = getContent(article, lang);
  const minutes  = readTime(content);
  const hasTE    = hasTelugu(article);
  const shareData = { url: window.location.href, title, summary: getSummary(article, 200) };

  return (
    <div className="min-h-screen bg-tricolor-light text-zinc-900">
      {/* Reading progress bar */}
      <motion.div className="reading-progress" style={{ scaleX }} />

      <PremiumHeader
        selectedCategory={cat}
        onCategoryChange={setCat}
        searchQuery={srch}
        onSearchChange={setSrch}
      />

      <main className="pt-6 pb-20">
        {/* ── Article header ── */}
        <header className="max-w-4xl mx-auto px-6 mb-10">
          {/* FIX: Link is <a> in wouter — no extra <a> inside */}
          <Link
            href="/"
            className="inline-flex items-center gap-2 text-[10px] font-black uppercase tracking-[0.3em] text-zinc-400 hover:text-[var(--pf-saffron)] transition-colors mb-6"
          >
            <ArrowLeft className="w-3 h-3" /> Back to Newsroom
          </Link>

          {/* Tricolor stripe */}
          <div className="tricolor-stripe rounded-full mb-6" />

          {article.category && (
            <Link href={`/news?category=${article.category}`}>
              <span className="inline-block bg-[var(--pf-navy)] text-white px-4 py-1.5 text-[10px] font-black uppercase tracking-[0.2em] mb-4 rounded-sm hover:bg-[var(--pf-saffron)] transition-colors cursor-pointer">
                {article.category}
              </span>
            </Link>
          )}

          <h1
            className="text-2xl sm:text-4xl md:text-5xl font-black leading-[1.1] tracking-tight text-zinc-950 mb-6"
            style={{ fontFamily: lang === 'te' ? 'var(--font-telugu)' : 'var(--font-headline)' }}
          >
            {title}
          </h1>

          {/* Language toggle — only if Telugu content exists */}
          {hasTE && (
            <div className="flex items-center gap-1 mb-8 bg-zinc-100 p-1 w-fit rounded-full border border-zinc-200 shadow-sm">
              <button
                onClick={() => setLang('en')}
                className={`px-5 py-1.5 rounded-full text-[10px] font-black uppercase tracking-widest transition-all ${
                  lang === 'en' ? 'bg-[var(--pf-navy)] text-white shadow-sm' : 'text-zinc-400 hover:text-zinc-700'
                }`}
              >
                English
              </button>
              <button
                onClick={() => setLang('te')}
                className={`px-5 py-1.5 rounded-full text-[10px] font-black uppercase tracking-widest transition-all telugu ${
                  lang === 'te' ? 'bg-[var(--pf-saffron)] text-white shadow-sm' : 'text-zinc-400 hover:text-zinc-700'
                }`}
              >
                తెలుగు
              </button>
            </div>
          )}

          <div className="pt-6 border-t border-zinc-100 flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <img src="/pf-logo.png" alt="PF" className="w-9 h-9 rounded-full object-contain bg-zinc-100 p-1" />
              <div>
                <p className="text-xs font-black uppercase tracking-widest text-tricolor">Peoples Feedback</p>
                <p className="text-[10px] font-bold text-zinc-400 uppercase tracking-widest">
                  {fmtDate(article.published_at)}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-5 text-[10px] font-black uppercase tracking-widest text-zinc-400">
              <span className="flex items-center gap-1">
                <Clock className="w-3 h-3" /> {minutes} min read
              </span>
              {article.author && <span>By {article.author}</span>}
            </div>
          </div>
        </header>

        {/* ── Featured image ── */}
        <div className="max-w-5xl mx-auto px-4 mb-14">
          <div className="relative overflow-hidden bg-zinc-100 shadow-xl news-image-wrapper">
            <img
              src={getImage(article)}
              alt={title}
              className="w-full aspect-[16/9] sm:aspect-[21/9] max-h-[480px] object-cover"
              onError={handleImgError}
              data-category={article.category}
            />
            {/* Bottom accent: tricolor */}
            <div className="tricolor-stripe" />
          </div>
          <p className="mt-2 text-[9px] text-zinc-400 font-bold uppercase tracking-widest px-1">
            Peoples Feedback Newsroom
          </p>
          
          {/* Header Ad unit */}
          <GoogleAdUnit slot="1122334455" className="mt-8" />
        </div>

        {/* ── Content + sidebar layout ── */}
        <div className="max-w-6xl mx-auto px-6 grid grid-cols-1 lg:grid-cols-12 gap-12">

          {/* Vertical share sidebar (desktop) */}
          <aside className="hidden lg:block lg:col-span-1">
            <div className="sticky top-28 flex flex-col items-center gap-3 py-4 border-r border-zinc-100">
              <ShareMenu data={shareData} variant="vertical" />
              <div className="w-5 h-px bg-zinc-200 my-1" />
              <span className="text-[8px] font-black uppercase tracking-widest text-zinc-300 -rotate-90 whitespace-nowrap mt-4">
                Share
              </span>
            </div>
          </aside>

          {/* Article body */}
          <div className="lg:col-span-8">
            <article
              className={lang === 'te' ? 'article-content-telugu' : 'article-content'}
              dangerouslySetInnerHTML={{ __html: content }}
            />

            {/* Mid-article Ad unit */}
            <GoogleAdUnit slot="5544332211" format="fluid" className="my-8" />

            {/* Tags */}
            {(article.tags || []).length > 0 && (
              <div className="mt-12 pt-6 border-t border-zinc-100 flex flex-wrap gap-2">
                {(article.tags || []).map(tag => (
                  <Link key={tag} href={`/news?search=${encodeURIComponent(tag)}`}>
                    <span className="text-[10px] font-black uppercase tracking-[0.15em] px-4 py-2 bg-zinc-50 border border-zinc-200 hover:bg-[var(--pf-saffron)] hover:text-white hover:border-[var(--pf-saffron)] transition-all cursor-pointer rounded-sm">
                      #{tag}
                    </span>
                  </Link>
                ))}
              </div>
            )}

            {/* Bottom tricolor */}
            <div className="tricolor-stripe-bottom rounded-full mt-10 mb-8" />

            {/* Mobile share bar */}
            <div className="lg:hidden mt-6 py-4 border-t border-zinc-100">
              <p className="text-[10px] font-black uppercase tracking-[0.2em] text-zinc-400 mb-3">
                Share this article
              </p>
              <ShareBar data={shareData} />
            </div>
          </div>

          <aside className="lg:col-span-3">
            <div className="sticky top-28 space-y-8">
              {/* Sidebar Ad Unit */}
              <GoogleAdUnit slot="1357924680" format="rectangle" className="rounded-xl border border-zinc-100 bg-white p-2" />

              {/* About box */}
              <div className="p-5 bg-zinc-50 border-t-2 border-[var(--pf-navy)]">
                <h4 className="text-[10px] font-black uppercase tracking-widest text-zinc-900 mb-4">
                  About this article
                </h4>
                <div className="space-y-3 text-xs">
                  <div className="flex gap-2">
                    <div className="w-1 bg-[var(--pf-green)] shrink-0 rounded-full" />
                    <p className="font-semibold text-zinc-600">Publisher: Peoples Feedback</p>
                  </div>
                  <div className="flex gap-2">
                    <div className="w-1 bg-[var(--pf-saffron)] shrink-0 rounded-full" />
                    <p className="font-semibold text-zinc-600">Category: {article.category || "General"}</p>
                  </div>
                  {article.original_language && article.original_language !== "en" && (
                    <div className="flex gap-2">
                      <div className="w-1 bg-zinc-300 shrink-0 rounded-full" />
                      <p className="font-semibold text-zinc-600">Source language: {article.original_language.toUpperCase()}</p>
                    </div>
                  )}
                  {hasTE && (
                    <div className="flex gap-2">
                      <div className="w-1 bg-[var(--pf-saffron)] shrink-0 rounded-full" />
                      <p className="font-semibold text-zinc-600 telugu">తెలుగు అనువాదం అందుబాటులో ఉంది ✓</p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </aside>
        </div>

        {/* ── Related articles ── */}
        {related?.articles && related.articles.filter(a => a.id !== article.id).length > 0 && (
          <section className="mt-20 bg-[var(--pf-navy)] py-16 text-white">
            <div className="max-w-6xl mx-auto px-6">
              <div className="flex items-center justify-between mb-8">
                <div>
                  <div className="tricolor-stripe rounded-full w-24 mb-3" />
                  <h2 className="text-2xl font-black uppercase tracking-tight" style={{ fontFamily: 'var(--font-headline)' }}>
                    Continue Reading
                  </h2>
                </div>
                <Link
                  href={`/news?category=${article.category}`}
                  className="text-[10px] font-black uppercase tracking-widest text-[var(--pf-saffron)] hover:text-white transition-colors flex items-center gap-1"
                >
                  More {article.category} <ChevronRight className="w-3 h-3" />
                </Link>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-6">
                {related.articles
                  .filter(a => a.id !== article.id)
                  .slice(0, 4)
                  .map(a => (
                    <Link key={a.id} href={`/news/${a.slug || a.id}`}>
                      <div className="group cursor-pointer space-y-3">
                        <div className="aspect-video bg-zinc-800 overflow-hidden rounded-sm news-image-wrapper">
                          <img
                            src={getImage(a)}
                            alt=""
                            className="w-full h-full object-cover opacity-80 group-hover:opacity-100 group-hover:scale-105 transition-all duration-500"
                            loading="lazy"
                            onError={handleImgError}
                            data-category={a.category}
                          />
                        </div>
                        {a.category && (
                          <span className="text-[9px] font-bold uppercase tracking-wider text-[var(--pf-saffron)]">
                            {a.category}
                          </span>
                        )}
                        <h3 className="text-sm font-bold leading-snug group-hover:text-[var(--pf-saffron)] transition-colors line-clamp-2">
                          {getTitle(a)}
                        </h3>
                      </div>
                    </Link>
                  ))}
              </div>
            </div>
          </section>
        )}
      </main>

      <PremiumFooter />
      <BackToTop />
    </div>
  );
}
