import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useRoute, Link, useLocation } from "wouter";
import { Clock, ArrowLeft, ChevronRight } from "lucide-react";
import { motion, useScroll, useSpring } from "framer-motion";
import { PremiumHeader } from "@/components/news/PremiumHeader";
import { PremiumFooter } from "@/components/news/PremiumFooter";
import { ShareMenu, ShareBar } from "@/components/news/ShareMenu";
import { newsApi } from "@/lib/api";
import type { NewsArticle, ArticleListResponse } from "@/types/news";
import { getTitle, getContent, getImage, getSummary, categoryPlaceholder } from "@/types/news";

/** Handle broken images — fall back to category placeholder */
const handleImgError = (e: React.SyntheticEvent<HTMLImageElement>) => {
  const el = e.currentTarget;
  if (!el.dataset.fallback) {
    el.dataset.fallback = "1";
    el.src = categoryPlaceholder(el.dataset.category || 'news');
  }
};

const fmtDate = (d?: string) => {
  if (!d) return "Recently";
  try {
    return new Intl.DateTimeFormat("en-US", {
      day: "numeric", month: "long", year: "numeric",
      hour: "2-digit", minute: "2-digit",
    }).format(new Date(d));
  } catch { return "Recently"; }
};

const readTime = (html: string) => {
  const words = html.replace(/<[^>]*>/g, "").split(/\s+/).length;
  return Math.max(2, Math.ceil(words / 200));
};

