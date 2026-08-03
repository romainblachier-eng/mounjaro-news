#!/usr/bin/env python3
"""
Migration ponctuelle : passage du site en français uniquement.

Pour chaque article de content/posts/ :
  1. `title`        <- titre français nettoyé (suffixe média retiré, marqueurs parasites supprimés)
  2. `source_name`  <- vrai nom du média, extrait du suffixe du titre (au lieu de "news.google.com")
  3. `lede`         <- chapô (ex-`summary_fr`)
  4. le corps de l'article devient le vrai contenu Markdown (ex-`content_fr`),
     découpé en paragraphes lisibles
  5. `title_fr`, `content_fr`, `content_en`, `summary_fr` sont supprimés

Idempotent : un article déjà migré (sans `content_fr`) est laissé tel quel.
"""

import json
import re
import sys
from pathlib import Path

import yaml

POSTS = Path(__file__).resolve().parent.parent / "content" / "posts"

# Suffixe " - Nom du média" en fin de titre (le nom peut contenir un trait d'union)
MEDIA_TAIL = re.compile(r"\s+[-–—]\s+((?:(?!\s[-–—]\s).){2,60})$")
# Marqueurs parasites laissés par certains flux, ex. "*WRn3AEdaq*"
JUNK_MARKER = re.compile(r"\s*\*[A-Za-z0-9]{5,}\*\s*")
# Agrégateurs : ce ne sont pas de vraies sources
AGGREGATORS = {"google news", "news.google.com", "google actualités", "google actualites"}
# Étiquettes génériques ajoutées par les flux, à retirer sans les créditer
GENERIC_LABELS = AGGREGATORS | {"actualité", "actualités", "actualite", "actualites",
                                "news", "info", "infos", "à la une", "a la une"}
MAX_MEDIA_WORDS = 7
MIN_KEPT_TITLE  = 25   # longueur mini du titre une fois le média retiré


def _split_tail(title):
    """Isole le dernier segment " - xxx" du titre. Retourne (début, segment) ou None."""
    m = MEDIA_TAIL.search(title)
    if not m:
        return None
    return title[: m.start()].strip(), m.group(1).strip()


def _looks_like_media(rest: str, tail: str) -> bool:
    """Un nom de média : court, capitalisé, sans ponctuation finale, et plus court que le titre."""
    if not tail or tail.endswith((".", "!", "?", ":")):
        return False
    if not (tail[0].isupper() or tail[0].isdigit()):
        return False  # minuscule = suite de la phrase, pas un média
    if len(tail.split()) > MAX_MEDIA_WORDS:
        return False
    # Un titre amputé plus court que son prétendu média : c'est une phrase qu'on couperait
    return len(rest) >= max(MIN_KEPT_TITLE, len(tail))


def clean_title(raw: str) -> tuple[str, str]:
    """Retourne (titre nettoyé, nom du média détecté ou "")."""
    title = JUNK_MARKER.sub(" ", raw).strip()
    title = re.sub(r"\s{2,}", " ", title)
    # Préfixe générique, ex. "Actualité - Analogues du GLP-1…"
    title = re.sub(r"^(actualit[ée]s?|news|infos?)\s*[-–—]\s*", "", title, flags=re.I)

    media = ""
    # 1. On retire d'abord les étiquettes génériques, éventuellement empilées
    while True:
        split = _split_tail(title)
        if not split or split[1].lower() not in GENERIC_LABELS:
            break
        title = split[0]

    # 2. Puis, une seule fois, le vrai nom du média
    split = _split_tail(title)
    if split and _looks_like_media(*split):
        title, media = split

    return title.strip(" -–—:"), media


def paragraphize(text: str) -> str:
    """Découpe un pavé de texte en paragraphes de ~3 phrases."""
    text = " ".join(text.split())
    if not text:
        return ""

    sentences = re.findall(r"[^.!?]+[.!?]+(?:\s|$)|[^.!?]+$", text)
    sentences = [s.strip() for s in sentences if s.strip()]
    if len(sentences) <= 3:
        return text

    # 2 paragraphes si le texte est court, 3 sinon
    nb = 2 if len(sentences) <= 6 else 3
    size = -(-len(sentences) // nb)  # arrondi supérieur
    chunks = [" ".join(sentences[i : i + size]) for i in range(0, len(sentences), size)]
    return "\n\n".join(c for c in chunks if c)


def yaml_str(value: str) -> str:
    """Sérialise une chaîne en scalaire YAML entre guillemets (syntaxe JSON, valide en YAML)."""
    return json.dumps(value, ensure_ascii=False)


def migrate(path: Path) -> bool:
    raw = path.read_text(encoding="utf-8")
    if not raw.startswith("---"):
        return False

    _, fm_raw, body = raw.split("---", 2)
    fm = yaml.safe_load(fm_raw) or {}

    if "content_fr" not in fm and "title_fr" not in fm:
        return False  # déjà migré

    title, media = clean_title(str(fm.get("title_fr") or fm.get("title") or "").strip())
    content = str(fm.get("content_fr") or "").strip()
    lede = str(fm.get("lede") or fm.get("summary_fr") or "").strip()
    lede = JUNK_MARKER.sub(" ", lede).strip()

    if not content:
        # Rien d'exploitable en français : on retombe sur l'ancien corps
        content = body.strip()

    source_name = media or str(fm.get("source_name") or "").strip()
    if source_name.lower() in AGGREGATORS:
        source_name = ""

    description = (str(fm.get("description") or lede or title)).strip()
    description = JUNK_MARKER.sub(" ", description).strip()[:160]

    lines = [
        "---",
        f"title: {yaml_str(title)}",
        f"date: {fm['date'].isoformat() if hasattr(fm.get('date'), 'isoformat') else fm.get('date')}",
        "draft: false",
        f"description: {yaml_str(description)}",
        f"lede: {yaml_str(lede)}",
    ]
    if source_name:
        lines.append(f"source_name: {yaml_str(source_name)}")
    if fm.get("source_url"):
        lines.append(f"source_url: {yaml_str(str(fm['source_url']))}")
    lines += ["---", "", paragraphize(content), ""]

    path.write_text("\n".join(lines), encoding="utf-8")
    return True


def retitle(path: Path) -> bool:
    """Repasse le nettoyage sur le `title` d'un article déjà migré."""
    raw = path.read_text(encoding="utf-8")
    m = re.search(r'^title:\s*(".*")\s*$', raw, re.M)
    if not m:
        return False

    old = json.loads(m.group(1))
    new, media = clean_title(old)
    if not new or new == old:
        return False

    raw = raw[: m.start(1)] + yaml_str(new) + raw[m.end(1):]
    # Si aucun média n'était crédité et qu'on vient d'en identifier un, on l'ajoute
    if media and not re.search(r"^source_name:", raw, re.M):
        raw = re.sub(r"^(source_url:)", f"source_name: {yaml_str(media)}\n\\1", raw, count=1, flags=re.M)

    path.write_text(raw, encoding="utf-8")
    print(f"  · {old}\n    → {new}")
    return True


def main() -> None:
    files = sorted(POSTS.glob("*.md"))
    done = sum(1 for f in files if migrate(f))
    print(f"{done}/{len(files)} article(s) migré(s) en français.")
    fixed = sum(1 for f in files if retitle(f))
    print(f"{fixed} titre(s) renettoyé(s).")


if __name__ == "__main__":
    sys.exit(main())
