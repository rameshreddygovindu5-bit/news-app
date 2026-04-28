/**
 * PremiumFooter — Indian flag themed.
 * Fix: Social icon links now actually navigate to social URLs.
 * Fix: "Home" added to sections list.
 * Fix: Telugu News section added.
 */
import { Link } from "wouter";
import { useQuery } from "@tanstack/react-query";
import { Globe } from "lucide-react";
import { newsApi } from "@/lib/api";
import { DEFAULT_CATEGORIES, type CategoryResponse } from "@/types/news";
import { useLocation } from "wouter";

const SOCIAL_LINKS = [
  {
    name: "Facebook",
    href: "https://www.facebook.com/peoplesfeedback",
    icon: () => (
      <svg viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4">
        <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/>
      </svg>
    ),
  },
  {
    name: "X / Twitter",
    href: "https://twitter.com/peoplesfeedback",
    icon: () => (
      <svg viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4">
        <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
      </svg>
    ),
  },
  {
    name: "YouTube",
    href: "https://youtube.com/@peoplesfeedback",
    icon: () => (
      <svg viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4">
        <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/>
      </svg>
    ),
  },
  {
    name: "WhatsApp",
    href: "https://wa.me/message/peoplesfeedback",
    icon: () => (
      <svg viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4">
        <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/>
      </svg>
    ),
  },
  {
    name: "Telegram",
    href: "https://t.me/peoplesfeedback",
    icon: () => (
      <svg viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4">
        <path d="M11.944 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0a12 12 0 0 0-.056 0zm4.962 7.224c.1-.002.321.023.465.14a.506.506 0 0 1 .171.325c.016.093.036.306.02.472-.18 1.898-.962 6.502-1.36 8.627-.168.9-.499 1.201-.82 1.23-.696.065-1.225-.46-1.9-.902-1.056-.693-1.653-1.124-2.678-1.8-1.185-.78-.417-1.21.258-1.91.177-.184 3.247-2.977 3.307-3.23.007-.032.014-.15-.056-.212s-.174-.041-.249-.024c-.106.024-1.793 1.14-5.061 3.345-.479.33-.913.49-1.302.48-.428-.008-1.252-.241-1.865-.44-.752-.245-1.349-.374-1.297-.789.027-.216.325-.437.893-.663 3.498-1.524 5.83-2.529 6.998-3.014 3.332-1.386 4.025-1.627 4.476-1.635z"/>
      </svg>
    ),
  },
];

