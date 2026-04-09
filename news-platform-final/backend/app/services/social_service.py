"""
Social Media Posting Service — Real API integrations.

Supports:
  - Facebook Page posting (Graph API v18)
  - Instagram Business posting (via Facebook Graph API)
  - X / Twitter posting (API v2 with OAuth 1.0a)
  - WhatsApp Business messaging (Cloud API)

Each platform is independent — if API keys missing, that platform is skipped.
All errors are non-fatal (won't break the pipeline).

Setup (add keys to .env):
  FB_PAGE_ACCESS_TOKEN=...   FB_PAGE_ID=...
  IG_BUSINESS_ACCOUNT_ID=...
  X_API_KEY=... X_API_SECRET=... X_ACCESS_TOKEN=... X_ACCESS_SECRET=...
  WA_PHONE_NUMBER_ID=... WA_ACCESS_TOKEN=... WA_RECIPIENT_GROUP=91xxxxxxxxxx,91yyyyyyyyyy
"""

import re
import logging
import hashlib
import hmac
import time
import urllib.parse
import base64
from typing import Dict
import requests

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _strip_html(html: str) -> str:
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', html)).strip()


def _truncate(text: str, n: int = 280) -> str:
    return text if len(text) <= n else text[:n - 3].rsplit(' ', 1)[0] + '...'


