import { useState, useEffect } from "react";
import { Link, useLocation } from "wouter";
import { useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { motion, AnimatePresence } from "framer-motion";
import { Search, Menu, X, ArrowRight, TrendingUp } from "lucide-react";
import { newsApi } from "@/lib/api";
import { DEFAULT_CATEGORIES, CategoryResponse } from "@/types/news";

interface Props {
  selectedCategory?: string;
  onCategoryChange?: (cat: string) => void;
  searchQuery?: string;
  onSearchChange?: (q: string) => void;
}

export function PremiumHeader({ selectedCategory, onCategoryChange, searchQuery, onSearchChange }: Props) {
  const [menuOpen, setMenuOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const [, setLocation] = useLocation();
  const [location] = useLocation();

  const { data: apiCategories } = useQuery<CategoryResponse[]>({
    queryKey: ["categories"],
    queryFn: () => newsApi.getCategories(),
    staleTime: 10 * 60 * 1000,
  });

  const navCategories = apiCategories && apiCategories.length > 0
    ? ['Home', ...apiCategories.map(c => c.name)]
    : [...DEFAULT_CATEGORIES];

  useEffect(() => {
    const h = () => setScrolled(window.scrollY > 60);
    window.addEventListener('scroll', h);
    return () => window.removeEventListener('scroll', h);
  }, []);

  useEffect(() => {
    const init = () => {
      if (!document.getElementById('gt-script')) {
        const s = document.createElement('script');
        s.id = 'gt-script';
        s.src = '//translate.google.com/translate_a/element.js?cb=gtInit';
        s.async = true;
        document.body.appendChild(s);
        (window as any).gtInit = () => {
          new (window as any).google.translate.TranslateElement({
            pageLanguage: 'en', includedLanguages: 'te,hi,en,ta,kn,ml',
            layout: (window as any).google.translate.TranslateElement.InlineLayout.SIMPLE, autoDisplay: false
          }, 'google_translate_element');
        };
      }
    };
    const t = setTimeout(init, 800);
    return () => clearTimeout(t);
  }, [location]);

  const currentDate = new Intl.DateTimeFormat('en-US', { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' }).format(new Date());
  const langs = [{ name: 'English', code: 'en' }, { name: 'తెలుగు', code: 'te' }, { name: 'हिन्दी', code: 'hi' }];

  const switchLang = (code: string) => {
    document.cookie = `googtrans=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;`;
    document.cookie = `googtrans=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/; domain=${window.location.hostname};`;
    if (code !== 'en') {
      document.cookie = `googtrans=/en/${code}; path=/;`;
      document.cookie = `googtrans=/en/${code}; path=/; domain=${window.location.hostname};`;
    }
    window.location.reload();
  };

  const handleCat = (cat: string) => {
    const id = cat === 'Home' ? '' : cat;
    onCategoryChange?.(id || 'All');
    if (id) setLocation(`/news?category=${id}`);
    else setLocation('/');
    setMenuOpen(false);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery?.trim()) setLocation(`/news?search=${encodeURIComponent(searchQuery.trim())}`);
  };

  return (
    <header className="flex flex-col w-full z-50">
      {/* ── Tricolor stripe ── */}
      <div className="tricolor-stripe" />

      {/* ── Top utility bar — vibrant gradient ── */}
      <div className="bg-gradient-to-r from-[var(--pf-navy)] via-[var(--pf-blue)] to-[var(--pf-purple)] text-white h-12 px-4 hidden md:flex items-center justify-between text-[11px] font-medium shadow-lg relative overflow-hidden">
        {/* Animated background element */}
        <div className="absolute inset-0 bg-[url('https://www.transparenttextures.com/patterns/carbon-fibre.png')] opacity-10"></div>
        
        <div className="flex items-center gap-6 relative z-10">
          <div className="flex items-center gap-2 bg-white/10 backdrop-blur-md border border-white/20 rounded-full px-3 py-1.5 shadow-inner">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[var(--pf-green)] opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-[var(--pf-green)]"></span>
            </span>
            <span className="text-[10px] font-black uppercase tracking-widest text-[var(--pf-green)]">Live</span>
            <div className="w-px h-3 bg-white/20 mx-1"></div>
            <span className="text-white/90 font-bold">{currentDate}</span>
          </div>

          <div className="flex items-center gap-1.5 bg-black/20 backdrop-blur-sm border border-white/10 rounded-full p-1">
            {langs.map(l => {
              const isActive = document.cookie.includes(`googtrans=/en/${l.code}`) || (l.code === 'en' && !document.cookie.includes('googtrans='));
              return (
                <button key={l.code} onClick={() => switchLang(l.code)}
                  className={`px-3 py-1 rounded-full text-[10px] font-bold transition-all duration-300 ${isActive ? 'bg-gradient-to-r from-[var(--pf-orange)] to-[var(--pf-pink)] text-white shadow-lg transform scale-105' : 'text-white/70 hover:text-white hover:bg-white/10'}`}>
                  {l.name}
                </button>
              );
            })}
          </div>
        </div>

        <div className="flex items-center gap-8 relative z-10">
          <div className="hidden lg:flex items-center gap-4">
            <span className="flex items-center gap-1.5 text-white/70 hover:text-white transition-colors cursor-pointer">
              <TrendingUp className="w-3.5 h-3.5" />
              <span className="font-bold uppercase tracking-tighter">Election 2024</span>
            </span>
            <span className="flex items-center gap-1.5 text-white/70 hover:text-white transition-colors cursor-pointer">
              <TrendingUp className="w-3.5 h-3.5" />
              <span className="font-bold uppercase tracking-tighter">Tech Summit</span>
            </span>
          </div>

          <div id="google_translate_element" className="hidden" />
          <span className="text-white/90 font-bold italic tracking-wider flex items-center gap-2 bg-white/5 px-4 py-1.5 rounded-full border border-white/10">
            <span className="w-1.5 h-1.5 bg-[var(--pf-saffron)] rounded-full animate-pulse shadow-[0_0_8px_var(--pf-saffron)]"></span>
            Empowering Every Voice
          </span>
        </div>
      </div>

      {/* ── Masthead — enhanced modern style ── */}
      <div className="bg-gradient-to-br from-white via-white to-gray-50 border-b border-gray-200 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-6 md:py-8 flex items-center justify-between">
          <div className="md:hidden">
            <Button variant="ghost" size="icon" onClick={() => setMenuOpen(true)} className="text-gray-700 hover:text-[var(--pf-orange)] transition-colors"><Menu className="h-6 w-6" /></Button>
          </div>
          <div className="flex-1 flex md:justify-center justify-center overflow-hidden">
            <Link href="/" onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}>
              <div className="flex flex-col items-center cursor-pointer group max-w-full">
                <div className="flex items-center gap-3 md:gap-4 max-w-full">
                  <div className="relative shrink-0">
                    <img src="/pf-logo.png" alt="PF" className="h-10 md:h-16 w-auto object-contain filter drop-shadow-lg group-hover:scale-110 transition-transform duration-300" />
                    <div className="absolute -inset-1 bg-gradient-to-r from-[var(--pf-orange)] to-[var(--pf-pink)] rounded-full opacity-0 group-hover:opacity-20 blur-lg transition-opacity duration-300"></div>
                  </div>
                  <div className="flex flex-col items-center md:items-start min-w-0">
                    <h1 className="text-xl sm:text-2xl md:text-5xl font-black tracking-tight bg-gradient-to-r from-[var(--pf-navy)] via-[var(--pf-blue)] to-[var(--pf-purple)] bg-clip-text text-transparent leading-none group-hover:scale-105 transition-transform duration-300 truncate md:whitespace-normal" style={{ fontFamily: 'var(--font-headline)' }}>
                      Peoples Feedback
                    </h1>
                    <div className="flex items-center gap-2 md:gap-3 mt-1.5 md:mt-2">
                      <div className="h-0.5 w-4 md:w-8 bg-gradient-to-r from-[var(--pf-orange)] to-[var(--pf-pink)]"></div>
                      <span className="text-[8px] md:text-[10px] font-bold tracking-[0.1em] md:tracking-[0.2em] text-transparent bg-gradient-to-r from-[var(--pf-green)] to-[var(--pf-teal)] bg-clip-text uppercase whitespace-nowrap">Empowering Every Voice</span>
                      <div className="h-0.5 w-4 md:w-8 bg-gradient-to-r from-[var(--pf-green)] to-[var(--pf-teal)]"></div>
                    </div>
                  </div>
                </div>
              </div>
            </Link>
          </div>
          <div className="hidden md:flex items-center">
            <form onSubmit={handleSearchSubmit} className="relative group">
              <div className="absolute inset-0 bg-gradient-to-r from-[var(--pf-orange)] to-[var(--pf-pink)] rounded-full opacity-0 group-hover:opacity-10 transition-opacity duration-300"></div>
              <input
                className="pl-5 pr-12 py-3 bg-white border-2 border-gray-200 text-gray-900 text-sm w-56 focus:w-72 focus:bg-white focus:ring-2 focus:ring-[var(--pf-orange)]/30 focus:border-[var(--pf-orange)] outline-none transition-all duration-300 rounded-full shadow-sm group-hover:shadow-md"
                placeholder="Search news..."
                value={searchQuery}
                onChange={e => onSearchChange?.(e.target.value)}
              />
              <button type="submit" className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 group-hover:text-[var(--pf-orange)] transition-colors duration-300">
                <Search className="h-4 w-4" />
              </button>
            </form>
          </div>
        </div>
      </div>

      {/* ── Category nav — enhanced modern navigation ── */}
      <motion.div className={`w-full z-40 transition-all duration-300 ${scrolled ? 'fixed top-0 bg-white/95 backdrop-blur-md shadow-xl border-b border-gray-100' : 'relative bg-gradient-to-r from-white via-gray-50 to-white border-b border-gray-200'}`}>
        <div className="max-w-7xl mx-auto px-4 flex items-center h-12">
          <nav className="flex-1 flex items-center gap-0 overflow-x-auto no-scrollbar">
            {navCategories.map(cat => {
              const isActive = (cat === 'Home' && (!selectedCategory || selectedCategory === 'All')) || selectedCategory === cat;
              return (
                <button key={cat} onClick={() => handleCat(cat)}
                  className={`relative px-5 text-[13px] font-bold uppercase tracking-[0.05em] h-12 flex items-center transition-all duration-300 whitespace-nowrap border-b-3 group
                    ${isActive 
                      ? 'text-transparent bg-gradient-to-r from-[var(--pf-orange)] to-[var(--pf-pink)] bg-clip-text border-[var(--pf-orange)] shadow-lg transform scale-105' 
                      : 'text-gray-600 border-transparent hover:text-[var(--pf-navy)] hover:border-gray-300 hover:transform hover:scale-105'}`}>
                  {cat}
                  {isActive && (
                    <div className="absolute inset-0 bg-gradient-to-r from-[var(--pf-orange)]/10 to-[var(--pf-pink)]/10 rounded-lg -z-10"></div>
                  )}
                </button>
              );
            })}
          </nav>
          <div className="hidden lg:flex items-center gap-2 text-[11px] font-bold text-transparent bg-gradient-to-r from-[var(--pf-red)] to-[var(--pf-pink)] bg-clip-text uppercase tracking-wider pl-6 border-l-2 border-gray-200">
            <TrendingUp className="w-4 h-4 text-[var(--pf-red)]" />
            <span>Trending</span>
          </div>
        </div>
      </motion.div>

      {/* ── Mobile drawer — enhanced modern design ── */}
      <AnimatePresence>
        {menuOpen && (
          <motion.div initial={{ x: '-100%' }} animate={{ x: 0 }} exit={{ x: '-100%' }} transition={{ type: 'tween', duration: 0.25 }} className="fixed inset-0 z-[100] bg-gradient-to-br from-white via-gray-50 to-white flex flex-col">
            <div className="flex justify-between items-center p-4 border-b border-gray-200 bg-white shadow-sm">
              <div className="flex items-center gap-3">
                <img src="/pf-logo.png" alt="PF" className="h-10 drop-shadow-lg" />
                <div>
                  <h2 className="text-lg font-black text-transparent bg-gradient-to-r from-[var(--pf-navy)] to-[var(--pf-purple)] bg-clip-text">Peoples Feedback</h2>
                  <p className="text-[10px] text-gray-500 uppercase tracking-wider">Empowering Every Voice</p>
                </div>
              </div>
              <Button variant="ghost" size="icon" onClick={() => setMenuOpen(false)} className="text-gray-600 hover:text-[var(--pf-red)] transition-colors">
                <X className="h-5 w-5" />
              </Button>
            </div>
            <div className="flex-1 overflow-y-auto p-6">
              <div className="space-y-2">
                {navCategories.map(cat => {
                  const isActive = (cat === 'Home' && (!selectedCategory || selectedCategory === 'All')) || selectedCategory === cat;
                  return (
                    <button key={cat} onClick={() => handleCat(cat)}
                      className={`w-full text-left text-lg font-bold transition-all duration-300 flex items-center group py-4 px-4 rounded-xl border-2
                        ${isActive 
                          ? 'text-white bg-gradient-to-r from-[var(--pf-orange)] to-[var(--pf-pink)] border-transparent shadow-lg transform scale-105' 
                          : 'text-gray-700 border-gray-200 hover:border-[var(--pf-orange)] hover:text-[var(--pf-orange)] hover:shadow-md hover:transform hover:scale-102'}`}>
                      <span className="flex-1">{cat}</span>
                      <ArrowRight className={`h-5 w-5 transition-all duration-300 ${isActive ? 'text-white' : 'text-gray-400 group-hover:text-[var(--pf-orange)] opacity-0 group-hover:opacity-100'}`} />
                    </button>
                  );
                })}
              </div>
              <div className="mt-8 pt-6 border-t border-gray-200">
                <form onSubmit={handleSearchSubmit} className="relative group">
                  <div className="absolute inset-0 bg-gradient-to-r from-[var(--pf-orange)] to-[var(--pf-pink)] rounded-xl opacity-0 group-hover:opacity-10 transition-opacity duration-300"></div>
                  <input 
                    className="w-full px-5 py-4 bg-gray-50 border-2 border-gray-200 text-gray-900 rounded-xl focus:bg-white focus:ring-2 focus:ring-[var(--pf-orange)]/30 focus:border-[var(--pf-orange)] outline-none transition-all duration-300 placeholder-gray-500" 
                    placeholder="Search news..." 
                    value={searchQuery} 
                    onChange={e => onSearchChange?.(e.target.value)} 
                  />
                  <button type="submit" className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 group-hover:text-[var(--pf-orange)] transition-colors duration-300">
                    <Search className="h-5 w-5" />
                  </button>
                </form>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </header>
  );
}