export function PremiumFooter() {
  const { data: apiCats } = useQuery<CategoryResponse[]>({
    queryKey: ["categories"],
    queryFn:  () => newsApi.getCategories(),
    staleTime: 10 * 60 * 1000,
  });
  const cats = apiCats && apiCats.length > 0
    ? apiCats.map(c => c.name)
    : DEFAULT_CATEGORIES.filter(c => c !== "Home");
  
  const [location] = useLocation();
  const isTe = location.startsWith('/telugu');
  const t = (en: string, te: string) => isTe ? te : en;

  return (
    <footer className="bg-[var(--pf-dark)] text-zinc-400 pt-16 pb-8 relative overflow-hidden">
      {/* Indian flag tricolor top accent */}
      <div className="tricolor-stripe mb-12 opacity-70" />

      <div className="max-w-7xl mx-auto px-4">
        <div className="grid grid-cols-1 md:grid-cols-12 gap-10 mb-14">

          {/* Brand column */}
          <div className="md:col-span-4 space-y-5">
            <Link href="/" className="flex items-center gap-4 cursor-pointer group">
              <img
                src="/pf-logo.png"
                alt="PF"
                className="h-12 w-auto opacity-80 group-hover:opacity-100 transition-opacity filter brightness-0 invert"
              />
              <div>
                <h2 className="text-2xl font-black text-tricolor leading-none notranslate" style={{ fontFamily: "var(--font-headline)" }}>
                  Peoples Feedback
                </h2>
                <span className="text-[10px] font-bold tracking-[0.2em] text-[var(--pf-saffron)] uppercase">
                  {t('Empowering Every Voice', 'ప్రతి గొంతుకకు సాధికారత')}
                </span>
              </div>
            </Link>
            <p className="text-sm leading-relaxed text-zinc-300 max-w-xs">
              {t("India's trusted platform for transparent community news and public accountability. Delivering truth, driving progress.", "భారతదేశం యొక్క విశ్వసనీయ వేదిక. పారదర్శకమైన కమ్యూనిటీ వార్తలు మరియు ప్రజా జవాబుదారీతనం కోసం.")}
            </p>
            {/* Social links — FIX: now have actual hrefs */}
            <div className="flex items-center gap-3">
              {SOCIAL_LINKS.map(s => (
                <a
                  key={s.name}
                  href={s.href}
                  target="_blank"
                  rel="noopener noreferrer"
                  title={s.name}
                  className="w-9 h-9 rounded-full border border-zinc-700 flex items-center justify-center hover:border-[var(--pf-saffron)] hover:text-[var(--pf-saffron)] hover:bg-[var(--pf-saffron)]/10 transition-all duration-200"
                >
                  <s.icon />
                </a>
              ))}
            </div>
          </div>

          {/* Sections */}
          <div className="md:col-span-2">
            <h4 className="text-[11px] font-black uppercase tracking-[0.2em] text-[var(--pf-saffron)] mb-5">{t("Sections", "విభాగాలు")}</h4>
            <ul className="space-y-3 text-[13px]">
              <li>
                <a href="/" className="text-zinc-400 hover:text-white hover:translate-x-1 transition-all inline-block">
                  {t("Home", "హోమ్")}
                </a>
              </li>
              {cats.map(cat => (
                <li key={cat}>
                  <a href={`/news?category=${cat}`} className="text-zinc-400 hover:text-white hover:translate-x-1 transition-all inline-block">
                    {cat}
                  </a>
                </li>
              ))}
              <li>
                <a href="/telugu" className="text-[var(--pf-saffron)] hover:text-white transition-all inline-block telugu font-bold">
                  తెలుగు వార్తలు
                </a>
              </li>
              <li>
                <Link href="/wishes" className="text-rose-400 hover:text-white transition-all inline-block font-bold">
                  {t("Wishes & Greetings", "శుభాకాంక్షలు")}
                </Link>
              </li>
            </ul>
          </div>

          {/* Company */}
          <div className="md:col-span-2">
            <h4 className="text-[11px] font-black uppercase tracking-[0.2em] text-[var(--pf-green)] mb-5">{t("Company", "కంపెనీ")}</h4>
            <ul className="space-y-3 text-[13px]">
              {["About Us", "Our Mission", "Privacy Policy", "Terms of Use", "Contact Us", "Advertise"].map(item => (
                <li key={item}>
                  <a href="#" className="text-zinc-400 hover:text-white hover:translate-x-1 transition-all inline-block">
                    {item}
                  </a>
                </li>
              ))}
            </ul>
          </div>

          {/* Newsletter */}
          <div className="md:col-span-4">
            <div className="p-6 bg-white/5 border border-white/10 rounded-xl">
              <div className="tricolor-stripe rounded-full mb-4 w-16" />
              <h4 className="text-lg font-black text-white mb-2" style={{ fontFamily: "var(--font-headline)" }}>
                {t("The Morning Brief", "మార్నింగ్ బ్రీఫ్")}
              </h4>
              <p className="text-sm text-zinc-300 mb-5 leading-relaxed">
                {t("Important stories from India and the world, delivered every morning.", "భారతదేశం మరియు ప్రపంచం నుండి ముఖ్యమైన వార్తలు, ప్రతి ఉదయం మీ ముందుకు.")}
              </p>
              <div className="flex gap-2">
                <input
                  className="flex-1 bg-white/10 border border-white/20 text-white text-sm px-4 py-2.5 rounded-lg placeholder:text-zinc-500 focus:outline-none focus:ring-2 focus:ring-[var(--pf-saffron)]/40 focus:border-[var(--pf-saffron)] transition-all"
                  placeholder="your@email.com"
                />
                <button className="bg-[var(--pf-saffron)] hover:bg-[var(--pf-orange)] text-white font-bold text-[11px] uppercase px-5 py-2.5 rounded-lg tracking-wider transition-colors whitespace-nowrap">
                  {t("Subscribe", "సబ్స్క్రైబ్")}
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Bottom bar */}
        <div className="tricolor-stripe-bottom mb-8 opacity-30" />
        <div className="flex flex-col md:flex-row items-center justify-between gap-3 text-[11px] font-medium">
          <span className="text-zinc-500">© 2026 Peoples Feedback Media Pvt Ltd. All rights reserved.</span>
          <div className="flex items-center gap-2 text-zinc-400">
            <div className="w-2 h-2 bg-[var(--pf-green)] rounded-full animate-pulse" />
            <Globe className="w-3.5 h-3.5" />
            <span>India Edition</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
