/**
 * Wishes Page — /wishes
 * Displays birthday greetings, festival wishes, special occasions.
 * Users can view all active wishes with images.
 */
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Gift, Calendar, Heart, Star, PartyPopper } from "lucide-react";
import { PremiumHeader } from "@/components/news/PremiumHeader";
import { PremiumFooter } from "@/components/news/PremiumFooter";
import { BackToTop } from "@/components/news/BackToTop";
import { newsApi } from "@/lib/api";
import type { WishItem } from "@/types/news";

const WISH_TYPES = [
  { key: "all", label: "All", icon: Star },
  { key: "birthday", label: "Birthday", icon: Gift },
  { key: "festival", label: "Festival", icon: PartyPopper },
  { key: "anniversary", label: "Anniversary", icon: Heart },
  { key: "custom", label: "Special", icon: Calendar },
];

const typeColors: Record<string, string> = {
  birthday: "from-pink-500 to-rose-500",
  festival: "from-amber-500 to-orange-500",
  anniversary: "from-red-500 to-pink-500",
  custom: "from-indigo-500 to-purple-500",
};

function WishCard({ wish }: { wish: WishItem }) {
  const gradient = typeColors[wish.wish_type] || "from-[var(--pf-saffron)] to-[var(--pf-orange)]";
  const fmtDate = (d?: string) => {
    if (!d) return "";
    try {
      return new Intl.DateTimeFormat("en-IN", { day: "numeric", month: "long", year: "numeric" }).format(new Date(d));
    } catch { return ""; }
  };

  return (
    <div className="group bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden hover:shadow-xl hover:-translate-y-1 transition-all duration-300">
      {/* Image */}
      {wish.image_url ? (
        <div className="aspect-[4/3] relative overflow-hidden">
          <img
            src={wish.image_url}
            alt={wish.title}
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-black/50 to-transparent" />
          <span className={`absolute top-3 left-3 px-3 py-1 text-[10px] font-bold uppercase tracking-wider text-white rounded-full bg-gradient-to-r ${gradient} shadow-lg`}>
            {wish.wish_type}
          </span>
        </div>
      ) : (
        <div className={`aspect-[4/3] bg-gradient-to-br ${gradient} flex items-center justify-center relative`}>
          <Gift className="w-16 h-16 text-white/30" />
          <span className="absolute top-3 left-3 px-3 py-1 text-[10px] font-bold uppercase tracking-wider text-white bg-white/20 backdrop-blur-sm rounded-full">
            {wish.wish_type}
          </span>
        </div>
      )}

      {/* Content */}
      <div className="p-5">
        <h3 className="text-lg font-black text-zinc-900 mb-2 leading-tight group-hover:text-[var(--pf-saffron)] transition-colors">
          {wish.title}
        </h3>
        {wish.person_name && (
          <p className="text-sm font-bold text-[var(--pf-navy)] mb-2 flex items-center gap-1.5">
            <Heart className="w-3.5 h-3.5 text-rose-500 fill-rose-500" />
            {wish.person_name}
          </p>
        )}
        {wish.message && (
          <p className="text-sm text-zinc-500 leading-relaxed line-clamp-3 mb-3">
            {wish.message}
          </p>
        )}
        <div className="flex items-center justify-between text-[10px] text-zinc-400 font-bold uppercase tracking-wider pt-3 border-t border-gray-100">
          {wish.occasion_date ? (
            <span className="flex items-center gap-1.5">
              <Calendar className="w-3 h-3" />
              {fmtDate(wish.occasion_date)}
            </span>
          ) : (
            <span>{fmtDate(wish.created_at)}</span>
          )}
          <span className={`px-2 py-0.5 rounded-full bg-gradient-to-r ${gradient} text-white`}>
            {wish.wish_type}
          </span>
        </div>
      </div>
    </div>
  );
}

export default function WishesPage() {
  const [filter, setFilter] = useState("all");
  const [cat, setCat] = useState("All");
  const [search, setSearch] = useState("");

  const { data: wishes, isLoading } = useQuery<WishItem[]>({
    queryKey: ["wishes", filter],
    queryFn: () => newsApi.getActiveWishes(filter === "all" ? undefined : filter),
    staleTime: 2 * 60 * 1000,
  });

  return (
    <div className="min-h-screen bg-tricolor-light text-zinc-900">
      <PremiumHeader
        selectedCategory={cat}
        onCategoryChange={setCat}
        searchQuery={search}
        onSearchChange={setSearch}
      />

      {/* Hero Banner */}
      <div className="bg-gradient-to-r from-[var(--pf-navy)] via-[#1a237e] to-[var(--pf-navy)] text-white py-12 px-4 relative overflow-hidden">
        <div className="absolute inset-0 opacity-10">
          <div className="absolute top-10 left-10 w-32 h-32 bg-[var(--pf-saffron)] rounded-full blur-3xl" />
          <div className="absolute bottom-10 right-10 w-32 h-32 bg-[var(--pf-green)] rounded-full blur-3xl" />
        </div>
        <div className="max-w-5xl mx-auto text-center relative z-10">
          <div className="tricolor-stripe rounded-full w-24 mx-auto mb-6" />
          <h1 className="text-4xl md:text-6xl font-black uppercase tracking-tight mb-3" style={{ fontFamily: "var(--font-headline)" }}>
            Wishes & Greetings
          </h1>
          <p className="text-white/70 text-lg max-w-xl mx-auto">
            Celebrate special moments with heartfelt wishes from the Peoples Feedback community.
          </p>
        </div>
      </div>

      {/* Filter tabs */}
      <div className="max-w-7xl mx-auto px-4 py-6">
        <div className="flex items-center gap-2 overflow-x-auto no-scrollbar pb-2">
          {WISH_TYPES.map(({ key, label, icon: Icon }) => (
            <button
              key={key}
              onClick={() => setFilter(key)}
              className={`flex items-center gap-2 px-5 py-2.5 rounded-full text-sm font-bold whitespace-nowrap transition-all ${
                filter === key
                  ? "bg-[var(--pf-navy)] text-white shadow-lg"
                  : "bg-white text-zinc-600 border border-gray-200 hover:border-[var(--pf-saffron)] hover:text-[var(--pf-saffron)]"
              }`}
            >
              <Icon className="w-4 h-4" />
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Wishes Grid */}
      <main className="max-w-7xl mx-auto px-4 pb-16">
        {isLoading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="bg-white rounded-2xl overflow-hidden">
                <div className="aspect-[4/3] skeleton" />
                <div className="p-5 space-y-3">
                  <div className="skeleton h-5 w-3/4 rounded" />
                  <div className="skeleton h-4 w-full rounded" />
                  <div className="skeleton h-4 w-2/3 rounded" />
                </div>
              </div>
            ))}
          </div>
        ) : !wishes?.length ? (
          <div className="text-center py-20">
            <Gift className="w-16 h-16 text-zinc-200 mx-auto mb-4" />
            <h3 className="text-xl font-bold text-zinc-400 mb-2">No wishes yet</h3>
            <p className="text-zinc-300">Check back soon for greetings and celebrations!</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {wishes.map((wish) => (
              <WishCard key={wish.id} wish={wish} />
            ))}
          </div>
        )}
      </main>

      <PremiumFooter />
      <BackToTop />
    </div>
  );
}
