
import { useEffect } from "react";

interface SEOProps {
  title?: string;
  description?: string;
  image?: string;
  url?: string;
  type?: "website" | "article";
  articleData?: {
    publishedTime?: string;
    author?: string;
    section?: string;
    tags?: string[];
  };
}

export default function SEO({ 
  title, 
  description, 
  image = "/pf-logo.png", 
  url, 
  type = "website",
  articleData 
}: SEOProps) {
  const siteName = "Peoples Feedback";
  const fullTitle = title ? `${title} | ${siteName}` : siteName;
  const siteUrl = "https://peoples-feedback.com";
  const currentUrl = url ? `${siteUrl}${url}` : siteUrl;
  const defaultDescription = "Peoples Feedback - Empowering Every Voice. Providing the latest news, updates, and community insights from across the globe and Telugu regions.";

  useEffect(() => {
    // 1. Update Basic Meta
    document.title = fullTitle;
    
    const metaDesc = document.querySelector('meta[name="description"]');
    if (metaDesc) {
      metaDesc.setAttribute("content", description || defaultDescription);
    } else {
      const meta = document.createElement("meta");
      meta.name = "description";
      meta.content = description || defaultDescription;
      document.head.appendChild(meta);
    }

    // 2. Open Graph Tags
    const ogTags = {
      "og:title": fullTitle,
      "og:description": description || defaultDescription,
      "og:image": image.startsWith('http') ? image : `${siteUrl}${image}`,
      "og:url": currentUrl,
      "og:type": type,
      "og:site_name": siteName,
    };

    Object.entries(ogTags).forEach(([property, content]) => {
      let el = document.querySelector(`meta[property="${property}"]`);
      if (!el) {
        el = document.createElement("meta");
        el.setAttribute("property", property);
        document.head.appendChild(el);
      }
      el.setAttribute("content", content);
    });

    // 3. Twitter Card Tags
    const twitterTags = {
      "twitter:card": "summary_large_image",
      "twitter:title": fullTitle,
      "twitter:description": description || defaultDescription,
      "twitter:image": image.startsWith('http') ? image : `${siteUrl}${image}`,
    };

    Object.entries(twitterTags).forEach(([name, content]) => {
      let el = document.querySelector(`meta[name="${name}"]`);
      if (!el) {
        el = document.createElement("meta");
        el.setAttribute("name", name);
        document.head.appendChild(el);
      }
      el.setAttribute("content", content);
    });

    // 4. Structured Data (JSON-LD)
    const existingScript = document.getElementById("structured-data-jsonld");
    if (existingScript) existingScript.remove();

    const script = document.createElement("script");
    script.id = "structured-data-jsonld";
    script.type = "application/ld+json";

    let jsonLd: any = {
      "@context": "https://schema.org",
      "@type": type === "article" ? "NewsArticle" : "WebSite",
      "name": siteName,
      "url": siteUrl,
      "potentialAction": {
        "@type": "SearchAction",
        "target": `${siteUrl}/news?search={search_term_string}`,
        "query-input": "required name=search_term_string"
      }
    };

    if (type === "article" && articleData) {
      jsonLd = {
        "@context": "https://schema.org",
        "@type": "NewsArticle",
        "headline": title,
        "image": [ogTags["og:image"]],
        "datePublished": articleData.publishedTime,
        "author": [{
          "@type": "Person",
          "name": articleData.author || "Peoples Feedback Reporter"
        }],
        "publisher": {
          "@type": "Organization",
          "name": siteName,
          "logo": {
            "@type": "ImageObject",
            "url": `${siteUrl}/pf-logo.png`
          }
        },
        "description": description || defaultDescription
      };
    }

    script.text = JSON.stringify(jsonLd);
    document.head.appendChild(script);

    // 5. Canonical Link
    let canonical = document.querySelector('link[rel="canonical"]');
    if (!canonical) {
      canonical = document.createElement("link");
      canonical.setAttribute("rel", "canonical");
      document.head.appendChild(canonical);
    }
    canonical.setAttribute("href", currentUrl);

  }, [fullTitle, description, image, currentUrl, type, articleData]);

  return null;
}
