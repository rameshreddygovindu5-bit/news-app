import { useEffect } from "react";

interface Props {
  slot: string;
  format?: "auto" | "fluid" | "rectangle";
  responsive?: boolean;
  style?: React.CSSProperties;
  className?: string;
}

/**
 * GoogleAdUnit — Reusable component for AdSense ads.
 * Requires VITE_GOOGLE_ADSENSE_ID in .env
 */
export const GoogleAdUnit = ({ slot, format = "auto", responsive = true, style, className }: Props) => {
  const publisherId = import.meta.env.VITE_GOOGLE_ADSENSE_ID || "ca-pub-XXXXXXXXXXXXXXXX";

  useEffect(() => {
    try {
      // @ts-ignore
      (window.adsbygoogle = window.adsbygoogle || []).push({});
    } catch (e) {
      console.error("AdSense error:", e);
    }
  }, []);

  return (
    <div className={`ad-container my-4 overflow-hidden flex justify-center ${className}`} style={style}>
      <ins
        className="adsbygoogle"
        style={{ display: "block", minWidth: "250px", ...style }}
        data-ad-client={publisherId}
        data-ad-slot={slot}
        data-ad-format={format}
        data-full-width-responsive={responsive ? "true" : "false"}
      />
    </div>
  );
};
