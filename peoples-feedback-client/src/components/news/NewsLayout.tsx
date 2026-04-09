import { useMemo } from "react";
import { Link } from "wouter";
import { Button } from "@/components/ui/button";
import { TrendingUp, ArrowRight, Clock, Newspaper } from "lucide-react";
import { NewsArticle, getTitle, getSummary, getImage, categoryPlaceholder } from "@/types/news";
import { ShareBar } from "@/components/news/ShareMenu";

/** Handle broken images — fall back to category placeholder */
const handleImgError = (e: React.SyntheticEvent<HTMLImageElement>) => {
  const el = e.currentTarget;
  if (!el.dataset.fallback) {
    el.dataset.fallback = "1";
    el.src = categoryPlaceholder(el.dataset.category || 'news');
  }
};
import { motion } from "framer-motion";

interface Props {
  articles: NewsArticle[];
  isLoading?: boolean;
  onLoadMore?: () => void;
  hasMore?: boolean;
  isLoadingMore?: boolean;
  selectedCategory?: string;
}

const timeAgo = (d?: string) => {
  if (!d) return 'Just now';
  try {
    const mins = Math.floor((Date.now() - new Date(d).getTime()) / 60000);
    if (mins < 1) return 'Just now';
    if (mins < 60) return `${mins}m ago`;
    if (mins < 1440) return `${Math.floor(mins / 60)}h ago`;
    if (mins < 10080) return `${Math.floor(mins / 1440)}d ago`;
    return new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric' }).format(new Date(d));
  } catch { return ''; }
};

/* ── Hero Card — Enhanced dramatic design ── */
const HeroCard = ({ article }: { article: NewsArticle }) => (
  <Link href={`/news/${article.slug || article.id}`}>
    <div className="group cursor-pointer relative overflow-hidden bg-gradient-to-br from-gray-900 to-black rounded-2xl shadow-2xl transform transition-all duration-500 hover:scale-[1.02] hover:shadow-3xl">
      <div className="aspect-[21/9] md:aspect-[2.5/1] relative">
        {article.image_url && article.image_url.trim() !== '' ? (
          <>
            <img src={getImage(article)} className="w-full h-full object-cover opacity-60 group-hover:opacity-70 group-hover:scale-[1.05] transition-all duration-700" alt="" onError={handleImgError} data-category={article.category} />
            <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/40 to-transparent"></div>
            {/* Animated overlay */}
            <div className="absolute inset-0 bg-gradient-to-r from-[var(--pf-orange)]/20 via-transparent to-[var(--pf-purple)]/20 opacity-0 group-hover:opacity-100 transition-opacity duration-500"></div>
          </>
        ) : (
          <div className="w-full h-full bg-gradient-to-br from-[var(--pf-navy)] via-[var(--pf-blue)] to-[var(--pf-purple)] flex items-center justify-center p-8">
            <div className="text-center">
              <h3 className="text-2xl md:text-4xl font-black text-white mb-4 leading-tight" style={{ fontFamily: 'var(--font-headline)' }}>
                {getTitle(article)}
              </h3>
              <p className="text-white/80 text-sm md:text-base line-clamp-4 leading-relaxed max-w-2xl mx-auto">
                {getSummary(article, 150)}
              </p>
            </div>
          </div>
        )}
      <div className="absolute bottom-0 left-0 right-0 p-6 md:p-10">
        <div className="flex items-center gap-3 mb-4">
          {article.category && (
            <span className="inline-block bg-gradient-to-r from-[var(--pf-orange)] to-[var(--pf-pink)] text-white px-4 py-2 text-[11px] font-bold uppercase tracking-widest rounded-full shadow-lg">
              {article.category}
            </span>
          )}
          <span className="flex items-center gap-2 text-white/60 text-[11px] font-medium">
            <span className="w-2 h-2 bg-[var(--pf-green)] rounded-full animate-pulse"></span>
            Latest News
          </span>
        </div>
        <h1 className="text-3xl md:text-5xl lg:text-6xl font-black text-white leading-[1.1] tracking-tight mb-4 max-w-4xl transform transition-all duration-300 group-hover:scale-105" style={{ fontFamily: 'var(--font-headline)' }}>
          {getTitle(article)}
        </h1>
        <p className="text-white/80 text-lg md:text-xl line-clamp-3 max-w-3xl mb-4 leading-relaxed" style={{ fontFamily: 'var(--font-serif)' }}>
          {getSummary(article, 200)}
        </p>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4 text-white/60 text-[12px] font-medium">
            <span className="flex items-center gap-1">
              <Clock className="w-4 h-4" />
              {timeAgo(article.published_at)}
            </span>
          </div>
          <div className="flex items-center gap-2 text-white/40 group-hover:text-white transition-colors duration-300">
            <span className="text-[11px] font-medium uppercase tracking-wider">Read More</span>
            <ArrowRight className="w-4 h-4 transform group-hover:translate-x-1 transition-transform duration-300" />
          </div>
        </div>
      </div>
    </div>
    </div>
  </Link>
);

