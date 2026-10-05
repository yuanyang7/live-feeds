"""Helpers shared by the FDA adapters: page parsing and dog/cat classification."""

import hashlib
import re
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup

from vibefeed import clean

FDA = "https://www.fda.gov"

DOG = re.compile(r"\b(?:dogs?|canines?|pupp(?:y|ies)|k-?9s?)\b", re.I)
CAT = re.compile(r"\b(?:cats?|felines?|kittens?)\b", re.I)
PET = re.compile(r"\bpets?\b", re.I)
# Products for other animals: a page that only names these isn't a dog/cat recall.
# (No "pig": pig ears are dog treats.)
OTHER = re.compile(
    r"\b(?:horses?|equine|cattle|bovine|swine|poultry|chickens? feed|layer feed|"
    r"livestock|goats?|sheep|rabbits?|birds?|parrots?|hedgehogs?|reptiles?|fish|deer|"
    r"alfalfa|meat bird)\b",
    re.I,
)
# Animal drugs and devices are recalled through the same lists; this app is about food.
DRUG = re.compile(r"\b(?:inject\w*|sterile|syringes?|vials?|ophthalmic|compounded)\b", re.I)

HAZARDS = (
    ("virus", r"bird flu|avian influenza|h5n1"),
    ("bacteria", r"salmonella|listeria|e\.? ?coli|campylobacter|clostridium|bacteri|microbial"),
    ("foreign", r"metal|plastic|foreign|glass|rubber|wire|bone fragment"),
    ("toxin", r"aflatoxin|mycotoxin|mold|vomitoxin|pentobarbital|thyroid hormone|melamine"),
    ("nutrient", r"vitamin|thiamine|potassium|copper|choline|folic|nutrient|mineral|calcium|zinc|levels? of"),
)


def rid(url: str) -> str:
    """Stable id from the page path (FDA keeps a recall at the same URL)."""
    return hashlib.sha1(urlsplit(url).path.rstrip("/").encode()).hexdigest()[:10]


def hazard(text: str) -> str:
    for code, pattern in HAZARDS:
        if re.search(pattern, text or "", re.I):
            return code
    return "other"


def species(head: str, body: str = "") -> list[str]:
    """['dog'], ['cat'], ['dog', 'cat'] or ['pet'] (pet food, animal unnamed); [] if neither.

    The headline text decides when it names an animal; the body is only a fallback,
    because boilerplate like "pets with Salmonella..." shows up on every page.
    """
    for text in (head, body):
        found = [name for name, rx in (("dog", DOG), ("cat", CAT)) if rx.search(text or "")]
        if found:
            return found
    return ["pet"] if PET.search(head or "") or PET.search(body or "") else []


def exclusion(head: str, body: str, types: str = "") -> str | None:
    """Why a record isn't a dog/cat food item ('drug', 'other-animal', 'not-pet'), or None."""
    if DRUG.search(head) or re.search(r"\b(?:Animal Drugs|Drugs|Medical Devices)\b", types):
        return "drug"
    if not (DOG.search(head) or CAT.search(head)) and OTHER.search(head):
        return "other-animal"
    if not species(head, body):
        return "not-pet"
    return None


MAX_LOT_ROWS = 150
PHONE = re.compile(r"(?:\b1[-.\s])?\(?\b\d{3}\)?[-.\s]?\d{3}[-.\s]\d{4}\b")
ILL = re.compile(r"\b(?:ill|illness(?:es)?|sick\w*|deaths?|died|injur\w*)\b", re.I)
REPORTED = re.compile(r"\b(?:report\w*|complaints?|confirmed|cases?)\b", re.I)


def _table(art) -> dict | None:
    """The biggest table on the page (the lot list) as {"h": header, "r": rows, "more": n}."""
    best = None
    for table in art.find_all("table"):
        rows = []
        for tr in table.find_all("tr"):
            cells = [clean(c.get_text(" "))[:120] for c in tr.find_all(["th", "td"])][:6]
            if any(cells):
                rows.append(cells)
        if len(rows) > 1 and (best is None or len(rows) > len(best)):
            best = rows
    if not best:
        return None
    body = best[1:]
    out = {"h": best[0], "r": body[:MAX_LOT_ROWS]}
    if len(body) > MAX_LOT_ROWS:
        out["more"] = len(body) - MAX_LOT_ROWS
    return out


def _para(el) -> str:
    """Block text with inline tags joined back up ("Salmonella , and" -> "Salmonella, and")."""
    t = clean(el.get_text(" "))
    return re.sub(r"\(\s+", "(", re.sub(r"\s+([,.;:!?)])", r"\1", t))


def parse_page(html: str, url: str) -> dict:
    """Headline, summary, announcement text, lot table, illness line, phone and photos."""
    s = BeautifulSoup(html, "html.parser")

    def meta(**attrs):
        tag = s.find("meta", attrs=attrs)
        return clean(tag.get("content")) if tag else ""

    title = re.sub(r"\s*\|\s*FDA\s*$", "", meta(property="og:title") or (clean(s.h1.get_text(" ")) if s.h1 else ""))
    main = s.find("main") or s
    art = main.find("article") or main
    for el in art.find_all(["nav", "aside", "script", "style"]):
        el.decompose()
    text = art.get_text("\n", strip=True)
    paras = [t for t in (_para(el) for el in art.find_all(["p", "li"]) if not el.find_parent("table")) if t]

    out = {"title": title, "sum": meta(name="description"), "body": " ".join(paras)}
    lots = _table(art)
    if lots:
        out["lots"] = lots
    for sentence in (x for para in paras for x in re.split(r"(?<=[.!?])\s+(?=[A-Z])", para)):
        if ILL.search(sentence) and REPORTED.search(sentence):
            out["ill"] = sentence[:300]
            break
    contact = text.split("Company Contact Information", 1)
    if len(contact) == 2:
        m = PHONE.search(contact[1])
        if m:
            out["tel"] = m.group(0)
    imgs = [urljoin(FDA, i["src"]) for i in art.find_all("img", src=True) if "recall_image" in i["src"]]
    if imgs:
        out["img"] = list(dict.fromkeys(imgs))[:4]
    return out
