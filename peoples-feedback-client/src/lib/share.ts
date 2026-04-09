/**
 * Social Sharing Utilities
 * Builds platform-specific share URLs for news articles.
 */

export interface ShareData {
  url: string;
  title: string;
  summary?: string;
  imageUrl?: string;
}

/** Facebook share via sharer.php */
export const facebookShareUrl = (d: ShareData): string =>
  `https://www.facebook.com/sharer/sharer.php?u=${enc(d.url)}&quote=${enc(d.title)}`;

/** X (Twitter) share via intent/tweet */
export const twitterShareUrl = (d: ShareData): string =>
  `https://twitter.com/intent/tweet?url=${enc(d.url)}&text=${enc(d.title)}&via=PeoplesFeedback`;

/** WhatsApp share via wa.me */
export const whatsappShareUrl = (d: ShareData): string =>
  `https://wa.me/?text=${enc(`${d.title}\n\n${d.url}`)}`;

/** LinkedIn share */
export const linkedinShareUrl = (d: ShareData): string =>
  `https://www.linkedin.com/sharing/share-offsite/?url=${enc(d.url)}`;

/** Telegram share */
export const telegramShareUrl = (d: ShareData): string =>
  `https://t.me/share/url?url=${enc(d.url)}&text=${enc(d.title)}`;

/** Email share */
export const emailShareUrl = (d: ShareData): string =>
  `mailto:?subject=${enc(d.title)}&body=${enc(`${d.title}\n\nRead more: ${d.url}`)}`;

/** Copy link to clipboard */
export const copyToClipboard = async (text: string): Promise<boolean> => {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    // Fallback for older browsers
    const ta = document.createElement('textarea');
    ta.value = text;
    ta.style.position = 'fixed';
    ta.style.left = '-9999px';
    document.body.appendChild(ta);
    ta.select();
    const ok = document.execCommand('copy');
    document.body.removeChild(ta);
    return ok;
  }
};

/** Native Web Share API (mobile) */
export const canNativeShare = (): boolean =>
  typeof navigator !== 'undefined' && !!navigator.share;

export const nativeShare = async (d: ShareData): Promise<boolean> => {
  try {
    await navigator.share({ title: d.title, text: d.summary || d.title, url: d.url });
    return true;
  } catch {
    return false;
  }
};

/** Open a share URL in a centered popup */
export const openSharePopup = (url: string, name = 'share'): void => {
  const w = 600, h = 500;
  const left = (screen.width - w) / 2;
  const top = (screen.height - h) / 2;
  window.open(url, name, `width=${w},height=${h},left=${left},top=${top},toolbar=no,menubar=no`);
};

/** Instagram — no direct share API; copies link + opens Instagram */
export const instagramShare = async (d: ShareData): Promise<void> => {
  await copyToClipboard(d.url);
  // On mobile, try to open Instagram app
  if (/Android|iPhone|iPad/i.test(navigator.userAgent)) {
    window.open('instagram://app', '_blank');
  }
};

function enc(s: string): string { return encodeURIComponent(s); }