/* ── Article Card — Enhanced modern design ── */
const ArticleCard = ({ article, size = 'md' }: { article: NewsArticle; size?: 'lg' | 'md' | 'sm' }) => (
  <motion.div initial={{ opacity: 0, y: 8 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }}>
    <Link href={`/news/${article.slug || article.id}`}>
      <div className="group cursor-pointer bg-white rounded-xl shadow-lg border border-gray-100 overflow-hidden transform transition-all duration-300 hover:scale-[1.02] hover:shadow-xl hover:border-[var(--pf-orange)]/50">
        {size !== 'sm' && (
          <div className="aspect-video relative overflow-hidden">
            {article.image_url && article.image_url.trim() !== '' ? (
              <>
                <img src={getImage(article)} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" alt="" onError={handleImgError} data-category={article.category} />
                <div className="absolute inset-0 bg-gradient-to-t from-black/30 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
              </>
            ) : (
              <div className="w-full h-full bg-gradient-to-br from-[var(--pf-orange)]/20 via-[var(--pf-blue)]/20 to-[var(--pf-purple)]/20 flex items-center justify-center p-6">
                <div className="text-center">
                  <h4 className="text-lg md:text-xl font-black text-white mb-2 leading-tight" style={{ fontFamily: 'var(--font-headline)' }}>
                    {getTitle(article)}
                  </h4>
                  <p className="text-white/80 text-sm md:text-base line-clamp-3 leading-relaxed max-w-md mx-auto">
                    {getSummary(article, 100)}
                  </p>
                </div>
              </div>
            )}
            {article.category && (
              <span className="absolute top-4 left-4 bg-gradient-to-r from-[var(--pf-orange)] to-[var(--pf-pink)] text-white px-3 py-1 text-[10px] font-bold uppercase tracking-wider rounded-full shadow-lg">
                {article.category}
              </span>
            )}
          </div>
        )}
        <div className="p-5">
          {size === 'sm' && article.category && (
            <span className="inline-block bg-gradient-to-r from-[var(--pf-orange)] to-[var(--pf-pink)] text-white px-2 py-1 text-[9px] font-bold uppercase tracking-wider rounded-full mb-3">
              {article.category}
            </span>
          )}
          <h3 className={`font-black leading-tight mb-3 group-hover:text-transparent group-hover:bg-gradient-to-r group-hover:from-[var(--pf-orange)] group-hover:to-[var(--pf-pink)] group-hover:bg-clip-text transition-all duration-300 ${size === 'lg' ? 'text-2xl' : size === 'md' ? 'text-xl' : 'text-lg'}`} style={{ fontFamily: 'var(--font-headline)' }}>
            {getTitle(article)}
          </h3>
          <p className={`text-gray-600 leading-relaxed mb-4 line-clamp-3 ${size === 'lg' ? 'text-base' : 'text-sm'}`} style={{ fontFamily: 'var(--font-serif)' }}>
            {getSummary(article, 150)}
          </p>
          <div className="flex items-center justify-between text-gray-500">
            <div className="flex items-center gap-3 text-[11px] font-medium">
              <span className="flex items-center gap-1">
                <Clock className="w-3 h-3" />
                {timeAgo(article.published_at)}
              </span>
            </div>
            <div className="flex items-center gap-1 text-[var(--pf-orange)] opacity-0 group-hover:opacity-100 transition-opacity duration-300">
              <ArrowRight className="w-4 h-4" />
            </div>
          </div>
        </div>
      </div>
    </Link>
  </motion.div>
);

