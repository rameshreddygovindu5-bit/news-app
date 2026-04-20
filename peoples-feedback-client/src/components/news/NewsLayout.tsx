/**
 * NewsLayout — Main article grid for Home and News pages.
 * Fixes:
 *   - Breaking ticker uses Indian flag navy (not purple)
 *   - Category section headers use saffron/navy (not purple gradient)
 *   - catGroups shows ALL categories (not just first 5)
 *   - HeroCard overlay uses saffron (not purple)
 *   - Proper image fallback with alt text
 */
import { useMemo } from "react";
import { Link } from "wouter";
import { useQuery } from "@tanstack/react-query";
import { TrendingUp, ArrowRight, Clock, Newspaper, Gift } from "lucide-react";
import { NewsArticle, getTitle, getSummary, getImage, categoryPlaceholder, WishItem } from "@/types/news";
import { ShareBar } from "@/components/news/ShareMenu";
import { PollWidget } from "@/components/news/PollWidget";
import { newsApi } from "@/lib/api";
import { motion } from "framer-motion";

const handleImgError = (e: React.SyntheticEvent<HTMLImageElement>) => {
  const el = e.currentTarget;
  if (!el.dataset.fallback) {
    el.dataset.fallback = "1";
    el.src = categoryPlaceholder(el.dataset.category);
  }
};

interface Props {
  articles:       NewsArticle[];
  isLoading?:     boolean;
  onLoadMore?:    () => void;
  hasMore?:       boolean;
  isLoadingMore?: boolean;
  selectedCategory?: string;
}

const timeAgo = (d?: string) => {
  if (!d) return "Just now";
  try {
    const mins = Math.floor((Date.now() - new Date(d).getTime()) / 60000);
    if (mins < 1)    return "Just now";
    if (mins < 60)   return `${mins}m ago`;
    if (mins < 1440) return `${Math.floor(mins / 60)}h ago`;
    if (mins < 10080)return `${Math.floor(mins / 1440)}d ago`;
    return new Intl.DateTimeFormat("en-IN", { month: "short", day: "numeric" }).format(new Date(d));
  } catch { return ""; }
};

/* ── Hero Card ───────────────────────────────────────────────────────── */
const HeroCard = ({ article }: { article: NewsArticle }) => (
  <Link href={`/news/${article.slug || article.id}`}>
    <div className="group cursor-pointer relative overflow-hidden bg-[var(--pf-navy)] rounded-2xl shadow-2xl transform transition-all duration-500 hover:scale-[1.015] hover:shadow-3xl">
      <div className="aspect-[16/9] sm:aspect-[21/9] md:aspect-[2.5/1] relative news-image-wrapper">
        <img
          src={getImage(article)}
          className="w-full h-full object-cover opacity-60 group-hover:opacity-70 group-hover:scale-[1.04] transition-all duration-700"
          alt={getTitle(article)}
          onError={handleImgError}
          data-category={article.category}
        />
        <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/40 to-transparent" />
        {/* Tricolor overlay for copyright differentiation */}
        <div className="absolute inset-0 bg-gradient-to-r from-[var(--pf-saffron)]/15 via-transparent to-[var(--pf-green)]/15 opacity-60 group-hover:opacity-80 transition-opacity duration-500" />
      </div>
        {/* Bottom text overlay */}
        <div className="absolute bottom-0 left-0 right-0 p-4 sm:p-6 md:p-10">
          <div className="flex items-center gap-3 mb-4">
            {article.category && (
              <span className="inline-block bg-[var(--pf-saffron)] text-white px-4 py-1.5 text-[11px] font-bold uppercase tracking-widest rounded-full shadow-lg">
                {article.category}
              </span>
            )}
            <span className="flex items-center gap-1.5 text-white/60 text-[11px] font-medium">
              <span className="w-2 h-2 bg-[var(--pf-green)] rounded-full animate-pulse" />
              Latest
            </span>
          </div>
          <h1
            className="text-2xl sm:text-3xl md:text-5xl font-black text-white leading-[1.1] tracking-tight mb-4 max-w-4xl group-hover:scale-[1.01] transition-transform duration-300"
            style={{ fontFamily: "var(--font-headline)" }}
          >
            {getTitle(article)}
          </h1>
          <p className="text-white/80 text-sm sm:text-lg line-clamp-2 max-w-3xl mb-4 leading-relaxed">
            {getSummary(article, 200)}
          </p>
          <div className="flex items-center justify-between">
            <span className="flex items-center gap-1.5 text-white/60 text-[11px] font-medium">
              <Clock className="w-3.5 h-3.5" /> {timeAgo(article.published_at)}
            </span>
            <span className="flex items-center gap-1.5 text-white/60 group-hover:text-white transition-colors text-[11px] font-medium uppercase tracking-wider">
              Read More <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
            </span>
          </div>
        </div>
      </div>
    </Link>
);

