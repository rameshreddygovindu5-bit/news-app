/**
 * Wishes Page — /wishes
 * Displays birthday greetings, festival wishes, special occasions.
 * Users can view all active wishes with images.
 */
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Gift, Calendar, Heart, Star, PartyPopper, Share2 } from "lucide-react";
import { PremiumHeader } from "@/components/news/PremiumHeader";
import { PremiumFooter } from "@/components/news/PremiumFooter";
import { BackToTop } from "@/components/news/BackToTop";
import { newsApi, API_BASE } from "@/lib/api";
import type { WishItem } from "@/types/news";
import { motion, AnimatePresence } from "framer-motion";
import { useToast } from "@/hooks/use-toast";
import { ShareBar } from "@/components/news/ShareMenu";

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
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const [isLiked, setIsLiked] = useState(false);
  const gradient = typeColors[wish.wish_type] || "from-[var(--pf-saffron)] to-[var(--pf-orange)]";
  
  const likeMutation = useMutation({
    mutationFn: () => newsApi.likeWish(wish.id),
    onSuccess: (data) => {
      setIsLiked(true);
      queryClient.setQueryData(["wishes", "all"], (old: any) => {
        if (!old) return old;
        return old.map((w: WishItem) => w.id === wish.id ? { ...w, likes_count: data.likes_count } : w);
      });
      toast({
        title: "Celebrated!",
        description: "Your wish has been shared with the community.",
      });
    },
  });

  const fmtDate = (d?: string) => {
    if (!d) return "";
    try {
      return new Intl.DateTimeFormat("en-IN", { day: "numeric", month: "long", year: "numeric" }).format(new Date(d));
    } catch { return ""; }
  };

  return (
    <div className="group bg-white rounded-3xl shadow-xl border border-white overflow-hidden hover:shadow-2xl transition-all duration-500 flex flex-col h-full relative">
      {/* Decorative border gradient */}
      <div className={`absolute inset-0 bg-gradient-to-br ${gradient} opacity-0 group-hover:opacity-5 transition-opacity duration-500 pointer-events-none`} />
      
      {/* Image / Header Section */}
      {wish.image_url ? (
        <div className="aspect-video relative overflow-hidden">
          <img
            src={wish.image_url.startsWith('/uploads') ? `${API_BASE.replace(/\/$/, '')}${wish.image_url}` : wish.image_url}
            alt={wish.title}
            className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-700"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent" />
          <div className="absolute top-4 left-4">
            <span className={`px-4 py-1.5 text-[11px] font-black uppercase tracking-widest text-white rounded-full bg-gradient-to-r ${gradient} shadow-2xl ring-2 ring-white/30 backdrop-blur-sm`}>
              {wish.wish_type}
            </span>
          </div>
        </div>
      ) : (
        <div className={`aspect-video bg-gradient-to-br ${gradient} flex items-center justify-center relative overflow-hidden`}>
          <div className="absolute inset-0 opacity-20">
             <div className="absolute top-0 left-0 w-full h-full bg-[url('https://www.transparenttextures.com/patterns/carbon-fibre.png')]" />
          </div>
          <Gift className="w-24 h-24 text-white/30 animate-pulse relative z-10" />
          <div className="absolute inset-0 pointer-events-none">
             {[...Array(8)].map((_, i) => (
               <Star key={i} className={`absolute text-white/40 w-5 h-5 animate-ping`} style={{ top: `${Math.random()*100}%`, left: `${Math.random()*100}%`, animationDelay: `${i*0.4}s` }} />
             ))}
          </div>
          <div className="absolute top-4 left-4">
            <span className="px-4 py-1.5 text-[11px] font-black uppercase tracking-widest text-white bg-white/20 backdrop-blur-md rounded-full shadow-lg ring-1 ring-white/30">
              {wish.wish_type}
            </span>
          </div>
        </div>
      )}

      {/* Content Section */}
      <div className="p-8 flex-grow flex flex-col relative z-20">
        <h3 className="text-2xl font-black text-zinc-900 mb-4 leading-tight group-hover:text-[var(--pf-navy)] transition-colors" style={{ fontFamily: 'var(--font-headline)' }}>
          {wish.title}
        </h3>
        
        {wish.person_name && (
          <div className="flex items-center gap-3 mb-6 bg-zinc-50 p-3 rounded-2xl border border-zinc-100">
            <div className={`w-10 h-10 rounded-full bg-gradient-to-br ${gradient} flex items-center justify-center text-white text-sm font-black shadow-lg ring-2 ring-white`}>
              {wish.person_name.charAt(0)}
            </div>
            <div className="flex flex-col">
               <span className="text-[10px] text-zinc-400 font-bold uppercase tracking-widest">From</span>
               <span className="text-md font-extrabold text-[var(--pf-navy)] tracking-tight">
                {wish.person_name}
               </span>
            </div>
          </div>
        )}

        {wish.message && (
          <div className="relative">
            <p className="text-[17px] text-zinc-700 leading-relaxed font-semibold mb-6 whitespace-pre-wrap selection:bg-[var(--pf-saffron)] selection:text-white">
              {wish.message}
            </p>
          </div>
        )}

        <div className="mt-auto pt-6 border-t border-zinc-100 flex flex-col gap-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-[12px] font-extrabold text-zinc-400 uppercase tracking-tighter">
              <Calendar className="w-4 h-4 text-[var(--pf-saffron)]" />
              {wish.occasion_date ? fmtDate(wish.occasion_date) : fmtDate(wish.created_at)}
            </div>
            <motion.div 
               whileTap={{ scale: 0.9 }}
               onClick={() => !isLiked && likeMutation.mutate()}
               className={`flex items-center gap-2 px-4 py-2 rounded-full cursor-pointer transition-all duration-300 group/heart ${
                 isLiked ? 'bg-rose-500 text-white shadow-lg' : 'bg-rose-50 text-rose-500 hover:bg-rose-100'
               }`}
            >
              <Heart className={`w-4 h-4 transition-colors ${isLiked ? 'fill-white' : 'fill-none group-hover/heart:fill-rose-500'}`} />
              <span className="text-xs font-black">{wish.likes_count || 0}</span>
              {!isLiked && <span className="text-[10px] font-bold uppercase ml-1 opacity-0 group-hover/heart:opacity-100 transition-opacity">Celebrate</span>}
            </motion.div>
          </div>

          <div className="flex items-center justify-between bg-zinc-50 rounded-2xl p-3 border border-zinc-100 hover:border-zinc-200 transition-colors">
            <div className="flex items-center gap-1.5 px-1">
              <Share2 className="w-3.5 h-3.5 text-zinc-400" />
              <span className="text-[9px] font-black uppercase tracking-[0.2em] text-zinc-400">Share Joy</span>
            </div>
            <ShareBar 
              data={{ 
                title: wish.title, 
                text: wish.message || wish.title, 
                url: `${window.location.origin}/wishes?id=${wish.id}` 
              }} 
            />
          </div>
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
    <div className="min-h-screen bg-white text-zinc-900 overflow-x-hidden">
      <PremiumHeader
        selectedCategory={cat}
        onCategoryChange={setCat}
        searchQuery={search}
        onSearchChange={setSearch}
      />

      {/* Hero Banner with Celebration Elements */}
      <div className="nav-india text-white py-20 px-4 relative overflow-hidden">
        <div className="absolute inset-0">
           <div className="absolute top-0 left-0 w-full h-full opacity-10 bg-[url('https://www.transparenttextures.com/patterns/fancy-pants.png')]" />
           <motion.div animate={{ rotate: 360 }} transition={{ duration: 20, repeat: Infinity, ease: "linear" }} className="absolute -top-20 -right-20 w-96 h-96 bg-[var(--pf-saffron)] rounded-full blur-[120px] opacity-30" />
           <motion.div animate={{ rotate: -360 }} transition={{ duration: 15, repeat: Infinity, ease: "linear" }} className="absolute -bottom-20 -left-20 w-96 h-96 bg-[var(--pf-green)] rounded-full blur-[120px] opacity-20" />
        </div>
        
        <div className="max-w-5xl mx-auto text-center relative z-10">
          <motion.div initial={{ y: 20, opacity: 0 }} animate={{ y: 0, opacity: 1 }} className="tricolor-stripe rounded-full w-32 mx-auto mb-8 h-1.5 shadow-lg" />
          <motion.h1 
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            className="text-5xl md:text-8xl font-black uppercase tracking-tighter mb-6 drop-shadow-2xl" 
            style={{ fontFamily: "var(--font-headline)" }}
          >
            Wishes & <br className="md:hidden" /><span className="text-India">Greetings</span>
          </motion.h1>
          <motion.p 
            initial={{ opacity: 0 }} 
            animate={{ opacity: 1 }} 
            transition={{ delay: 0.3 }}
            className="text-white/80 text-xl md:text-2xl font-medium max-w-2xl mx-auto leading-relaxed"
          >
            Join the Peoples Feedback community in celebrating special milestones and heartwarming wishes.
          </motion.p>
        </div>
      </div>

      {/* Filter tabs */}
      <div className="max-w-7xl mx-auto px-4 -mt-8 relative z-30">
        <div className="bg-white p-3 rounded-full shadow-2xl border border-gray-100 flex items-center gap-2 overflow-x-auto no-scrollbar scroll-smooth">
          {WISH_TYPES.map(({ key, label, icon: Icon }) => (
            <button
              key={key}
              onClick={() => setFilter(key)}
              className={`flex items-center gap-2 px-8 py-3.5 rounded-full text-sm font-black whitespace-nowrap transition-all duration-300 ${
                filter === key
                  ? "bg-[var(--pf-navy)] text-white shadow-xl scale-105"
                  : "text-zinc-500 hover:text-[var(--pf-saffron)] hover:bg-zinc-50"
              }`}
            >
              <Icon className={`w-4 h-4 ${filter === key ? 'text-[var(--pf-saffron)]' : ''}`} />
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Wishes Grid */}
      <main className="max-w-7xl mx-auto px-4 py-20">
        {isLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-2 gap-10">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="bg-white rounded-3xl overflow-hidden shadow-sm h-[400px]">
                <div className="aspect-video skeleton" />
                <div className="p-8 space-y-4">
                  <div className="skeleton h-8 w-3/4 rounded-xl" />
                  <div className="skeleton h-4 w-full rounded-lg" />
                  <div className="skeleton h-4 w-2/3 rounded-lg" />
                </div>
              </div>
            ))}
          </div>
        ) : !wishes?.length ? (
          <div className="text-center py-32 bg-zinc-50 rounded-[40px] border-2 border-dashed border-zinc-200">
            <div className="relative inline-block">
               <Gift className="w-24 h-24 text-zinc-200 mx-auto mb-6" />
               <Star className="absolute -top-2 -right-2 w-8 h-8 text-[var(--pf-saffron)]/20 animate-spin" />
            </div>
            <h3 className="text-3xl font-black text-zinc-400 mb-4">No wishes found</h3>
            <p className="text-zinc-300 text-lg">We haven't shared any greetings lately. Stay tuned!</p>
          </div>
        ) : (
          <motion.div 
            layout
            className={`grid grid-cols-1 md:grid-cols-1 ${wishes.length > 1 ? 'lg:grid-cols-2' : 'lg:grid-cols-1 max-w-3xl mx-auto'} gap-12`}
          >
            <AnimatePresence mode="popLayout">
              {wishes.map((wish) => (
                <motion.div
                  key={wish.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, scale: 0.9 }}
                  transition={{ duration: 0.5, ease: "easeOut" }}
                >
                  <WishCard wish={wish} />
                </motion.div>
              ))}
            </AnimatePresence>
          </motion.div>
        )}
      </main>

      <PremiumFooter />
      <BackToTop />
    </div>
  );
}
