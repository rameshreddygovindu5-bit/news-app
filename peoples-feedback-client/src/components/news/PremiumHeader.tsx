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

  const baseCategories = apiCategories && apiCategories.length > 0
    ? ['Home', ...apiCategories.filter(c => c.name !== 'Home').map(c => c.name)]
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

  // Auto-cleanup for Telugu translation stickiness
  useEffect(() => {
    if (!location.startsWith('/telugu') && document.cookie.includes('googtrans=/en/te')) {
      document.cookie = `googtrans=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;`;
      document.cookie = `googtrans=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/; domain=${window.location.hostname};`;
      window.location.reload();
    }
  }, [location]);

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
    setMenuOpen(false);
    window.scrollTo({ top: 0, behavior: 'smooth' });
    if (cat === 'తెలుగు వార్తలు') { setLocation('/telugu'); return; }
    const id = cat === 'Home' ? '' : cat;
    onCategoryChange?.(id || 'All');
    if (id) setLocation(`/news?category=${id}`); else setLocation('/');
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery?.trim()) setLocation(`/news?search=${encodeURIComponent(searchQuery.trim())}`);
  };

  // ── Hierarchical Menu Structure ──
  const menuConfig = [
    { name: 'Home', path: 'Home' },
    {
      name: 'Politics & World',
      items: ['Politics', 'World', 'Events']
    },
    {
      name: 'Business & Tech',
      items: ['Business', 'Tech', 'Science', 'Sports']
    },
    {
      name: 'Lifestyle',
      items: ['Entertainment', 'Health']
    },
    {
      name: 'Insights & Polls',
      items: ['Surveys', 'Polls']
    },
    { name: 'తెలుగు వార్తలు', path: 'తెలుగు వార్తలు', isSpecial: true }
  ];

  return (
    <header className="flex flex-col w-full z-50 notranslate">
      {/* ── Tricolor stripe ── */}
      <div className="tricolor-stripe" />

      {/* ── Top utility bar — vibrant gradient ── */}
      <div className="nav-india text-white h-12 px-4 hidden md:flex items-center justify-between text-[11px] font-medium shadow-lg relative overflow-hidden">
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
                    <h1 className="text-xl sm:text-2xl md:text-5xl font-black tracking-tight text-tricolor transition-transform duration-300 truncate md:whitespace-normal" style={{ fontFamily: 'var(--font-headline)' }}>
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

      {/* ── Category nav — Hierarchical Dropdown ── */}
      <motion.div className={`w-full z-40 transition-all duration-300 ${scrolled ? 'fixed top-0 bg-white/95 backdrop-blur-md shadow-xl border-b border-gray-100' : 'relative bg-gradient-to-r from-white via-gray-50 to-white border-b border-gray-200'}`}>
        <div className="max-w-7xl mx-auto px-4 flex items-center h-12">
          <nav className="flex-1 flex items-center gap-2">
            {menuConfig.map((main) => {
              const isDirect = !!main.path;
              const isActiveMain = isDirect && (
                (main.path === 'Home' && (!selectedCategory || selectedCategory === 'All')) ||
                selectedCategory === main.path ||
                (main.path === 'తెలుగు వార్తలు' && location === '/telugu')
              );
              const hasActiveChild = !isDirect && main.items?.some(sub => selectedCategory === sub);

              return (
                <div key={main.name} className="relative group/menu h-12 flex items-center">
                  <button
                    onClick={() => isDirect ? handleCat(main.path!) : null}
                    className={`px-4 text-[13px] font-black h-12 flex items-center transition-all duration-300 whitespace-nowrap uppercase tracking-wider
                      ${(isActiveMain || hasActiveChild) 
                        ? 'text-transparent bg-gradient-to-r from-[var(--pf-navy)] to-[var(--pf-blue)] bg-clip-text border-b-2 border-[var(--pf-navy)] shadow-sm' 
                        : 'text-zinc-600 hover:text-[var(--pf-navy)]'}
                      ${main.isSpecial ? 'telugu !font-bold !tracking-normal !normal-case !text-[15px]' : ''}`}
                  >
                    {main.name}
                    {!isDirect && <span className="ml-1 opacity-50 group-hover/menu:rotate-180 transition-transform text-[8px]">▼</span>}
                  </button>

                  {/* Dropdown for submenus */}
                  {!isDirect && (
                    <div className="absolute top-12 left-0 w-48 bg-white shadow-2xl border border-gray-100 rounded-b-xl opacity-0 invisible group-hover/menu:opacity-100 group-hover/menu:visible transition-all duration-200 transform translate-y-2 group-hover/menu:translate-y-0 z-50 overflow-hidden">
                      <div className="p-2 space-y-1">
                        {main.items?.map(sub => (
                          <button
                            key={sub}
                            onClick={() => handleCat(sub)}
                            className={`w-full text-left px-4 py-2.5 text-[12px] font-bold rounded-lg transition-all
                              ${selectedCategory === sub 
                                ? 'bg-[var(--pf-navy)]/5 text-[var(--pf-navy)]' 
                                : 'text-zinc-500 hover:bg-zinc-50 hover:text-[var(--pf-navy)]'}`}
                          >
                            {sub}
                          </button>
                        ))}
                      </div>
                      <div className="h-1 w-full bg-gradient-to-r from-[var(--pf-saffron)] via-[var(--pf-navy)] to-[var(--pf-green)] opacity-20" />
                    </div>
                  )}
                </div>
              );
            })}
          </nav>
          <div className="hidden lg:flex items-center gap-2 text-[11px] font-bold text-transparent bg-gradient-to-r from-[var(--pf-red)] to-[var(--pf-saffron)] bg-clip-text uppercase tracking-wider pl-6 border-l-2 border-gray-200">
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
                  <h2 className="text-lg font-black text-tricolor">Peoples Feedback</h2>
                  <p className="text-[10px] text-gray-500 uppercase tracking-wider">Empowering Every Voice</p>
                </div>
              </div>
              <Button variant="ghost" size="icon" onClick={() => setMenuOpen(false)} className="text-gray-600 hover:text-[var(--pf-red)] transition-colors">
                <X className="h-5 w-5" />
              </Button>
            </div>
            <div className="flex-1 overflow-y-auto p-6">
              <div className="space-y-2">
                {menuConfig.map((main) => {
                  const isDirect = !!main.path;
                  const isActiveMain = isDirect && (
                    (main.path === 'Home' && (!selectedCategory || selectedCategory === 'All')) ||
                    selectedCategory === main.path ||
                    (main.path === 'తెలుగు వార్తలు' && location === '/telugu')
                  );

                  return (
                    <div key={main.name} className="space-y-1">
                      <button 
                        onClick={() => isDirect ? handleCat(main.path!) : null}
                        className={`w-full text-left text-lg font-black transition-all duration-300 flex items-center py-4 px-4 rounded-xl border-2
                          ${isActiveMain 
                            ? 'text-white bg-[var(--pf-navy)] border-[var(--pf-saffron)] shadow-lg' 
                            : 'text-zinc-800 border-zinc-100 bg-zinc-50/50'}
                          ${main.isSpecial ? 'telugu !font-bold' : ''}`}>
                        <span className="flex-1">{main.name}</span>
                        {!isDirect && <span className="text-[10px] opacity-30">▼</span>}
                        {isDirect && <ArrowRight className={`h-5 w-5 ${isActiveMain ? 'text-white' : 'text-zinc-300'}`} />}
                      </button>
                      
                      {!isDirect && (
                        <div className="grid grid-cols-2 gap-2 pl-2 pb-2">
                          {main.items?.map(sub => (
                            <button
                              key={sub}
                              onClick={() => handleCat(sub)}
                              className={`text-left px-4 py-3 text-sm font-bold rounded-lg transition-all border
                                ${selectedCategory === sub 
                                  ? 'bg-[var(--pf-saffron)] text-white border-[var(--pf-saffron)] shadow-md' 
                                  : 'bg-white text-zinc-500 border-zinc-100 hover:border-[var(--pf-saffron)]'}`}
                            >
                              {sub}
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
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