/* ── Article Card ────────────────────────────────────────────────────── */
const ArticleCard = ({ article, size = "md" }: { article: NewsArticle; size?: "lg" | "md" | "sm" }) => (
  <motion.div
    initial={{ opacity: 0, y: 15 }}
    whileInView={{ opacity: 1, y: 0 }}
    viewport={{ once: true }}
    whileHover={{ y: -6 }}
    className="h-full"
  >
    <Link href={`/news/${article.slug || article.id}`}>
      <div className="group cursor-pointer h-full bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden hover:shadow-xl hover:border-[var(--pf-saffron)]/30 transition-all duration-300">
        {size !== "sm" && (
          <div className="aspect-video relative overflow-hidden news-image-wrapper">
            <img
              src={getImage(article)}
              className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-600"
              alt={getTitle(article)}
              onError={handleImgError}
              data-category={article.category}
            />
            <div className="absolute inset-0 bg-gradient-to-t from-black/50 via-transparent to-transparent opacity-60 group-hover:opacity-80 transition-opacity" />
            {article.category && (
              <span className="absolute top-3 left-3 bg-white/90 backdrop-blur-sm text-[var(--pf-navy)] px-3 py-1 text-[9px] font-black uppercase tracking-widest rounded-full shadow-sm">
                {article.category}
              </span>
            )}
            {article.rank_score > 80 && (
              <div className="absolute top-3 right-3 w-2 h-2 bg-[var(--pf-saffron)] rounded-full">
                <div className="absolute inset-0 rounded-full bg-[var(--pf-saffron)] animate-ping" />
              </div>
            )}
          </div>
        )}
        <div className="p-3 sm:p-5 flex flex-col h-fit">
          {size === "sm" && article.category && (
            <span className="inline-block bg-[var(--pf-saffron)] text-white px-3 py-1 text-[9px] font-black uppercase tracking-widest rounded-full mb-3 w-fit">
              {article.category}
            </span>
          )}
          <h3
            className={`font-black text-zinc-900 mb-3 group-hover:text-[var(--pf-saffron)] transition-colors leading-tight ${
              size === "lg" ? "text-xl" : size === "md" ? "text-lg" : "text-base"
            }`}
            style={{ fontFamily: "var(--font-headline)" }}
          >
            {getTitle(article)}
          </h3>
          <p className={`text-zinc-500 leading-relaxed mb-4 line-clamp-3 ${size === "lg" ? "text-sm" : "text-xs"}`}>
            {getSummary(article, 150)}
          </p>
          <div className="mt-auto pt-4 border-t border-gray-100 flex items-center justify-between">
            <span className="text-[9px] font-bold uppercase tracking-widest text-zinc-400">
              {timeAgo(article.published_at)}
            </span>
            <div className="w-7 h-7 rounded-full bg-zinc-50 flex items-center justify-center group-hover:bg-[var(--pf-saffron)] group-hover:text-white transition-all">
              <ArrowRight className="w-3.5 h-3.5" />
            </div>
          </div>
        </div>
      </div>
    </Link>
  </motion.div>
);

/* ── Ranked Item ─────────────────────────────────────────────────────── */
const RankedItem = ({ article, rank }: { article: NewsArticle; rank: number }) => (
  <Link href={`/news/${article.slug || article.id}`}>
    <div className="group cursor-pointer flex gap-4 py-4 border-b border-gray-100 last:border-0 hover:bg-[var(--pf-saffron)]/5 transition-colors rounded-lg px-2">
      <span
        className="text-3xl font-black text-zinc-300 group-hover:text-[var(--pf-saffron)] transition-colors w-8 shrink-0 leading-none"
        style={{ fontFamily: "var(--font-headline)" }}
      >
        {rank}
      </span>
      <div className="min-w-0 flex-1">
        <h4 className="font-bold text-zinc-900 text-sm leading-snug group-hover:text-[var(--pf-saffron)] transition-colors line-clamp-2">
          {getTitle(article)}
        </h4>
        <div className="flex items-center gap-2 mt-1.5 text-[10px] text-zinc-400 font-medium">
          {article.category && (
            <>
              <span className="w-1.5 h-1.5 bg-[var(--pf-green)] rounded-full" />
              <span>{article.category}</span>
              <span>·</span>
            </>
          )}
          <span>{timeAgo(article.published_at)}</span>
        </div>
      </div>
    </div>
  </Link>
);

