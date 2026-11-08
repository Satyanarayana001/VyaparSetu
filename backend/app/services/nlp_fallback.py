"""Deterministic Hinglish/Hindi/English order parser. This is NOT an LLM: it is a rule-based fallback.

It tokenises the message, splits it into order segments, pulls out quantity + unit (peti/case = case),
separates product-spec numbers ("1 kilo", "250 wala") from quantities, then scores every catalogue
product from keywords derived from the product name plus a small alias table, and the retailer's own aliases.
"""
import re
import unicodedata
from dataclasses import dataclass

from .ai_types import RawLine

_DEV_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")

CASE_WORDS = {"peti", "petti", "pethi", "carton", "cartons", "case", "cases", "cs", "कार्टन", "पेटी", "केस"}
PIECE_WORDS = {"packet", "packets", "pkt", "pkts", "pack", "packs", "piece", "pieces", "pcs", "pc", "dana", "dane",
               "nag", "dabba", "dibba", "पैकेट", "पीस", "दाना", "नग", "डिब्बा"}
KG_WORDS = {"kg", "kgs", "kilo", "kilos", "kilogram", "किलो", "किग्रा", "केजी"}
G_WORDS = {"g", "gm", "gms", "gram", "grams", "gr", "ग्राम", "ग्रा"}
SPEC_SUFFIX = {"wala", "wali", "waala", "wale", "vala", "vali", "wal", "वाला", "वाली", "वाले"}
SIZE_SMALL = {"chhota", "chota", "chhote", "choti", "chhoti", "small", "mini", "छोटा", "छोटे", "छोटी"}
NUMBER_WORDS = {
    "ek": 1, "एक": 1, "one": 1, "do": 2, "दो": 2, "two": 2, "teen": 3, "tin": 3, "तीन": 3, "three": 3,
    "char": 4, "chaar": 4, "चार": 4, "four": 4, "paanch": 5, "panch": 5, "पांच": 5, "पाँच": 5, "five": 5,
    "chhe": 6, "chah": 6, "che": 6, "छह": 6, "छः": 6, "six": 6, "saat": 7, "सात": 7, "seven": 7,
    "aath": 8, "आठ": 8, "eight": 8, "nau": 9, "नौ": 9, "nine": 9, "das": 10, "दस": 10, "ten": 10,
    "barah": 12, "twelve": 12, "pandrah": 15, "fifteen": 15, "bees": 20, "twenty": 20,
}
STOPWORDS = {"bhaiya", "bhaiyya", "bhaiyaji", "bhai", "bhaisahab", "sir", "ji", "please", "plz", "pls", "hi", "hello",
             "namaste", "chahiye", "chahie", "chaiye", "dena", "dedo", "dijiye", "bhejna", "bhejiye", "bhej", "mujhe",
             "humko", "hume", "need", "send", "me", "i", "want", "ka", "ki", "ke", "ko", "wala", "wali", "waala", "wale",
             "bhi", "the", "of", "a", "an", "for", "भैया", "भाई", "जी", "चाहिए", "दे", "का", "की", "के", "को", "मुझे",
             "वाला", "वाली", "वाले", "भेज"}
# Keyword hints per SKU. Anything not listed here falls back to words derived from the product name.
SKU_HINTS: dict[str, dict[str, set[str]]] = {
    "SKU-BS-075": {"strong": {"biscuit", "biscuits", "biskut", "biskit", "biscut", "bisket", "glucose", "glukose",
                              "बिस्कुट", "बिस्किट", "बिस्कीट", "ग्लूकोज"}, "weak": set(), "size": SIZE_SMALL},
    "SKU-DT-1KG": {"strong": {"detergent", "washing", "vashing", "surf", "डिटर्जेंट", "डिटरजेंट", "वॉशिंग", "वाशिंग"},
                   "weak": {"powder", "पाउडर", "kapda", "कपड़े", "kapde"}, "size": set()},
    "SKU-TE-250": {"strong": {"tea", "chai", "chay", "chaay", "चाय", "चायपत्ती"},
                   "weak": {"patti", "pati", "leaf", "पत्ती"}, "size": set()},
}
_GENERIC_NAME_WORDS = {"powder", "leaf", "g", "kg", "case", "pack"}


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).lower().translate(_DEV_DIGITS)
    text = re.sub(r"(?<=\d)(?=[^\W\d_])", " ", text)          # 75g -> 75 g
    text = re.sub(r"(?<=[^\W\d_])-(?=[^\W\d_])", " ", text)  # tea-leaf -> tea leaf
    return text


def tokenize(text: str) -> list[str]:
    toks = re.findall(r"[^\s,;:!?()\[\]{}\"'/\\|+]+", normalize_text(text))
    return [t.strip(".") for t in toks if t.strip(".")]


_NUM_RE = re.compile(r"^-?\d+(\.\d+)?$")


def parse_number(tok: str) -> float | None:
    if _NUM_RE.match(tok):
        v = float(tok)
        return int(v) if v == int(v) and "." not in tok else v
    if tok in NUMBER_WORDS:
        return NUMBER_WORDS[tok]
    return None