class SocialService:

    def post_to_all(self, article_id: int, title: str, content: str, url: str) -> Dict:
        t = _strip_html(title)
        c = _strip_html(content)
        results = {
            "facebook": self.post_to_facebook(article_id, t, c, url),
            "instagram": self.post_to_instagram(article_id, t, c, url),
            "x": self.post_to_x(article_id, t, url),
            "whatsapp": self.post_to_whatsapp(article_id, t, url),
        }
        posted = sum(1 for v in results.values() if v.get("success"))
        logger.info(f"[SOCIAL] Article {article_id}: posted to {posted}/4 platforms")
        return results

    # ─── FACEBOOK PAGE ───
    def post_to_facebook(self, article_id: int, title: str, content: str, url: str) -> Dict:
        token = settings.FB_PAGE_ACCESS_TOKEN
        page_id = settings.FB_PAGE_ID
        if not token or not page_id:
            logger.debug(f"[FB] Skipped {article_id} — not configured")
            return {"success": False, "reason": "not_configured"}
        try:
            msg = f"{title}\n\n{_truncate(content, 500)}\n\nRead more: {url}"
            resp = requests.post(
                f"https://graph.facebook.com/v18.0/{page_id}/feed",
                data={"message": msg, "link": url, "access_token": token},
                timeout=15)
            data = resp.json()
            if resp.ok and "id" in data:
                logger.info(f"[FB] ✓ Article {article_id}: {data['id']}")
                return {"success": True, "post_id": data["id"]}
            logger.warning(f"[FB] ✗ Article {article_id}: {data.get('error', {}).get('message', data)}")
            return {"success": False, "error": str(data)}
        except Exception as e:
            logger.error(f"[FB] Error {article_id}: {e}")
            return {"success": False, "error": str(e)}

    # ─── INSTAGRAM ───
    def post_to_instagram(self, article_id: int, title: str, content: str, url: str) -> Dict:
        token = settings.FB_PAGE_ACCESS_TOKEN
        ig_id = settings.IG_BUSINESS_ACCOUNT_ID
        if not token or not ig_id:
            logger.debug(f"[IG] Skipped {article_id} — not configured")
            return {"success": False, "reason": "not_configured"}
        try:
            caption = f"{title}\n\n{_truncate(content, 1000)}\n\n#PeoplesFeedback #News #India"
            # Step 1: Create media container
            r1 = requests.post(
                f"https://graph.facebook.com/v18.0/{ig_id}/media",
                data={"caption": caption, "image_url": f"{settings.SOCIAL_SITE_URL}/pf-logo.png", "access_token": token},
                timeout=15)
            d1 = r1.json()
            if "id" not in d1:
                return {"success": False, "error": str(d1)}
            # Step 2: Publish
            r2 = requests.post(
                f"https://graph.facebook.com/v18.0/{ig_id}/media_publish",
                data={"creation_id": d1["id"], "access_token": token},
                timeout=15)
            d2 = r2.json()
            if "id" in d2:
                logger.info(f"[IG] ✓ Article {article_id}: {d2['id']}")
                return {"success": True, "post_id": d2["id"]}
            return {"success": False, "error": str(d2)}
        except Exception as e:
            logger.error(f"[IG] Error {article_id}: {e}")
            return {"success": False, "error": str(e)}

    # ─── X (TWITTER) ───
    def post_to_x(self, article_id: int, title: str, url: str) -> Dict:
        ak, aks = settings.X_API_KEY, settings.X_API_SECRET
        at, ats = settings.X_ACCESS_TOKEN, settings.X_ACCESS_SECRET
        if not all([ak, aks, at, ats]):
            logger.debug(f"[X] Skipped {article_id} — not configured")
            return {"success": False, "reason": "not_configured"}
        try:
            tweet = _truncate(f"{title}\n\n{url}\n\n#PeoplesFeedback #News", 280)
            ep = "https://api.twitter.com/2/tweets"
            nonce = hashlib.sha256(f"{time.time()}".encode()).hexdigest()[:32]
            ts = str(int(time.time()))
            op = {"oauth_consumer_key": ak, "oauth_nonce": nonce, "oauth_signature_method": "HMAC-SHA1",
                  "oauth_timestamp": ts, "oauth_token": at, "oauth_version": "1.0"}
            ps = "&".join(f"{k}={urllib.parse.quote(v, safe='')}" for k, v in sorted(op.items()))
            sb = f"POST&{urllib.parse.quote(ep, safe='')}&{urllib.parse.quote(ps, safe='')}"
            sk = f"{urllib.parse.quote(aks, safe='')}&{urllib.parse.quote(ats, safe='')}"
            sig = base64.b64encode(hmac.new(sk.encode(), sb.encode(), hashlib.sha1).digest()).decode()
            op["oauth_signature"] = sig
            ah = "OAuth " + ", ".join(f'{k}="{urllib.parse.quote(v, safe="")}"' for k, v in op.items())
            resp = requests.post(ep, json={"text": tweet}, headers={"Authorization": ah, "Content-Type": "application/json"}, timeout=15)
            data = resp.json()
            if resp.status_code in (200, 201) and "data" in data:
                logger.info(f"[X] ✓ Article {article_id}: {data['data']['id']}")
                return {"success": True, "tweet_id": data["data"]["id"]}
            logger.warning(f"[X] ✗ Article {article_id}: {data}")
            return {"success": False, "error": str(data)}
        except Exception as e:
            logger.error(f"[X] Error {article_id}: {e}")
            return {"success": False, "error": str(e)}

    # ─── WHATSAPP ───
    def post_to_whatsapp(self, article_id: int, title: str, url: str) -> Dict:
        pid, token = settings.WA_PHONE_NUMBER_ID, settings.WA_ACCESS_TOKEN
        recipients = settings.WA_RECIPIENT_GROUP
        if not pid or not token or not recipients:
            logger.debug(f"[WA] Skipped {article_id} — not configured")
            return {"success": False, "reason": "not_configured"}
        try:
            msg = f"📰 *{title}*\n\n🔗 {url}\n\n— Peoples Feedback News"
            sent = 0
            for phone in recipients.split(","):
                phone = phone.strip()
                if not phone: continue
                resp = requests.post(
                    f"https://graph.facebook.com/v18.0/{pid}/messages",
                    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                    json={"messaging_product": "whatsapp", "to": phone, "type": "text", "text": {"preview_url": True, "body": msg}},
                    timeout=15)
                if resp.ok: sent += 1
                else: logger.warning(f"[WA] Failed {phone}: {resp.text[:200]}")
            logger.info(f"[WA] Article {article_id}: sent to {sent} recipients")
            return {"success": sent > 0, "sent_count": sent}
        except Exception as e:
            logger.error(f"[WA] Error {article_id}: {e}")
            return {"success": False, "error": str(e)}


social_service = SocialService()