/* ── Skeleton ─────────────────────────────────────────────────────────── */
const SkeletonLayout = () => (
  <div className="max-w-7xl mx-auto px-4 space-y-8">
    <div className="skeleton h-[400px] w-full rounded-2xl" />
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
      {[1,2,3,4].map(i => (
        <div key={i} className="space-y-3">
          <div className="skeleton h-40 rounded-xl" />
          <div className="skeleton h-4 rounded w-4/5" />
          <div className="skeleton h-3 rounded w-3/5" />
        </div>
      ))}
    </div>
  </div>
);

/* ── Wishes Sidebar Widget ────────────────────────────────────────────── */
function WishesSidebar() {
  const { data: wishes } = useQuery<WishItem[]>({
    queryKey: ["home-wishes"],
    queryFn: () => newsApi.getHomeWishes(),
    staleTime: 5 * 60 * 1000,
  });

  if (!wishes?.length) return null;

  return (
    <div className="bg-gradient-to-br from-pink-50 to-rose-50 rounded-xl p-5 border border-pink-100">
      <h3 className="flex items-center gap-2 text-xs font-black uppercase tracking-wider text-rose-600 mb-4 pb-3 border-b border-pink-200">
        <Gift className="w-4 h-4" /> Wishes & Greetings
      </h3>
      <div className="space-y-3">
        {wishes.slice(0, 3).map(w => (
          <div key={w.id} className="flex gap-3 items-start">
            {w.image_url ? (
              <img src={w.image_url} alt="" className="w-12 h-12 rounded-lg object-cover shrink-0 border border-pink-200" />
            ) : (
              <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-pink-400 to-rose-400 flex items-center justify-center shrink-0">
                <Gift className="w-5 h-5 text-white" />
              </div>
            )}
            <div className="min-w-0">
              <p className="text-sm font-bold text-zinc-800 line-clamp-2 leading-snug">{w.title}</p>
              {w.person_name && <p className="text-[10px] text-rose-500 font-medium mt-0.5">{w.person_name}</p>}
            </div>
          </div>
        ))}
      </div>
      <Link href="/wishes" className="flex items-center justify-center gap-1.5 mt-4 pt-3 border-t border-pink-200 text-[11px] font-bold uppercase tracking-wider text-rose-600 hover:text-rose-800 transition-colors">
        View All <ArrowRight className="w-3 h-3" />
      </Link>
    </div>
  );
}

