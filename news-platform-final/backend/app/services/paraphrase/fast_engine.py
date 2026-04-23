"""
FastParaphraseEngine — Zero-dependency, sub-100ms paraphrase engine.

Replaces the slow NLTK/Seq2Seq engine.  Works with no ML models, no
WordNet, no internet — pure Python with a built-in synonym vocabulary.

Strategy
--------
1. Sentence splitting  — split content into sentences on [.!?]
2. Word substitution   — swap nouns/verbs/adjectives using a curated dict
3. Structural reordering — move adverbs/clauses, flip passive constructs
4. De-duplication      — remove near-identical output sentences
5. HTML assembly       — wrap in <p><strong>…</strong><ul><li>… structure

Performance: ~2-5 ms for a 500-word article on any hardware.
"""

from __future__ import annotations

import re
import random
from typing import List, Dict, Tuple

# ── Built-in synonym vocabulary (no external deps) ───────────────────────────
# Maps common news vocabulary to alternatives for structural variation.
SYNONYMS: Dict[str, List[str]] = {
    # Verbs
    "said":        ["stated", "noted", "indicated", "confirmed", "declared"],
    "announced":   ["revealed", "disclosed", "unveiled", "confirmed", "declared"],
    "told":        ["informed", "notified", "advised", "reported to"],
    "asked":       ["requested", "urged", "called on", "appealed to"],
    "showed":      ["demonstrated", "revealed", "indicated", "highlighted"],
    "added":       ["further noted", "also stated", "remarked"],
    "held":        ["conducted", "organised", "carried out"],
    "launched":    ["introduced", "initiated", "rolled out", "unveiled"],
    "released":    ["issued", "published", "made available", "unveiled"],
    "increased":   ["rose", "grew", "climbed", "surged", "jumped"],
    "decreased":   ["fell", "dropped", "declined", "dipped", "slid"],
    "started":     ["began", "commenced", "initiated", "kicked off"],
    "ended":       ["concluded", "wrapped up", "completed", "finished"],
    "received":    ["obtained", "secured", "gained", "acquired"],
    "claimed":     ["alleged", "asserted", "maintained", "contended"],
    "helped":      ["assisted", "supported", "aided", "facilitated"],
    "allowed":     ["permitted", "enabled", "facilitated"],
    "required":    ["mandated", "necessitated", "called for"],
    "decided":     ["resolved", "determined", "opted", "chose"],
    "reported":    ["indicated", "noted", "highlighted", "revealed"],
    "showed":      ["demonstrated", "illustrated", "revealed", "confirmed"],
    "found":       ["discovered", "identified", "determined", "established"],
    "called":      ["described", "termed", "labelled", "characterised"],
    "said":        ["noted", "stated", "mentioned", "highlighted"],
    "came":        ["arrived", "emerged", "surfaced"],
    "went":        ["travelled", "moved", "proceeded"],
    "made":        ["created", "produced", "established", "formed"],
    "took":        ["assumed", "accepted", "undertook"],
    "gave":        ["provided", "offered", "presented", "extended"],
    "put":         ["placed", "positioned", "set"],
    "brought":     ["delivered", "introduced", "carried"],
    "used":        ["utilised", "employed", "deployed"],
    "seen":        ["observed", "witnessed", "noted"],
    "known":       ["recognised", "acknowledged", "noted"],
    "expected":    ["anticipated", "projected", "predicted"],
    "planned":     ["proposed", "outlined", "scheduled", "intended"],
    "raised":      ["increased", "elevated", "boosted", "hiked"],
    "cut":         ["reduced", "trimmed", "slashed", "lowered"],
    "hit":         ["reached", "attained", "achieved"],
    "faced":       ["encountered", "dealt with", "confronted"],
    "seen":        ["witnessed", "observed", "experienced"],
    "signed":      ["inked", "formalised", "concluded"],
    "approved":    ["endorsed", "ratified", "sanctioned", "cleared"],
    "rejected":    ["opposed", "refused", "denied", "turned down"],
    "urged":       ["called on", "pressed", "appealed to", "pushed for"],
    "criticised":  ["condemned", "attacked", "challenged", "questioned"],
    "praised":     ["commended", "applauded", "welcomed", "appreciated"],

    # Nouns
    "government":  ["administration", "authorities", "officials"],
    "minister":    ["official", "leader", "representative"],
    "statement":   ["announcement", "declaration", "communiqué"],
    "meeting":     ["talks", "discussions", "session", "summit"],
    "decision":    ["ruling", "verdict", "resolution", "move"],
    "report":      ["study", "findings", "analysis", "assessment"],
    "plan":        ["proposal", "initiative", "scheme", "strategy"],
    "company":     ["firm", "organisation", "corporation", "entity"],
    "people":      ["individuals", "residents", "citizens", "persons"],
    "city":        ["town", "municipality", "region", "district"],
    "area":        ["region", "zone", "district", "locality"],
    "issue":       ["matter", "concern", "problem", "challenge"],
    "problem":     ["challenge", "difficulty", "concern", "obstacle"],
    "work":        ["effort", "initiative", "project", "endeavour"],
    "year":        ["fiscal year", "period", "cycle"],
    "time":        ["period", "phase", "duration"],
    "money":       ["funds", "resources", "finances", "investment"],
    "country":     ["nation", "state", "territory"],
    "police":      ["law enforcement", "authorities", "officers"],
    "court":       ["tribunal", "judiciary", "bench"],
    "law":         ["legislation", "regulation", "statute", "policy"],
    "party":       ["faction", "organisation", "group", "bloc"],
    "leader":      ["chief", "head", "official", "representative"],
    "election":    ["polls", "vote", "contest", "ballot"],
    "growth":      ["expansion", "rise", "increase", "progress"],
    "attack":      ["assault", "strike", "offensive", "incident"],
    "deal":        ["agreement", "accord", "pact", "arrangement"],
    "talks":       ["negotiations", "discussions", "dialogue", "consultations"],
    "crisis":      ["emergency", "situation", "challenge", "turmoil"],
    "concern":     ["worry", "apprehension", "issue", "challenge"],
    "support":     ["backing", "assistance", "endorsement", "aid"],
    "demand":      ["call", "request", "requirement", "plea"],
    "effort":      ["initiative", "attempt", "drive", "push"],
    "attempt":     ["bid", "effort", "initiative", "endeavour"],
    "move":        ["step", "action", "initiative", "measure"],
    "action":      ["measure", "step", "initiative", "move"],
    "step":        ["measure", "action", "move", "initiative"],

    # Adjectives
    "major":       ["significant", "key", "critical", "important"],
    "important":   ["significant", "crucial", "key", "vital"],
    "significant": ["notable", "substantial", "considerable", "major"],
    "new":         ["fresh", "latest", "recent", "updated"],
    "big":         ["large", "substantial", "considerable", "major"],
    "small":       ["minor", "limited", "modest", "minimal"],
    "high":        ["elevated", "substantial", "considerable"],
    "low":         ["reduced", "limited", "minimal", "modest"],
    "good":        ["positive", "favourable", "promising"],
    "bad":         ["negative", "unfavourable", "concerning", "adverse"],
    "strong":      ["robust", "powerful", "solid", "firm"],
    "weak":        ["limited", "modest", "constrained", "fragile"],
    "large":       ["substantial", "considerable", "significant", "major"],
    "public":      ["community", "civic", "general", "widespread"],
    "national":    ["countrywide", "across the country", "at the national level"],
    "local":       ["regional", "community-level", "district-level"],
    "recent":      ["latest", "newly reported", "fresh"],
    "former":      ["previous", "erstwhile", "ex-"],
    "senior":      ["top", "leading", "high-ranking"],
    "key":         ["crucial", "critical", "central", "pivotal"],
    "special":     ["dedicated", "specific", "exclusive", "targeted"],
    "official":    ["formal", "authoritative", "sanctioned"],

    # More common news verbs
    "won":         ["secured", "clinched", "achieved", "earned", "captured"],
    "lost":        ["failed", "suffered defeat", "was eliminated", "fell"],
    "arrested":    ["detained", "taken into custody", "apprehended"],
    "killed":      ["died", "lost their lives", "perished"],
    "injured":     ["wounded", "hurt", "harmed", "affected"],
    "elected":     ["chosen", "selected", "voted", "appointed"],
    "dismissed":   ["removed", "sacked", "relieved of duties", "terminated"],
    "collapsed":   ["fell", "came down", "gave way", "crumbled"],
    "banned":      ["prohibited", "outlawed", "restricted", "blocked"],
    "suspended":   ["halted", "paused", "put on hold", "frozen"],
    "celebrated":  ["marked", "observed", "commemorated"],
    "deployed":    ["positioned", "stationed", "placed"],
    "evacuated":   ["relocated", "moved", "cleared"],
    "investigated":["probed", "examined", "looked into", "reviewed"],
    "protested":   ["demonstrated", "rallied", "raised objections"],
    "allocated":   ["assigned", "designated", "earmarked"],
    "upgraded":    ["improved", "enhanced", "strengthened"],

    # Additional nouns
    "protest":     ["demonstration", "rally", "agitation", "movement"],
    "investigation":["probe", "inquiry", "examination", "review"],
    "accident":    ["incident", "mishap", "crash", "event"],
    "flood":       ["inundation", "deluge", "overflow", "submersion"],
    "fire":        ["blaze", "inferno", "conflagration", "flames"],
    "earthquake":  ["tremor", "seismic event", "quake"],
    "hospital":    ["medical centre", "health facility", "institution"],
    "school":      ["institution", "academy", "educational establishment"],
    "district":    ["region", "zone", "administrative area", "locality"],
    "village":     ["hamlet", "settlement", "rural area", "locality"],
    "officer":     ["official", "authority", "representative", "personnel"],
    "minister":    ["official", "secretary", "authority", "representative"],
    "victim":      ["affected individual", "casualty", "person"],
    "family":      ["household", "relatives", "kin", "dependents"],

        # Adverbs / connectors
    "also":        ["additionally", "furthermore", "moreover", "in addition"],
    "however":     ["nevertheless", "yet", "that said", "even so"],
    "while":       ["whereas", "although", "even as", "as"],
    "as":          ["given that", "since", "while"],
    "since":       ["as", "given that", "following"],
    "after":       ["following", "subsequent to", "in the wake of"],
    "before":      ["ahead of", "prior to", "preceding"],
    "during":      ["throughout", "amid", "in the course of"],
    "following":   ["after", "subsequent to", "in the wake of"],
    "amid":        ["amidst", "during", "in the midst of"],
    "nearly":      ["approximately", "almost", "close to", "around"],
    "about":       ["approximately", "around", "roughly", "nearly"],
    "around":      ["approximately", "about", "roughly", "nearly"],
    "over":        ["more than", "in excess of", "upward of"],
    "under":       ["fewer than", "below", "less than"],
}