export default function NewsDetail() {
  const [, params] = useRoute("/news/:idOrSlug");
  const [, setLocation] = useLocation();
  const idOrSlug = params?.idOrSlug;
  const [search, setSearch] = useState("");
  const [cat, setCat] = useState("All");

  const { scrollYProgress } = useScroll();
  const scaleX = useSpring(scrollYProgress, { stiffness: 100, damping: 30 });

  // Fetch article
  const { data: article, isLoading, error } = useQuery<NewsArticle>({
    queryKey: ["article", idOrSlug],
    queryFn: () => newsApi.getArticle(idOrSlug!),
    enabled: !!idOrSlug,
  });

  // Fetch related articles from same category
  const { data: related } = useQuery<ArticleListResponse>({
    queryKey: ["related", article?.category],
    queryFn: () => newsApi.getArticles({
      page_size: 5,
      category: article?.category || undefined,
    }),
    enabled: !!article?.category,
  });

  // Share data for this article
  const shareData = article ? {
    url: window.location.href,
    title: article ? getTitle(article) : '',
    summary: article ? getContent(article).replace(/<[^>]*>/g, '').slice(0, 200) : '',
  } : { url: '', title: '', summary: '' };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="w-12 h-12 border-4 border-[var(--pf-orange)] border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (error || !article) {
    return (
      <div className="min-h-screen bg-white">
        <PremiumHeader selectedCategory={cat} onCategoryChange={c => { setCat(c); setLocation(c === "All" ? "/" : `/news?category=${c}`); }} searchQuery={search} onSearchChange={setSearch} />
        <div className="flex flex-col items-center justify-center py-32 gap-4">
          <h2 className="text-2xl font-bold text-zinc-400">Article not found</h2>
          <Link href="/"><a className="text-[var(--pf-orange)] font-bold hover:underline">← Back to Home</a></Link>
        </div>
        <PremiumFooter />
      </div>
    );
  }

  const title = getTitle(article);
  const content = getContent(article);
  const minutes = readTime(content);

  return (
    <div className="min-h-screen bg-white text-zinc-900">
      <PremiumHeader
        selectedCategory={cat}
        onCategoryChange={c => { setCat(c); setLocation(c === "All" ? "/" : `/news?category=${c}`); }}
        searchQuery={search}
        onSearchChange={setSearch}
      />

      {/* Reading progress */}
      <motion.div
        className="fixed top-0 left-0 right-0 h-[3px] bg-gradient-to-r from-[var(--pf-orange)] to-[var(--pf-green)] z-[60] origin-left"
        style={{ scaleX }}
      />

      <main className="pt-6 pb-20">
        {/* ── Header ── */}
        <header className="max-w-4xl mx-auto px-6 mb-10">
          <Link href="/" className="inline-flex items-center gap-2 text-[10px] font-black uppercase tracking-[0.3em] text-zinc-400 hover:text-[var(--pf-orange)] transition-colors mb-6">
            <ArrowLeft className="w-3 h-3" /> Back to Newsroom
          </Link>

          {article.category && (
            <Link href={`/news?category=${article.category}`}>
              <span className="inline-block bg-zinc-900 text-white px-3 py-1 text-[10px] font-black uppercase tracking-[0.2em] mb-4 hover:bg-[var(--pf-orange)] transition-colors cursor-pointer">
                {article.category}
              </span>
            </Link>
          )}

          <h1 className="text-3xl md:text-5xl font-[900] leading-[0.95] tracking-tight text-zinc-950 mb-6">
            {title}
          </h1>

          <div className="pt-6 border-t border-zinc-100 flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <img src="/pf-logo.png" alt="PF" className="w-9 h-9 rounded-full object-contain bg-zinc-100 p-1" />
              <div>
                <p className="text-xs font-black uppercase tracking-widest text-zinc-900">
                  Peoples Feedback
                </p>
                <p className="text-[10px] font-bold text-zinc-400 uppercase tracking-widest">
                  {fmtDate(article.published_at)}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-5 text-[10px] font-black uppercase tracking-widest text-zinc-400">
              <span className="flex items-center gap-1">
                <Clock className="w-3 h-3" /> {minutes} min read
              </span>
              {article.submitted_by && (
                <span>By {article.submitted_by}</span>
              )}
            </div>
          </div>
        </header>

        {/* ── Featured Image ── */}
        <div className="max-w-5xl mx-auto px-4 mb-14">
          <div className="relative overflow-hidden bg-zinc-100 shadow-xl border-b-[3px] border-[var(--pf-orange)]">
            <img
                src={getImage(article)}
                alt=""
                className="w-full aspect-[21/9] max-h-[480px] object-cover"
                onError={handleImgError}
                data-category={article.category}
              />
          </div>
          <div className="mt-3 text-[9px] text-zinc-400 font-bold uppercase tracking-widest flex items-center gap-3 px-1">
            <div className="w-5 h-[2px] bg-[var(--pf-green)]" />
            Peoples Feedback Newsroom
          </div>
        </div>

        {/* ── Content + Sidebars ── */}
        <div className="max-w-6xl mx-auto px-6 grid grid-cols-1 lg:grid-cols-12 gap-14">

          {/* Social sidebar */}
          <aside className="hidden lg:block lg:col-span-1">
            <div className="sticky top-28 flex flex-col gap-2 items-center border-r border-zinc-50 py-4">
              <ShareMenu data={shareData} variant="vertical" />
              <div className="w-px h-4 bg-zinc-100 my-2" />
              <div className="text-[8px] font-black uppercase tracking-widest text-zinc-300 -rotate-90 whitespace-nowrap mt-6">Share</div>
            </div>
          </aside>

          {/* Article body */}
          <div className="lg:col-span-8">
            <article
              className="article-content prose prose-zinc max-w-none text-xl leading-[1.9] text-zinc-950"
              style={{ fontFamily: "var(--font-serif)" }}
              dangerouslySetInnerHTML={{ __html: content }}
            />

            {/* Tags */}
            {article.tags && article.tags.length > 0 && (
              <div className="mt-14 pt-6 border-t border-zinc-100 flex flex-wrap gap-2">
                {article.tags.map(tag => (
                  <Link key={tag} href={`/news?search=${encodeURIComponent(tag)}`}>
                    <span className="text-[10px] font-black uppercase tracking-[0.2em] px-4 py-2 bg-zinc-50 hover:bg-[var(--pf-orange)] hover:text-white transition-all cursor-pointer">
                      #{tag}
                    </span>
                  </Link>
                ))}
              </div>
            )}

            {/* Mobile share bar */}
            <div className="lg:hidden mt-8 py-4 border-t border-zinc-100">
              <div className="text-[10px] font-black uppercase tracking-[0.2em] text-zinc-400 mb-3">Share this article</div>
              <ShareBar data={shareData} className="justify-start gap-2" />
            </div>
          </div>

          {/* Info sidebar */}
          <aside className="lg:col-span-3 space-y-10">
            <div className="p-5 bg-zinc-50 border-t-2 border-zinc-900">
              <h4 className="text-[10px] font-black uppercase tracking-widest text-zinc-900 mb-5">About this article</h4>
              <div className="space-y-3 text-xs">
                <div className="flex gap-2">
                  <div className="w-1 h-auto bg-[var(--pf-green)] shrink-0" />
                  <p className="font-bold text-zinc-600">Publisher: Peoples Feedback</p>
                </div>
                <div className="flex gap-2">
                  <div className="w-1 h-auto bg-[var(--pf-orange)] shrink-0" />
                  <p className="font-bold text-zinc-600">Category: {article.category || "General"}</p>
                </div>
                {article.original_language && article.original_language !== "en" && (
                  <div className="flex gap-2">
                    <div className="w-1 h-auto bg-zinc-400 shrink-0" />
                    <p className="font-bold text-zinc-600">Original language: {article.original_language}</p>
                  </div>
                )}
                              </div>
            </div>

            {/* Ad placeholder */}
            <div className="aspect-[3/4] bg-zinc-50 flex items-center justify-center border border-zinc-200 rounded">
              <span className="text-[9px] font-bold text-zinc-300 uppercase tracking-widest">Ad Space</span>
            </div>
          </aside>
        </div>

        {/* ── Related Articles ── */}
        {related?.articles && related.articles.filter(a => a.id !== article.id).length > 0 && (
          <section className="mt-20 bg-zinc-950 py-20 text-white">
            <div className="max-w-6xl mx-auto px-6">
              <div className="flex items-center justify-between mb-10">
                <h2 className="text-2xl font-[900] uppercase tracking-tight">Continue Reading</h2>
                <Link href={`/news?category=${article.category}`} className="text-[10px] font-black uppercase tracking-widest text-[var(--pf-orange)] hover:text-white transition-colors flex items-center gap-1">
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
                        <div className="aspect-video bg-zinc-800 overflow-hidden">
                          <img
                            src={getImage(a)}
                            alt=""
                            className="w-full h-full object-cover grayscale group-hover:grayscale-0 group-hover:scale-110 transition-all duration-700"
                            loading="lazy"
                          />
                        </div>
                        <h3 className="text-base font-bold leading-tight group-hover:text-[var(--pf-orange)] transition-colors line-clamp-2">
                          {getTitle(a)}
                        </h3>
                        <span className="text-[10px] font-black uppercase tracking-widest text-zinc-500">
                          Peoples Feedback
                        </span>
                      </div>
                    </Link>
                  ))}
              </div>
            </div>
          </section>
        )}
      </main>

      <PremiumFooter />
    </div>
  );
}