/* ── Ranked Item — Enhanced trending design ── */
const RankedItem = ({ article, rank }: { article: NewsArticle; rank: number }) => (
  <Link href={`/news/${article.slug || article.id}`}>
    <div className="group cursor-pointer flex gap-4 py-4 border-b border-gray-100 last:border-0 hover:bg-gradient-to-r hover:from-[var(--pf-orange)]/5 hover:to-[var(--pf-pink)]/5 transition-all duration-300 rounded-lg px-3">
      <div className="relative">
        <span className="text-3xl font-black text-transparent bg-gradient-to-b from-gray-300 to-gray-500 group-hover:from-[var(--pf-orange)] group-hover:to-[var(--pf-pink)] group-hover:bg-clip-text transition-all duration-300 w-10 shrink-0 leading-none" style={{ fontFamily: 'var(--font-headline)' }}>
          {rank}
        </span>
        <div className="absolute -inset-1 bg-gradient-to-r from-[var(--pf-orange)]/20 to-[var(--pf-pink)]/20 rounded-full opacity-0 group-hover:opacity-100 transition-opacity duration-300 blur-sm"></div>
      </div>
      <div className="min-w-0 flex-1">
        <h4 className="font-bold text-gray-900 text-sm leading-snug group-hover:text-transparent group-hover:bg-gradient-to-r group-hover:from-[var(--pf-orange)] group-hover:to-[var(--pf-pink)] group-hover:bg-clip-text transition-all duration-300 line-clamp-2">
          {getTitle(article)}
        </h4>
        <div className="flex items-center gap-3 mt-2 text-[10px] text-gray-500 font-medium">
          <span className="flex items-center gap-1">
            <span className="w-1.5 h-1.5 bg-[var(--pf-green)] rounded-full"></span>
            {article.category}
          </span>
          <span>·</span>
          <span>{timeAgo(article.published_at)}</span>
        </div>
      </div>
    </div>
  </Link>
);

