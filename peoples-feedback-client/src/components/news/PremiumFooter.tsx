import { Link } from "wouter";
import { useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Globe, Twitter, Facebook, Linkedin, Mail, Youtube } from "lucide-react";
import { newsApi } from "@/lib/api";
import { DEFAULT_CATEGORIES, CategoryResponse } from "@/types/news";

export function PremiumFooter() {
  const { data: apiCats } = useQuery<CategoryResponse[]>({
    queryKey: ["categories"],
    queryFn: () => newsApi.getCategories(),
    staleTime: 10 * 60 * 1000,
  });
  const cats = apiCats && apiCats.length > 0 ? apiCats.map(c => c.name) : [...DEFAULT_CATEGORIES].filter(c => c !== "Home");

  return (
    <footer className="bg-gradient-to-br from-[var(--pf-dark)] via-[var(--pf-navy)] to-black text-zinc-400 pt-20 pb-8 relative overflow-hidden">
      {/* Background pattern */}
      <div className="absolute inset-0 opacity-5">
        <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHZpZXdCb3g9IjAgMCA2MCA2MCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPGNpcmNsZSBjeD0iMzAiIGN5PSIzMCIgcj0iMiIgZmlsbD0id2hpdGUiLz4KPC9zdmc+')]"></div>
      </div>
      
      <div className="max-w-7xl mx-auto px-4 relative z-10">
        <div className="grid grid-cols-1 md:grid-cols-12 gap-12 mb-16">
          {/* Brand */}
          <div className="md:col-span-4 space-y-6">
            <Link href="/">
              <div className="flex items-center gap-4 cursor-pointer group">
                <div className="relative">
                  <img src="/pf-logo.png" alt="PF" className="h-12 w-auto filter brightness-0 invert opacity-80 group-hover:opacity-100 transition-opacity duration-300" />
                  <div className="absolute -inset-1 bg-gradient-to-r from-[var(--pf-orange)] to-[var(--pf-pink)] rounded-full opacity-0 group-hover:opacity-20 blur-lg transition-opacity duration-300"></div>
                </div>
                <div>
                  <h2 className="text-2xl font-black text-white leading-none group-hover:text-transparent group-hover:bg-gradient-to-r group-hover:from-[var(--pf-orange)] group-hover:to-[var(--pf-pink)] group-hover:bg-clip-text transition-all duration-300" style={{ fontFamily: 'var(--font-headline)' }}>
                    Peoples Feedback
                  </h2>
                  <span className="text-[10px] font-bold tracking-[0.2em] text-transparent bg-gradient-to-r from-[var(--pf-saffron)] to-[var(--pf-gold)] bg-clip-text uppercase">Empowering Every Voice</span>
                </div>
              </div>
            </Link>
            <p className="text-base leading-relaxed text-zinc-300 max-w-sm" style={{ fontFamily: 'var(--font-serif)' }}>
              India's trusted platform for transparent community news and public accountability. Delivering truth, driving progress.
            </p>
            <div className="flex items-center gap-4">
              {[Twitter, Facebook, Youtube, Linkedin, Mail].map((Icon, i) => (
                <div key={i} className="w-10 h-10 rounded-full border-2 border-zinc-600 flex items-center justify-center hover:border-[var(--pf-orange)] hover:text-[var(--pf-orange)] hover:bg-[var(--pf-orange)]/10 transition-all duration-300 cursor-pointer transform hover:scale-110">
                  <Icon className="w-5 h-5" />
                </div>
              ))}
            </div>
          </div>

          {/* Sections */}
          <div className="md:col-span-2">
            <h4 className="text-[11px] font-extrabold uppercase tracking-[0.2em] text-transparent bg-gradient-to-r from-[var(--pf-orange)] to-[var(--pf-pink)] bg-clip-text mb-6">Sections</h4>
            <ul className="space-y-3 text-[14px]">
              {cats.slice(0, 8).map(cat => (
                <li key={cat}>
                  <Link href={`/news?category=${cat}`} className="text-zinc-400 hover:text-white hover:translate-x-1 transition-all duration-300 inline-block">
                    {cat}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Company */}
          <div className="md:col-span-2">
            <h4 className="text-[11px] font-extrabold uppercase tracking-[0.2em] text-transparent bg-gradient-to-r from-[var(--pf-blue)] to-[var(--pf-purple)] bg-clip-text mb-6">Company</h4>
            <ul className="space-y-3 text-[14px]">
              {["About Us", "Our Mission", "Privacy Policy", "Terms of Use", "Contact"].map(item => (
                <li key={item}>
                  <a href="#" className="text-zinc-400 hover:text-white hover:translate-x-1 transition-all duration-300 inline-block">
                    {item}
                  </a>
                </li>
              ))}
            </ul>
          </div>

          {/* Newsletter */}
          <div className="md:col-span-4">
            <div className="p-8 bg-gradient-to-br from-white/10 to-white/5 border border-white/20 rounded-2xl backdrop-blur-sm">
              <h4 className="text-lg font-black uppercase tracking-wider text-white mb-3" style={{ fontFamily: 'var(--font-headline)' }}>
                The Morning Brief
              </h4>
              <p className="text-sm text-zinc-300 mb-6 leading-relaxed" style={{ fontFamily: 'var(--font-serif)' }}>
                The most important stories, delivered to your inbox every morning.
              </p>
              <div className="flex gap-3">
                <Input className="bg-white/10 border-white/20 text-white placeholder:text-zinc-500 h-12 rounded-xl text-sm flex-1 focus:ring-2 focus:ring-[var(--pf-orange)]/50 focus:border-[var(--pf-orange)] transition-all duration-300" placeholder="your@email.com" />
                <Button className="bg-gradient-to-r from-[var(--pf-orange)] to-[var(--pf-pink)] hover:from-orange-600 hover:to-pink-600 text-white font-bold text-[11px] uppercase h-12 px-8 rounded-xl tracking-wider shadow-lg hover:shadow-xl transform hover:scale-105 transition-all duration-300">
                  Subscribe
                </Button>
              </div>
            </div>
          </div>
        </div>

        {/* Bottom */}
        <div className="tricolor-stripe mb-8 opacity-50"></div>
        <div className="flex flex-col md:flex-row items-center justify-between gap-4 text-[11px] font-medium tracking-wide">
          <span className="text-zinc-400">© 2026 Peoples Feedback Media Pvt Ltd. All rights reserved.</span>
          <div className="flex items-center gap-3 text-zinc-300">
            <div className="w-2 h-2 bg-[var(--pf-green)] rounded-full animate-pulse"></div>
            <Globe className="w-4 h-4" />
            <span>India Edition</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