def _drop_give_do(toks: list[str]) -> list[str]:
    """'bhej do', 'de do', 'kar do' mean 'send/give', not the number two."""
    out, i = [], 0
    while i < len(toks):
        if toks[i] in {"bhej", "de", "kar", "भेज", "दे", "कर"} and i + 1 < len(toks) and toks[i + 1] in {"do", "दो"}:
            i += 2
            continue
        out.append(toks[i])
        i += 1
    return out


@dataclass
class Segment:
    text: str
    raw_quantity: float | None
    unit: str
    product_tokens: list[str]
    specs_g: list[float]          # weights in grams from "1 kilo", "250 g", "75 gram"
    specs_bare: list[float]       # "250 wala"
    has_size_word: bool
    notes: list[str]


def _is_pair(toks, i, words):
    return i + 1 < len(toks) and parse_number(toks[i]) is not None and toks[i + 1] in words


def analyse_segment(text: str) -> Segment:
    toks = _drop_give_do(tokenize(text))
    used = [False] * len(toks)
    qty: float | None = None
    unit = "unknown"
    specs_g: list[float] = []
    specs_bare: list[float] = []
    notes: list[str] = []

    def spec_follows(i):  # is the number at i a product spec rather than a quantity?
        return i + 1 < len(toks) and (toks[i + 1] in KG_WORDS or toks[i + 1] in G_WORDS or toks[i + 1] in SPEC_SUFFIX)

    # 1. quantity with an explicit packing word
    for words, u in ((CASE_WORDS, "case"), (PIECE_WORDS, "piece")):
        if qty is not None:
            break
        for i in range(len(toks)):
            if _is_pair(toks, i, words) and not spec_follows(i):
                qty, unit, used[i], used[i + 1] = parse_number(toks[i]), u, True, True
                break
            if toks[i] in words and i + 1 < len(toks) and parse_number(toks[i + 1]) is not None and not spec_follows(i + 1):
                qty, unit, used[i], used[i + 1] = parse_number(toks[i + 1]), u, True, True
                break
    # 2. product specs: "1 kilo", "250 g", "250 wala"
    for i in range(len(toks) - 1):
        n = parse_number(toks[i])
        if n is None or used[i] or n < 0:
            continue
        if toks[i + 1] in KG_WORDS:
            specs_g.append(n * 1000)
            used[i] = used[i + 1] = True
        elif toks[i + 1] in G_WORDS:
            specs_g.append(n)
            used[i] = used[i + 1] = True
        elif toks[i + 1] in SPEC_SUFFIX:
            specs_bare.append(n)
            used[i] = used[i + 1] = True
    # 3. a bare number with no unit: quantity of unknown unit (never assumed to be cases)
    if qty is None:
        cands = [(i, parse_number(t)) for i, t in enumerate(toks) if not used[i] and parse_number(t) is not None]
        if len(cands) > 1:
            known_specs = {75, 250, 1000}
            narrowed = [c for c in cands if c[1] not in known_specs]
            cands = narrowed if narrowed else cands
        if len(cands) == 1:
            qty, used[cands[0][0]] = cands[0][1], True
        elif len(cands) > 1:
            notes.append("more than one number found")
    has_size = any(t in SIZE_SMALL for t in toks)
    product_tokens = [t for i, t in enumerate(toks) if not used[i] and t not in STOPWORDS and parse_number(t) is None]
    return Segment(text.strip(), qty, unit, product_tokens, specs_g, specs_bare, has_size, notes)


_SPLIT_RE = re.compile(r"[,;\n\r|]+|\s+(?:and|aur|plus|और)\s+|\s*\+\s*")


def split_segments(message: str) -> list[str]:
    parts = [p.strip() for p in _SPLIT_RE.split(message) if p and p.strip()]
    out: list[str] = []
    for part in parts:
        out.extend(_split_multi_quantity(part))
    return [p for p in out if re.search(r"\w", p)]


def _split_multi_quantity(part: str) -> list[str]:
    """'5 peti biscuit 2 peti powder' (no commas) -> two segments."""
    words = part.split()
    toks_norm = [normalize_text(w).strip(".") for w in words]
    hits = [i for i in range(len(words) - 1)
            if parse_number(toks_norm[i]) is not None and toks_norm[i + 1] in CASE_WORDS | PIECE_WORDS
            and not (i + 2 < len(words) and toks_norm[i + 2] in KG_WORDS | G_WORDS)]
    if len(hits) < 2:
        return [part]
    if hits[0] == 0:                       # quantity-first style: split at each quantity
        bounds = hits + [len(words)]
        return [" ".join(words[bounds[k]:bounds[k + 1]]) for k in range(len(hits))]
    ends = [h + 2 for h in hits]           # product-first style: split after each quantity
    segs, start = [], 0
    for e in ends:
        segs.append(" ".join(words[start:e]))
        start = e
    if start < len(words):
        segs[-1] += " " + " ".join(words[start:])
    return segs