/* ── Main Layout ── */
export function NewsLayout({ articles, isLoading, onLoadMore, hasMore, isLoadingMore }: Props) {
  const { featured, secondary, catGroups, allSorted } = useMemo(() => {
    if (!articles?.length) return { featured: null, secondary: [], catGroups: {} as Record<string, NewsArticle[]>, latest: [], allSorted: [] };
    const sorted = [...articles].sort((a, b) => (b.rank_score || 0) - (a.rank_score || 0) || new Date(b.published_at || 0).getTime() - new Date(a.published_at || 0).getTime());
    const safe = sorted.filter(a => a.original_title);
    const groups: Record<string, NewsArticle[]> = {};
    safe.slice(5).forEach(a => { const c = a.category || 'General'; (groups[c] ??= []).push(a); });
    return { featured: safe[0], secondary: safe.slice(1, 5), catGroups: groups, latest: safe.slice(16), allSorted: safe };
  }, [articles]);

  if (isLoading) return (
    <div className="max-w-7xl mx-auto px-4 space-y-8 animate-pulse">
      <div className="h-[400px] bg-zinc-100 rounded-xl" />
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">{[1,2,3,4].map(i => <div key={i} className="space-y-3"><div className="h-44 bg-zinc-100 rounded-lg" /><div className="h-4 bg-zinc-100 w-3/4 rounded" /></div>)}</div>
    </div>
  );

  if (!featured) return (
    <div className="text-center py-24 max-w-md mx-auto">
      <Newspaper className="w-14 h-14 text-zinc-200 mx-auto mb-4" />
      <h3 className="text-lg font-bold text-zinc-400 mb-1">No articles available</h3>
      <p className="text-zinc-400 text-sm">Check back soon for the latest news.</p>
    </div>
  );

  const tickerItems = allSorted.slice(0, 8);

  return (
    <div className="max-w-7xl mx-auto px-4 pb-16">
      {/* ── Breaking ticker — enhanced design ── */}
      <div className="flex items-center bg-gradient-to-r from-[var(--pf-navy)] via-[var(--pf-blue)] to-[var(--pf-purple)] text-white h-10 mb-8 overflow-hidden rounded-xl shadow-lg">
        <div className="bg-gradient-to-r from-[var(--pf-red)] to-[var(--pf-pink)] px-6 h-full flex items-center font-bold text-[11px] uppercase tracking-wider shrink-0 gap-2">
          <span className="relative flex h-2 w-2"><span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-white opacity-75" /><span className="relative inline-flex rounded-full h-2 w-2 bg-white" /></span>
          Breaking News
        </div>
        <div className="flex-1 overflow-hidden">
          <div className="flex animate-marquee whitespace-nowrap items-center">
            {[...tickerItems, ...tickerItems].map((a, i) => (
              <Link key={`${a.id}-${i}`} href={`/news/${a.slug || a.id}`}>
                <span className="text-[12px] font-medium px-6 hover:text-transparent hover:bg-gradient-to-r hover:from-[var(--pf-orange)] hover:to-[var(--pf-pink)] hover:bg-clip-text cursor-pointer border-r border-white/20 transition-all duration-300">
                  {getTitle(a)}
                </span>
              </Link>
            ))}
          </div>
        </div>
      </div>

      {/* ── Hero section with enhanced background ── */}
      <section className="mb-12 relative">
        <div className="absolute inset-0 bg-gradient-to-r from-[var(--pf-orange)]/5 via-transparent to-[var(--pf-purple)]/5 rounded-3xl"></div>
        <HeroCard article={featured} />
      </section>

      {/* ── Secondary grid — enhanced cards ── */}
      <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-16">
        {secondary.map((a, index) => (
          <motion.div
            key={a.id}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: index * 0.1 }}
          >
            <ArticleCard article={a} size="md" />
          </motion.div>
        ))}
      </section>

      {/* ── Category sections with enhanced design ── */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-12">
        <div className="lg:col-span-3 space-y-16">
          {Object.entries(catGroups).slice(0, 5).map(([cat, items], catIndex) => (
            <motion.section
              key={cat}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: catIndex * 0.1 }}
              className="relative"
            >
              <div className="absolute inset-0 bg-gradient-to-r from-transparent via-gray-50 to-transparent -z-10 rounded-2xl"></div>
              <div className="flex items-center justify-between mb-8 p-6">
                <div>
                  <h2 className="text-2xl md:text-3xl font-black uppercase tracking-tight text-transparent bg-gradient-to-r from-[var(--pf-navy)] via-[var(--pf-blue)] to-[var(--pf-purple)] bg-clip-text" style={{ fontFamily: 'var(--font-headline)' }}>
                    {cat}
                  </h2>
                  <p className="text-gray-600 text-sm mt-1">Latest stories and updates</p>
                </div>
                <Link href={`/news?category=${cat}`} className="group bg-gradient-to-r from-[var(--pf-orange)] to-[var(--pf-pink)] text-white px-6 py-3 rounded-xl font-bold text-[11px] uppercase tracking-wider shadow-lg hover:shadow-xl transform hover:scale-105 transition-all duration-300 flex items-center gap-2">
                  See All
                  <ArrowRight className="w-4 h-4 transform group-hover:translate-x-1 transition-transform duration-300" />
                </Link>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-8 px-6 pb-6">
                {items[0] && <div className="md:col-span-1"><ArticleCard article={items[0]} size="lg" /></div>}
                <div className="md:col-span-2 space-y-0">
                  {items.slice(1, 5).map((a, idx) => <RankedItem key={a.id} article={a} rank={idx + 1} />)}
                </div>
              </div>
            </motion.section>
          ))}

          {hasMore && (
            <div className="flex justify-center pt-8">
              <Button variant="outline" onClick={onLoadMore}
                className="rounded-full px-10 h-11 border-zinc-300 text-zinc-700 font-bold text-sm hover:bg-zinc-900 hover:text-white hover:border-zinc-900 transition-all">
                {isLoadingMore ? "Loading..." : "Load More Headlines"}
              </Button>
            </div>
          )}
        </div>

        {/* ── Sidebar ── */}
        <aside className="lg:col-span-1">
          <div className="sticky top-20 space-y-8">
            <div className="bg-zinc-50 rounded-xl p-5 border border-zinc-100">
              <h3 className="flex items-center gap-2 text-xs font-extrabold uppercase tracking-wider text-zinc-900 mb-5 pb-3 border-b border-zinc-200">
                <TrendingUp className="w-4 h-4 text-[var(--pf-red)]" /> Most Read
              </h3>
              {allSorted.slice(0, 6).map((a, i) => <RankedItem key={a.id} article={a} rank={i + 1} />)}
            </div>

            <div className="bg-gradient-to-br from-[var(--pf-orange)] to-orange-600 rounded-xl p-6 text-white">
              <h4 className="font-black uppercase tracking-wider text-xs mb-2" style={{ fontFamily: 'var(--font-headline)' }}>Daily Brief</h4>
              <p className="text-sm mb-4 opacity-90" style={{ fontFamily: 'var(--font-serif)' }}>The most important stories, every morning.</p>
              <input className="w-full bg-white/15 border border-white/20 px-3 py-2 text-xs rounded-lg mb-2 placeholder:text-white/50 focus:outline-none focus:ring-2 focus:ring-white/30" placeholder="Enter email" />
              <button className="w-full bg-white text-[var(--pf-orange)] py-2 text-[11px] font-extrabold uppercase tracking-wider rounded-lg hover:bg-zinc-100 transition-colors">Subscribe</button>
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}