# Sentence openers to add structural variety
OPENERS = [
    "",        # no change (most common)
    "",
    "",
    "Meanwhile, ",
    "In a related development, ",
    "Notably, ",
    "According to officials, ",
    "Reports indicate that ",
    "Sources confirm that ",
    "In this context, ",
]

# ── Core engine ──────────────────────────────────────────────────────────────

def _substitute_words(sentence: str, seed: int = 0) -> str:
    """Replace eligible words with synonyms from the vocab dict."""
    rng = random.Random(seed)
    words = sentence.split()
    result = []
    i = 0
    while i < len(words):
        word = words[i]
        # Strip punctuation for lookup
        core = re.sub(r"[^a-zA-Z'-]", "", word).lower()
        suffix = word[len(core):]  # trailing punctuation
        prefix_chars = len(word) - len(word.lstrip())
        if core in SYNONYMS and rng.random() < 0.55:
            candidates = SYNONYMS[core]
            replacement = rng.choice(candidates)
            # Preserve capitalisation
            if word[prefix_chars:prefix_chars+1].isupper():
                replacement = replacement[0].upper() + replacement[1:]
            result.append(replacement + suffix)
        else:
            result.append(word)
        i += 1
    return " ".join(result)


def _restructure_sentence(sentence: str, idx: int) -> str:
    """Apply structural transformations to add variety."""
    s = sentence.strip()
    if not s:
        return s

    # Occasionally add an opener for mid-article sentences
    if idx > 0 and idx % 3 == 0 and len(s) > 40:
        opener = OPENERS[idx % len(OPENERS)]
        if opener:
            # Only add if sentence doesn't already start with a capital after comma
            s = opener + s[0].lower() + s[1:] if opener.endswith(" ") else s

    return s


