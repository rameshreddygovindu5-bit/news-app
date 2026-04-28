/**
 * Telugu Article Detail — /telugu/:idOrSlug
 * PF Editorial Design System — Telugu Edition
 * Optimised for readability, mobile-first, consistent with PF UI.
 */
import { useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { useRoute, Link } from "wouter";
import { Clock, ArrowLeft, Share2, Languages, ChevronRight, Bookmark } from "lucide-react";
import { motion, useScroll, useSpring } from "framer-motion";
import { PremiumHeader } from "@/components/news/PremiumHeader";
import { PremiumFooter } from "@/components/news/PremiumFooter";
import { BackToTop } from "@/components/news/BackToTop";
import { ShareMenu } from "@/components/news/ShareMenu";
import SEO from "@/components/shared/SEO";
import { newsApi } from "@/lib/api";
import type { NewsArticle } from "@/types/news";
import { getTitle, getContent, getImage, getSummary, categoryPlaceholder, hasTelugu } from "@/types/news";

// ─── Helpers ─────────────────────────────────────────────────────────────────

const handleImgError = (e: React.SyntheticEvent<HTMLImageElement>) => {
  const el = e.currentTarget;
  if (!el.dataset.fallback) { el.dataset.fallback = "1"; el.src = categoryPlaceholder(el.dataset.category); }
};

const fmtDate = (d?: string) => {
  if (!d) return "ఇప్పుడే";
  try {
    return new Intl.DateTimeFormat("te-IN", {
      day: "numeric", month: "long", year: "numeric",
      hour: "2-digit", minute: "2-digit",
    }).format(new Date(d));
  } catch { return ""; }
};

const readTime = (text: string) => {
  const words = text.replace(/<[^>]+>/g, "").split(/\s+/).length;
  return `${Math.max(1, Math.ceil(words / 130))} నిమిషాల పఠనం`;
};

// ─── Article body renderer ────────────────────────────────────────────────────
// Renders structured AI HTML (p/ul/li/strong/i) in Telugu-optimised styles.

function ArticleBody({ html, isTelugu }: { html: string; isTelugu: boolean }) {
  const baseFont = isTelugu ? "telugu" : "";
  const lineH = isTelugu ? "leading-[2.0]" : "leading-[1.9]";
  const fontSize = isTelugu ? "text-[1.1rem] md:text-[1.2rem]" : "text-[1.05rem] md:text-[1.15rem]";

  if (!html?.trim()) return null;

  // If plain text (no tags), build basic paragraphs
  if (!/<[a-zA-Z]/.test(html)) {
    return (
      <div className={`space-y-5 ${baseFont} ${fontSize} ${lineH} text-zinc-700`}>
        {html.trim().split(/\n\s*\n/).filter(Boolean).map((p, i) => (
          <p key={i} className="mb-5">{p.trim()}</p>
        ))}
      </div>
    );
  }

  // Rich HTML — render via dangerouslySetInnerHTML with article-content class
  return (
    <div
      className={`article-content${isTelugu ? " article-content-telugu" : ""} ${baseFont}`}
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}

// ─── Related card (sidebar) ───────────────────────────────────────────────────

function RelatedCard({ article }: { article: NewsArticle }) {
  const title = getTitle(article, "te");
  const img = getImage(article);
  return (
    <Link href={`/telugu/${article.slug || article.id}`}>
      <div className="group flex gap-3 cursor-pointer hover:bg-[var(--pf-saffron)]/5 p-2 rounded-lg transition-colors">
        <div className="w-20 h-14 rounded-lg overflow-hidden flex-shrink-0 bg-gray-100">
          <img src={img} alt="" data-category={article.category}
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
            onError={handleImgError} />
        </div>
        <p className="telugu text-sm font-bold text-zinc-800 group-hover:text-[var(--pf-saffron)] transition-colors leading-snug line-clamp-3"
          style={{ lineHeight: 1.5 }}>
          {title}
        </p>
      </div>
    </Link>
  );
}

// ─── Loading skeleton ─────────────────────────────────────────────────────────

function LoadingSkeleton() {
  return (
    <div className="min-h-screen bg-white">
      <div className="max-w-4xl mx-auto px-4 pt-24 animate-pulse space-y-6">
        <div className="h-6 bg-gray-200 rounded w-1/4" />
        <div className="h-10 bg-gray-200 rounded w-full" />
        <div className="h-10 bg-gray-200 rounded w-3/4" />
        <div className="h-64 bg-gray-200 rounded-2xl w-full" />
        <div className="space-y-3">
          {[1, 2, 3, 4].map(i => <div key={i} className="h-4 bg-gray-100 rounded w-full" />)}
        </div>
      </div>
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function TeluguDetail() {
  const [, params] = useRoute("/telugu/:idOrSlug");
  const idOrSlug = params?.idOrSlug;
  const [lang, setLang] = useState<"te" | "en">("te");

  const { scrollYProgress } = useScroll();
  const scaleX = useSpring(scrollYProgress, { stiffness: 100, damping: 30 });

  const { data: article, isLoading, isError } = useQuery<NewsArticle>({
    queryKey: ["article", idOrSlug],
    queryFn: () => newsApi.getArticle(idOrSlug!),
    enabled: !!idOrSlug,
    retry: 2,
    staleTime: 5 * 60 * 1000,
  });

  useEffect(() => { window.scrollTo({ top: 0, behavior: "smooth" }); }, [idOrSlug]);

  if (isLoading) return <LoadingSkeleton />;

  if (isError || !article) {
    return (
      <div className="min-h-screen bg-white flex flex-col items-center justify-center gap-4 px-4">
        <div className="w-16 h-16 rounded-full bg-[var(--pf-saffron)]/10 flex items-center justify-center mb-2">
          <Languages className="w-8 h-8 text-[var(--pf-saffron)]/50" />
        </div>
        <h2 className="telugu text-2xl font-black text-zinc-800">వార్త అందుబాటులో లేదు</h2>
        <p className="telugu text-zinc-400 text-center text-sm">ఈ వార్త తొలగించబడింది లేదా అందుబాటులో లేదు.</p>
        <Link href="/telugu">
          <button className="mt-4 flex items-center gap-2 px-5 py-2.5 bg-[var(--pf-navy)] text-white font-bold rounded-full text-sm hover:opacity-90 transition-opacity">
            <ArrowLeft className="w-4 h-4" />
            <span className="telugu">తిరిగి వెళ్ళండి</span>
          </button>
        </Link>
      </div>
    );
  }

  const hasTE = hasTelugu(article);
  const activeTitle = getTitle(article, lang);
  const activeContent = getContent(article, lang);
  const plainText = activeContent.replace(/<[^>]+>/g, " ");
  const imgUrl = getImage(article);

  const shareData = {
    title: activeTitle,
    description: plainText.slice(0, 160),
    url: `${window.location.origin}/telugu/${article.slug || article.id}`,
    image: imgUrl,
  };

  return (
    <div className="min-h-screen bg-white text-zinc-900">
      <SEO
        title={`${activeTitle} | తెలుగు వార్తలు`}
        description={plainText.slice(0, 160)}
        image={imgUrl}
        url={`/telugu/${article.slug || article.id}`}
      />

      {/* Reading progress bar */}
      <motion.div
        className="fixed top-0 left-0 right-0 h-1 z-[200] origin-left"
        style={{
          scaleX,
          background: "linear-gradient(90deg, var(--pf-saffron), var(--pf-navy), var(--pf-green))"
        }}
      />

      <PremiumHeader
        selectedCategory="తెలుగు వార్తలు"
        onCategoryChange={() => { }}
        searchQuery=""
        onSearchChange={() => { }}
      />

      <main className="pt-6 pb-20">

        {/* ── Breadcrumb ── */}
        <div className="max-w-4xl mx-auto px-4 mb-6">
          <nav className="flex items-center gap-1.5 text-[11px] text-zinc-400 font-medium">
            <a href="/" className="hover:text-[var(--pf-navy)] transition-colors">హోమ్</a>
            <ChevronRight className="w-3 h-3" />
            <Link href="/telugu" className="hover:text-[var(--pf-navy)] transition-colors">తెలుగు వార్తలు</Link>
            <ChevronRight className="w-3 h-3" />
            <span className="telugu text-zinc-600 truncate max-w-[200px]">{activeTitle}</span>
          </nav>
        </div>

        {/* ── Article header ── */}
        <header className="max-w-4xl mx-auto px-4 mb-8">
          {/* Back link */}
          <Link href="/telugu"
            className="group inline-flex items-center gap-1.5 text-[11px] font-bold text-zinc-400 hover:text-[var(--pf-saffron)] transition-colors mb-5">
            <ArrowLeft className="w-3.5 h-3.5 group-hover:-translate-x-0.5 transition-transform" />
            <span className="telugu">తిరిగి వెళ్ళండి</span>
          </Link>

          {/* Category + badges */}
          <div className="flex flex-wrap items-center gap-2 mb-4">
            {article.category && (
              <span className="bg-[var(--pf-saffron)] text-white px-3 py-1 text-[10px] font-black uppercase tracking-widest rounded-full">
                {article.category}
              </span>
            )}
            {article.ai_status === "AI_SUCCESS" || article.ai_status === "AI_RETRY_SUCCESS" ? (
              <span className="flex items-center gap-1 bg-emerald-100 text-emerald-700 px-3 py-1 text-[10px] font-bold rounded-full border border-emerald-200">
                ✅ AI Rephrased
              </span>
            ) : null}
          </div>

          {/* Headline */}
          <h1
            className={`font-black text-zinc-950 leading-snug mb-5 ${lang === "te" ? "telugu" : ""}`}
            style={{
              fontSize: "clamp(1.6rem, 4vw, 2.6rem)",
              lineHeight: lang === "te" ? 1.45 : 1.2,
            }}
          >
            {activeTitle}
          </h1>

          {/* Meta row */}
          <div className="flex flex-wrap items-center justify-between gap-4 pt-4 border-t border-gray-100">
            <div className="flex items-center gap-4">
              {/* Author avatar */}
              <div className="w-10 h-10 rounded-full bg-[var(--pf-navy)] flex items-center justify-center text-white text-xs font-black shadow-sm flex-shrink-0">
                PF
              </div>
              <div>
                <p className="text-xs font-black text-zinc-800">PF తెలుగు డెస్క్</p>
                <div className="flex items-center gap-2 mt-0.5">
                  <span className="flex items-center gap-1 text-[10px] text-zinc-400 font-medium">
                    <Clock className="w-3 h-3" />{fmtDate(article.published_at)}
                  </span>
                  {activeContent && (
                    <span className="text-[10px] text-zinc-400 telugu">· {readTime(activeContent)}</span>
                  )}
                </div>
              </div>
            </div>

            {/* Language toggle + share */}
            <div className="flex items-center gap-2">
              {hasTE && (
                <div className="flex bg-gray-100 p-1 rounded-full border border-gray-200">
                  {(["te", "en"] as const).map(l => (
                    <button key={l} onClick={() => setLang(l)}
                      className={`px-4 py-1.5 rounded-full text-[10px] font-black uppercase tracking-widest transition-all ${lang === l
                        ? "bg-white text-[var(--pf-navy)] shadow-sm"
                        : "text-zinc-400 hover:text-zinc-600"
                        }`}>
                      {l === "te" ? "తెలుగు" : "English"}
                    </button>
                  ))}
                </div>
              )}
              <ShareMenu shareData={shareData} />
            </div>
          </div>
        </header>

        {/* ── Hero image ── */}
        <div className="max-w-5xl mx-auto px-4 mb-10">
          <div className="rounded-2xl overflow-hidden shadow-xl bg-gray-100 aspect-[16/7] relative">
            <img
              src={imgUrl}
              alt=""
              data-category={article.category}
              className="w-full h-full object-cover"
              onError={handleImgError}
            />
            {/* Tricolor accent overlay bottom */}
            <div className="absolute bottom-0 left-0 right-0 h-1 tricolor-stripe" />
          </div>
        </div>

        {/* ── Body + Sidebar grid ── */}
        <div className="max-w-7xl mx-auto px-4 grid grid-cols-1 lg:grid-cols-12 gap-10">

          {/* Article body */}
          <article className="lg:col-span-8">

            {/* Lead summary */}
            {getSummary(article, 220) && (
              <div className="bg-[var(--pf-saffron)]/5 border-l-4 border-[var(--pf-saffron)] rounded-r-xl px-5 py-4 mb-8">
                <p className={`font-semibold text-zinc-700 leading-relaxed ${lang === "te" ? "telugu" : ""}`}
                  style={{ fontSize: lang === "te" ? "1.0rem" : "0.95rem", lineHeight: lang === "te" ? 1.8 : 1.7 }}>
                  {getSummary(article, 220)}
                </p>
              </div>
            )}

            {/* Main content */}
            <ArticleBody html={activeContent} isTelugu={lang === "te"} />

            {/* Tags */}
            {(article.tags ?? []).length > 0 && (
              <div className="mt-10 pt-6 border-t border-gray-100">
                <p className="text-[10px] font-black uppercase tracking-widest text-zinc-400 mb-3">ట్యాగ్‌లు</p>
                <div className="flex flex-wrap gap-2">
                  {article.tags?.map(t => (
                    <span key={t}
                      className="px-3 py-1.5 bg-gray-100 hover:bg-[var(--pf-saffron)] hover:text-white text-zinc-600 text-[10px] font-bold uppercase tracking-widest rounded-full transition-all cursor-pointer">
                      #{t}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Share footer */}
            <div className="mt-10 pt-6 border-t border-gray-100 flex items-center justify-between">
              <p className="text-sm text-zinc-400 font-medium telugu">ఈ వార్తను షేర్ చేయండి:</p>
              <ShareMenu shareData={shareData} />
            </div>

            {/* Back link */}
            <div className="mt-8">
              <Link href="/telugu">
                <button className="flex items-center gap-2 px-5 py-2.5 border-2 border-gray-200 rounded-full text-sm font-bold text-zinc-600 hover:border-[var(--pf-saffron)] hover:text-[var(--pf-saffron)] transition-all">
                  <ArrowLeft className="w-4 h-4" />
                  <span className="telugu">అన్ని తెలుగు వార్తలు</span>
                </button>
              </Link>
            </div>
          </article>

          {/* Sidebar */}
          <aside className="lg:col-span-4">
            <div className="sticky top-24 space-y-6">

              {/* Quick Insight */}
              <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
                <h4 className="telugu text-[11px] font-black uppercase tracking-widest text-[var(--pf-saffron)] mb-4 flex items-center gap-2">
                  <Clock className="w-3.5 h-3.5" /> ముఖ్య అంశాలు
                </h4>
                <div className="space-y-3">
                  <div className="flex gap-3">
                    <div className="w-1 bg-[var(--pf-green)] rounded-full flex-shrink-0" />
                    <p className="telugu text-xs text-zinc-600 leading-relaxed" style={{ lineHeight: 1.8 }}>
                      ఈ నివేదిక పీపుల్స్ ఫీడ్‌బ్యాక్ కమ్యూనిటీ డెస్క్ ధృవీకరించింది.
                    </p>
                  </div>
                  <div className="flex gap-3">
                    <div className="w-1 bg-[var(--pf-navy)] rounded-full flex-shrink-0" />
                    <p className="telugu text-xs text-zinc-500 leading-relaxed" style={{ lineHeight: 1.8 }}>
                      ప్రచురణ: {fmtDate(article.published_at)}
                    </p>
                  </div>
                </div>
              </div>


            </div>
          </aside>
        </div>
      </main>

      <PremiumFooter />
      <BackToTop />
    </div>
  );
}