def clean_display_phrase(segment: str) -> str:
    """Trim greetings/fillers from the ends of a segment for display, keeping the customer's own words."""
    words = segment.split()
    while len(words) > 1 and normalize_text(words[0]).strip(".") in {"bhej", "de", "kar"} and normalize_text(words[1]).strip(".") == "do":
        words = words[2:]
    while words and normalize_text(words[0]).strip(".") in STOPWORDS - {"wala", "wali", "waala", "wale"}:
        words.pop(0)
    while words and normalize_text(words[-1]).strip(".") in {"chahiye", "chahie", "chaiye", "dena", "dedo", "dijiye", "please", "plz"}:
        words.pop()
    return " ".join(words) or segment


def extract_product_phrase(original_phrase: str) -> str:
    """Product words only (no quantity, packing word, or filler): used as the alias text."""
    seg = analyse_segment(original_phrase)
    return " ".join(seg.product_tokens)


def normalize_alias(text: str) -> str:
    return " ".join(t for t in tokenize(text) if t not in STOPWORDS)


# ---------------------------------------------------------------- product matching
@dataclass
class CatalogueEntry:
    sku: str
    name: str
    strong: set[str]
    weak: set[str]
    size_words: set[str]
    spec_g: set[float]


def build_catalogue(products) -> list[CatalogueEntry]:
    entries = []
    for p in products:
        hints = SKU_HINTS.get(p.sku, {})
        name_toks = {t for t in tokenize(p.name) if parse_number(t) is None and t not in KG_WORDS | G_WORDS}
        strong = set(hints.get("strong", set())) | {t for t in name_toks if t not in _GENERIC_NAME_WORDS}
        weak = set(hints.get("weak", set())) | {t for t in name_toks if t in _GENERIC_NAME_WORDS and t not in {"g", "kg", "case", "pack"}}
        specs = {float(v) * (1000 if u == "kg" else 1) for v, u in re.findall(r"(\d+(?:\.\d+)?)\s*(kg|g)\b", p.name.lower())}
        entries.append(CatalogueEntry(p.sku, p.name, strong, weak - strong, set(hints.get("size", set())), specs))
    return entries


def _score(entry: CatalogueEntry, seg: Segment) -> float:
    toks = set(seg.product_tokens)
    strong_hits, weak_hits = len(toks & entry.strong), len(toks & entry.weak)
    base = 0.0
    if strong_hits:
        base = 0.85 + 0.04 * (min(strong_hits, 3) - 1)
    elif weak_hits:
        base = 0.6
    spec_present = bool(seg.specs_g or seg.specs_bare)
    spec_match = any(g in entry.spec_g for g in seg.specs_g) or any(
        b in entry.spec_g or b * 1000 in entry.spec_g for b in seg.specs_bare)
    size_match = seg.has_size_word and bool(entry.size_words)
    if base == 0:
        if spec_match:
            base = 0.55
        elif size_match:
            base = 0.4
    else:
        if spec_match or size_match:
            base += 0.1
        elif spec_present:
            base -= 0.35
    return round(max(0.0, min(base, 0.99)), 2)


def match_segment(seg: Segment, catalogue: list[CatalogueEntry], aliases: list[tuple[str, str]]):
    """aliases: (alias_text, sku) for this retailer only. Returns (sku|None, confidence, alt_skus, source, ambiguous)."""
    phrase_set = set(seg.product_tokens)
    best_alias = None
    for alias_text, sku in aliases:
        a = set(normalize_alias(alias_text).split())
        if a and a <= phrase_set and (best_alias is None or len(a) > best_alias[0]):
            best_alias = (len(a), sku)
    ranked = sorted(((_score(e, seg), i, e.sku) for i, e in enumerate(catalogue)), key=lambda r: (-r[0], r[1]))
    if best_alias:
        sku = best_alias[1]
        alts = [r[2] for r in ranked if r[2] != sku][:2]
        return sku, 0.98, alts, "alias", False
    top = ranked[0]
    if top[0] <= 0:
        return None, 0.0, [r[2] for r in ranked][:3], "keyword", False
    second = ranked[1] if len(ranked) > 1 else None
    ambiguous = bool(second and second[0] >= 0.5 and top[0] - second[0] < 0.15)
    conf = min(top[0], 0.55) if ambiguous else top[0]
    return top[2], conf, [r[2] for r in ranked if r[2] != top[2]][:2], "keyword", ambiguous


def parse_with_rules(message: str, products, aliases: list[tuple[str, str]]) -> list[RawLine]:
    catalogue = build_catalogue(products)
    lines: list[RawLine] = []
    for segment in split_segments(message):
        seg = analyse_segment(segment)
        if not seg.product_tokens and seg.raw_quantity is None and not (seg.specs_g or seg.specs_bare):
            continue
        sku, conf, alts, source, ambiguous = match_segment(seg, catalogue, aliases)
        lines.append(RawLine(original_phrase=clean_display_phrase(segment), raw_quantity=seg.raw_quantity, unit=seg.unit,
                             sku=sku, confidence=conf, alternative_skus=alts, source=source, ambiguous=ambiguous,
                             notes=seg.notes))
    return lines