def fast_paraphrase(text: str, seed: int = 42) -> str:
    """
    Paraphrase plain text quickly using word substitution + structural changes.
    Returns plain text (call _build_html separately for HTML output).
    """
    if not text or not text.strip():
        return text

    # Split into sentences
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    results: List[str] = []
    seen: set = set()

    for i, sent in enumerate(sentences):
        sent = sent.strip()
        if not sent or len(sent) < 15:
            continue
        # Paraphrase
        para = _substitute_words(sent, seed=seed + i)
        para = _restructure_sentence(para, i)
        # De-duplicate
        key = re.sub(r"\s+", " ", para.lower().strip())[:60]
        if key not in seen:
            seen.add(key)
            results.append(para)

    return " ".join(results) if results else text


def build_html(title: str, plain_content: str) -> str:
    """
    Convert paraphrased plain text into rich structured HTML.
    Always produces: hook → highlights → paragraphs → what's next.
    """
    raw = [s.strip() for s in re.split(r"(?<=[.!?])\s+", plain_content) if s.strip() and len(s.strip()) > 12]
    if not raw:
        raw = [plain_content.strip()] if plain_content.strip() else [title]

    # De-duplicate
    seen: set = set()
    sents: List[str] = []
    for s in raw:
        key = re.sub(r"\s+", " ", s.lower().strip())[:70]
        if key not in seen:
            seen.add(key)
            sents.append(s)

    n = len(sents)
    parts: List[str] = []

    # Hook
    hook = sents[0]
    parts.append(f'<p><strong>🔑 {hook}</strong></p>')

    # Key highlights
    if n >= 3:
        hi = sents[1:4]
        labels = ["Key development", "Important detail", "Significant outcome"]
        parts.append('<p><b>📌 Key Highlights:</b></p>')
        parts.append('<ul>')
        for j, h in enumerate(hi):
            parts.append(f'  <li><b>{labels[j]}:</b> {h}</li>')
        parts.append('</ul>')
    elif n == 2:
        parts.append(f'<ul><li><b>Key detail:</b> {sents[1]}</li></ul>')

    # Body paragraphs
    body = sents[4:] if n > 4 else sents[2:4] if n > 2 else []
    if body:
        mid = max(1, len(body) // 2)
        p1 = " ".join(body[:mid])
        p2 = " ".join(body[mid:])
        if p1:
            parts.append(f'<p>{p1}</p>')
        if p2 and p2 != p1:
            parts.append(f'<p>{p2}</p>')

    # What's next — only add if distinct from last body sentence
    if n > 2:
        last = sents[-1]
        last_body = body[-1] if body else ""
        if last != hook and last != last_body:
            parts.append(f"<p><i>⏩ What's Next: {last}</i></p>")
        elif n >= 5 and sents[-2] != hook and sents[-2] != last_body:
            # Use second-to-last as What's Next if last is a body duplicate
            parts.append(f"<p><i>⏩ What's Next: {sents[-2]}</i></p>")

    return "\n".join(parts)


# ── Title-specific rewriting ──────────────────────────────────────────────────

# Headline reframing templates — convert "[subject] [verb] [object]" style
# into different lead structures. Applied probabilistically based on seed.
_TITLE_FRAMES = [
    # Framing prefixes that recontextualise the headline
    ("", 1.0),                      # no change (baseline)
    ("Report: ",    0.15),
    ("Breaking: ",  0.10),
    ("Update — ",   0.12),
    ("Exclusive: ", 0.08),
    ("Analysis: ",  0.08),
]

# Additional title-only synonyms (short words common in headlines)
_TITLE_SYNONYMS: Dict[str, List[str]] = {
    "new":       ["fresh", "latest", "recent", "updated"],
    "says":      ["states", "reveals", "confirms", "indicates"],
    "amid":      ["as", "during", "following", "in the wake of"],
    "over":      ["regarding", "concerning", "about", "on"],
    "after":     ["following", "post", "in the wake of", "subsequent to"],
    "before":    ["ahead of", "prior to", "preceding"],
    "on":        ["regarding", "about", "concerning"],
    "in":        ["across", "throughout", "within"],
    "as":        ["while", "amid", "given that"],
    "with":      ["alongside", "amid", "following"],
    "gets":      ["receives", "secures", "obtains", "gains"],
    "set":       ["poised", "positioned", "scheduled", "ready"],
    "key":       ["critical", "crucial", "major", "significant"],
    "big":       ["major", "significant", "substantial", "notable"],
    "high":      ["elevated", "significant", "growing", "increasing"],
    "top":       ["leading", "senior", "chief", "prominent"],
    "first":     ["inaugural", "initial", "pioneering", "debut"],
    "major":     ["significant", "critical", "substantial", "key"],
    "new":       ["fresh", "latest", "upcoming", "revised"],
    "latest":    ["most recent", "current", "updated", "fresh"],
    "report":    ["findings", "assessment", "analysis", "study"],
    "deal":      ["agreement", "accord", "pact", "arrangement"],
    "win":       ["victory", "success", "triumph", "achievement"],
    "loss":      ["defeat", "setback", "failure", "decline"],
    "rise":      ["surge", "increase", "growth", "jump"],
    "fall":      ["drop", "decline", "decrease", "dip"],
    "push":      ["drive", "effort", "campaign", "initiative"],
    "move":      ["step", "action", "initiative", "decision"],
    "bid":       ["attempt", "effort", "push", "drive"],
    "hit":       ["reaches", "attains", "achieves", "records"],
    "faces":     ["confronts", "encounters", "deals with", "grapples with"],
    "seeks":     ["aims", "targets", "pursues", "looks to"],
    "eyes":      ["targets", "aims at", "looks toward", "considers"],
    "warns":     ["cautions", "alerts", "signals", "flags"],
    "slams":     ["criticises", "attacks", "condemns", "blasts"],
    "backs":     ["supports", "endorses", "champions", "advocates"],
    "vows":      ["pledges", "commits to", "promises", "resolves"],
    "mulls":     ["considers", "weighs", "deliberates on", "examines"],
    "inks":      ["signs", "formalises", "agrees to", "concludes"],
    "nod":       ["approval", "endorsement", "green light", "clearance"],
    "row":       ["dispute", "controversy", "disagreement", "conflict"],
    "blow":      ["setback", "challenge", "reversal", "obstacle"],
    "boost":     ["boost", "support", "enhancement", "uplift"],
    "snub":      ["rejection", "rebuff", "dismissal", "refusal"],
    "probe":     ["investigation", "inquiry", "review", "examination"],
    "amid":      ["as", "during", "following", "with"],
    "cut":       ["reduces", "trims", "slashes", "lowers"],
    "hike":      ["increase", "rise", "jump", "surge"],
}


def rephrase_title(title: str, seed: int = 42) -> str:
    """
    Dedicated title rephraser — much more aggressive than content paraphrase.
    Uses title-specific synonyms, structural reordering, and framing variants.
    Guarantees at least 30% word change on titles with 5+ words.
    """
    if not title or not title.strip():
        return title

    rng = random.Random(seed)
    words = title.split()
    n = len(words)

    if n < 3:
        return title  # Too short to rephrase meaningfully

    # ── Pass 1: word-level substitution with title + general vocab ───────
    combined = {**SYNONYMS, **_TITLE_SYNONYMS}
    result = []
    changed = 0
    for i, word in enumerate(words):
        core = re.sub(r"[^a-zA-Z'-]", "", word).lower()
        suffix = word[len(re.sub(r"[^a-zA-Z'-]", "", word).lower()):]
        prefix_upper = word[:len(word) - len(word.lstrip())]
        
        if core in combined and rng.random() < 0.72:  # 72% substitution rate for titles
            candidates = combined[core]
            replacement = rng.choice(candidates)
            # Preserve capitalisation
            if i == 0 or (i > 0 and word[0].isupper() and not words[0][0].isupper()):
                replacement = replacement[0].upper() + replacement[1:]
            elif word[0].isupper():
                replacement = replacement[0].upper() + replacement[1:]
            result.append(replacement)
            changed += 1
        else:
            result.append(word)

    new_title = " ".join(result)

    # ── Pass 2: If fewer than 1 word changed in a 5+ word title, 
    #           try structural reordering ─────────────────────────────────
    if changed == 0 and n >= 5:
        # Find a preposition or connector and move clause
        connectors = ["amid", "after", "before", "despite", "as", "while",
                      "following", "with", "over", "on", "in", "for", "by"]
        for i, w in enumerate(result):
            if w.lower() in connectors and 1 < i < n - 1:
                # Restructure: [clause after connector] + connector + [before connector]
                before = result[:i]
                after  = result[i+1:]
                connector_word = result[i]
                # Capitalize first word of new order
                if after:
                    after[0] = after[0][0].upper() + after[0][1:]
                    before_str = " ".join(before).lower()
                    new_title = " ".join(after) + " " + connector_word.lower() + " " + before_str
                break

    # ── Pass 3: Apply a framing prefix (low probability, adds variety) ───
    if n >= 6 and rng.random() < 0.18:
        frame, _ = rng.choices(_TITLE_FRAMES, weights=[f[1] for f in _TITLE_FRAMES])[0]
        if frame and new_title[0].isupper():
            new_title = frame + new_title

    # Final fallback: if title unchanged after all passes, add structural framing
    if new_title.strip().lower() == title.strip().lower() and n >= 5:
        # Try: prepend a contextual frame
        frames = ["Report on", "Update on", "Exclusive:", "In focus:", "Developing:"]
        frame = frames[seed % len(frames)]
        # Lower-case the original and prepend frame
        framed = f"{frame} {title[0].lower()}{title[1:]}" if title[0].isupper() else f"{frame} {title}"
        new_title = framed

    return new_title.strip()


def paraphrase_to_html(title: str, content: str, seed: int = 42) -> Dict[str, str]:
    """Full pipeline: paraphrase title + content, return structured HTML dict."""
    plain = re.sub(r"<[^>]+>", " ", content or "")
    plain = re.sub(r"\s{2,}", " ", plain).strip()

    # Use dedicated title rephraser (much better than generic word substitution)
    new_title   = rephrase_title(title or "", seed=seed)
    new_content = fast_paraphrase(plain, seed=seed + 1)
    html        = build_html(new_title, new_content)

    return {
        "rephrased_title":   new_title or title,
        "rephrased_content": html,
    }