/* ── Main Layout ─────────────────────────────────────────────────────── */
export function NewsLayout({ articles, isLoading, onLoadMore, hasMore, isLoadingMore, selectedCategory }: Props) {
  const { featured, secondary, catGroups, allSorted } = useMemo(() => {
    if (!articles?.length) return { featured: null, secondary: [], catGroups: {} as Record<string, NewsArticle[]>, allSorted: [] };
    // Sort by recency first (newest on top), rank_score as tiebreaker
    const sorted = [...articles].sort(
      (a, b) => new Date(b.published_at || b.created_at || 0).getTime() - new Date(a.published_at || a.created_at || 0).getTime()
        || (b.rank_score || 0) - (a.rank_score || 0)
    );
    const safe = sorted.filter(a => a.original_title);
    const groups: Record<string, NewsArticle[]> = {};
    // FIX: Show ALL categories, not just first 5
    safe.slice(5).forEach(a => {
      let c = a.category || "General News";
      if (c === "Home") c = "Latest Updates";
      (groups[c] ??= []).push(a);
    });
    return { featured: safe[0], secondary: safe.slice(1, 5), catGroups: groups, allSorted: safe };
  }, [articles]);

  if (isLoading && !articles?.length) return <SkeletonLayout />;

  // If no articles, show empty state
  if (!articles || articles.length === 0) {
    return (
      <div className="max-w-7xl mx-auto px-4 pb-16">
        <div className="text-center py-20">
          <div className="tricolor-stripe rounded-full w-24 mx-auto mb-6" />
          <h2 className="text-3xl md:text-4xl font-black uppercase tracking-tight text-zinc-900 mb-4" style={{ fontFamily: 'var(--font-headline)' }}>
            No Articles Available
          </h2>
          <p className="text-zinc-600 max-w-md mx-auto">
            We're working on bringing you the latest news. Please check back later.
          </p>
        </div>
      </div>
    );
  }

  if (selectedCategory === "Surveys") {
    return (
      <div className="max-w-7xl mx-auto px-4 pb-16">
        <div className="bg-white rounded-2xl shadow-xl overflow-hidden border border-gray-100">
          <div className="bg-[var(--pf-navy)] p-6 text-white flex items-center justify-between">
            <div>
              <h2 className="text-2xl font-black uppercase tracking-tight">Survey Reports & Results</h2>
              <p className="text-white/70 text-sm mt-1">Structured data from community feedback and public polls.</p>
            </div>
            <div className="flex gap-2">
              <div className="w-2 h-2 rounded-full bg-[var(--pf-saffron)]" />
              <div className="w-2 h-2 rounded-full bg-white" />
              <div className="w-2 h-2 rounded-full bg-[var(--pf-green)]" />
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-200">
                  <th className="px-6 py-4 text-[10px] font-black uppercase tracking-widest text-zinc-400">Date</th>
                  <th className="px-6 py-4 text-[10px] font-black uppercase tracking-widest text-zinc-400">Topic / Survey Title</th>
                  <th className="px-6 py-4 text-[10px] font-black uppercase tracking-widest text-zinc-400">Category</th>
                  <th className="px-6 py-4 text-[10px] font-black uppercase tracking-widest text-zinc-400">Status</th>
                  <th className="px-6 py-4 text-[10px] font-black uppercase tracking-widest text-zinc-400">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {articles.map((a, i) => (
                  <tr key={a.id} className="hover:bg-zinc-50 transition-colors group">
                    <td className="px-6 py-4 text-xs font-bold text-zinc-400">
                      {new Date(a.published_at!).toLocaleDateString('en-IN', { day: '2-digit', month: 'short' })}
                    </td>
                    <td className="px-6 py-4">
                      <Link href={`/news/${a.slug || a.id}`}>
                        <span className="font-black text-zinc-800 group-hover:text-[var(--pf-saffron)] transition-colors cursor-pointer">
                          {getTitle(a)}
                        </span>
                      </Link>
                    </td>
                    <td className="px-6 py-4">
                      <span className="px-2 py-1 bg-zinc-100 text-[10px] font-black uppercase tracking-tighter text-zinc-500 rounded-sm">
                        {a.category || "Survey"}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <span className="flex items-center gap-1.5 text-green-600 text-[10px] font-bold uppercase">
                        <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
                        Completed
                      </span>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <Link href={`/news/${a.slug || a.id}`}>
                        <button className="px-4 py-1.5 border border-[var(--pf-navy)] text-[var(--pf-navy)] text-[10px] font-black uppercase tracking-widest rounded-full hover:bg-[var(--pf-navy)] hover:text-white transition-all">
                          View Results
                        </button>
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    );
  }

  if (selectedCategory === "Polls") {
    return (
      <div className="max-w-4xl mx-auto px-4 pb-16">
        <div className="text-center mb-10">
          <div className="tricolor-stripe rounded-full w-24 mx-auto mb-4" />
          <h2 className="text-3xl md:text-5xl font-black uppercase tracking-tight text-zinc-900" style={{ fontFamily: 'var(--font-headline)' }}>
            People's Voice Polls
          </h2>
          <p className="text-zinc-500 mt-3 font-medium">Shape the news with your opinion. Real-time community feedback.</p>
        </div>
        <PollWidget />
      </div>
    );
  }

  if (!featured) return (
    <div className="text-center py-24 max-w-md mx-auto">
      <Newspaper className="w-14 h-14 text-zinc-200 mx-auto mb-4" />
      <h3 className="text-lg font-bold text-zinc-400 mb-1">No articles available</h3>
      <p className="text-zinc-300 text-sm">Check back soon for the latest news.</p>
    </div>
  );

  const tickerItems = allSorted.slice(0, 10);

  return (
    <div className="max-w-7xl mx-auto px-4 pb-16">
      {/* ── Breaking News Ticker (Indian flag navy) ── */}
      <div className="flex items-center bg-[var(--pf-navy)] text-white h-10 mb-8 overflow-hidden rounded-xl shadow-lg">
        <div className="bg-[var(--pf-red)] px-5 h-full flex items-center font-bold text-[11px] uppercase tracking-wider shrink-0 gap-2">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-white opacity-75" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-white" />
          </span>
          Breaking
        </div>
        <div className="flex-1 overflow-hidden">
          <div className="flex animate-marquee whitespace-nowrap items-center">
            {[...tickerItems, ...tickerItems].map((a, i) => (
              <Link key={`${a.id}-${i}`} href={`/news/${a.slug || a.id}`}>
                <span className="text-[12px] font-medium px-5 hover:text-[var(--pf-saffron)] cursor-pointer border-r border-white/20 transition-colors">
                  {getTitle(a)}
                </span>
              </Link>
            ))}
          </div>
        </div>
      </div>
      
      {/* ── Hero ── */}
      <section className="mb-10">
        <HeroCard article={featured} />
      </section>

      {/* ── Secondary grid ── */}
      {secondary.length > 0 && (
        <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5 mb-14">
          {secondary.map((a, i) => (
            <motion.div
              key={a.id}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.08 }}
            >
              <ArticleCard article={a} size="md" />
            </motion.div>
          ))}
        </section>
      )}

      {/* ── Category sections + sidebar ── */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-10">
        {/* Category sections — FIX: ALL categories shown */}
        <div className="lg:col-span-3 space-y-14">
          {Object.entries(catGroups).map(([cat, items], idx) => (
            <motion.section
              key={cat}
              initial={{ opacity: 0, y: 24 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: idx * 0.05 }}
            >
              {/* Section header — Indian flag saffron/navy (not purple) */}
              <div className="flex items-center justify-between mb-6 pb-3 border-b-2 border-[var(--pf-navy)]">
                <div className="flex items-center gap-3">
                  <div className="w-1 h-8 bg-[var(--pf-saffron)] rounded-full" />
                  <h2
                    className="text-2xl font-black uppercase tracking-tight text-[var(--pf-navy)]"
                    style={{ fontFamily: "var(--font-headline)" }}
                  >
                    {cat === "Home" ? "Fresh News" : cat}
                  </h2>
                </div>
                <Link
                  href={cat === "Home" || cat === "Latest Updates" ? "/news" : `/news?category=${cat}`}
                  className="flex items-center gap-1.5 bg-[var(--pf-navy)] text-white px-5 py-2 rounded-lg font-bold text-[11px] uppercase tracking-wider hover:bg-[var(--pf-saffron)] transition-colors"
                >
                  See All <ArrowRight className="w-3.5 h-3.5" />
                </Link>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {items[0] && (
                  <div className="md:col-span-1">
                    <ArticleCard article={items[0]} size="lg" />
                  </div>
                )}
                <div className="md:col-span-2 divide-y divide-gray-100">
                  {items.slice(1, 5).map((a, i) => (
                    <RankedItem key={a.id} article={a} rank={i + 1} />
                  ))}
                </div>
              </div>
            </motion.section>
          ))}

          {/* Load More - removed from here, moved below grid */}
        </div>

        {/* Sidebar */}
        <aside className="lg:col-span-1">
          <div className="sticky top-20 space-y-6">
            {/* Most Read */}
            <div className="bg-white rounded-xl p-5 border border-gray-100 shadow-sm">
              <h3 className="flex items-center gap-2 text-xs font-black uppercase tracking-wider text-[var(--pf-navy)] mb-4 pb-3 border-b-2 border-[var(--pf-saffron)]">
                <TrendingUp className="w-4 h-4 text-[var(--pf-red)]" /> Most Read
              </h3>
              {allSorted.slice(0, 7).map((a, i) => (
                <RankedItem key={a.id} article={a} rank={i + 1} />
              ))}
            </div>

            {/* Newsletter */}
            <div className="bg-[var(--pf-navy)] rounded-xl p-5 text-white">
              <h4 className="font-black uppercase tracking-wider text-xs mb-2">Daily Brief</h4>
              <p className="text-sm mb-4 text-white/80">Top stories delivered every morning.</p>
              <input
                className="w-full bg-white/10 border border-white/20 px-3 py-2 text-xs rounded-lg mb-2 placeholder:text-white/40 focus:outline-none focus:ring-2 focus:ring-[var(--pf-saffron)]/50 text-white"
                placeholder="your@email.com"
              />
              <button className="w-full bg-[var(--pf-saffron)] text-white py-2 text-[11px] font-bold uppercase tracking-wider rounded-lg hover:bg-[var(--pf-orange)] transition-colors">
                Subscribe
              </button>
            </div>


            {/* Wishes & Greetings */}
            <WishesSidebar />
          </div>
        </aside>
      </div>

      {/* FIX 2: Load More — moved OUTSIDE grid so it's always visible */}
      {hasMore && onLoadMore && (
        <div className="flex justify-center pt-10 pb-4">
          <button
            type="button"
            onClick={() => { onLoadMore(); }}
            disabled={isLoadingMore}
            className="px-10 py-3.5 border-2 border-[var(--pf-navy)] text-[var(--pf-navy)] font-black text-sm uppercase tracking-wider rounded-full hover:bg-[var(--pf-navy)] hover:text-white transition-all disabled:opacity-50 active:scale-95"
          >
            {isLoadingMore ? (
              <span className="flex items-center gap-2">
                <span className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
                Loading…
              </span>
            ) : "Load More Headlines"}
          </button>
        </div>
      )}
    </div>
  );
}
