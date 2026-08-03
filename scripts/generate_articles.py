#!/usr/bin/env python3
"""
Mounjaro News — Générateur d'articles quotidiens (français uniquement)
=====================================================================
1. Scrape les dernières actualités Mounjaro via Google News RSS + PubMed RSS
2. Filtre les articles déjà traités (fichier .processed_urls)
3. Pour chaque nouvelle source :
   - Récupère le contenu de l'article
   - Génère via Claude : un titre français + une synthèse française en 3 paragraphes
4. Crée un fichier Hugo Markdown : métadonnées en frontmatter, texte dans le corps

Variables d'environnement :
  ANTHROPIC_API_KEY   Clé API Anthropic (obligatoire)
"""

import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import feedparser
import requests

# ──────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────

RSS_FEEDS = [
    # Google News — Mounjaro EN
    "https://news.google.com/rss/search?q=mounjaro+tirzepatide&hl=en-US&gl=US&ceid=US:en",
    # Google News — Mounjaro FR
    "https://news.google.com/rss/search?q=mounjaro+tirzepatide&hl=fr&gl=FR&ceid=FR:fr",
    # PubMed — tirzepatide
    "https://pubmed.ncbi.nlm.nih.gov/rss/search/?term=tirzepatide&limit=5&format=abstract",
]

MAX_ARTICLES_PER_RUN = 3          # Nb max d'articles générés par exécution
PROCESSED_FILE       = ".processed_urls"
CONTENT_DIR          = Path("content/posts")
MIN_TITLE_LENGTH     = 20         # Ignore les titres trop courts

MODEL = "claude-haiku-4-5-20251001"

# Suffixe " - Nom du média" ajouté par Google News (le nom peut contenir un trait d'union)
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


# ──────────────────────────────────────────────
# 1. Gestion des URLs déjà traitées
# ──────────────────────────────────────────────

def load_processed() -> set:
    if Path(PROCESSED_FILE).exists():
        return set(Path(PROCESSED_FILE).read_text().splitlines())
    return set()


def save_processed(urls: set) -> None:
    Path(PROCESSED_FILE).write_text("\n".join(sorted(urls)))


# ──────────────────────────────────────────────
# 2. Scraping des flux RSS
# ──────────────────────────────────────────────

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


def split_title_and_media(raw: str) -> tuple[str, str]:
    """Sépare "Titre - Le Monde" en ("Titre", "Le Monde")."""
    title = JUNK_MARKER.sub(" ", raw).strip()
    title = re.sub(r"\s{2,}", " ", title)
    title = re.sub(r"^(actualit[ée]s?|news|infos?)\s*[-–—]\s*", "", title, flags=re.I)

    media = ""
    # 1. Étiquettes génériques, éventuellement empilées
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


def fetch_rss_articles() -> list[dict]:
    """Récupère les articles depuis tous les flux RSS."""
    articles = []
    seen_titles = set()

    for feed_url in RSS_FEEDS:
        try:
            print(f"  📡 {feed_url[:70]}…")
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:10]:
                raw_title = entry.get("title", "").strip()
                url = entry.get("link", "").strip()
                title, media = split_title_and_media(raw_title)

                if not title or not url or len(title) < MIN_TITLE_LENGTH:
                    continue
                if title.lower() in seen_titles:
                    continue

                seen_titles.add(title.lower())
                # Le nom du média extrait du titre est bien plus utile que le domaine
                # de l'URL, qui vaut "news.google.com" pour tout Google News.
                domain = urlparse(url).netloc.replace("www.", "")
                source = media or ("" if domain in AGGREGATORS else domain)

                articles.append({
                    "title":       title,
                    "url":         url,
                    "source_name": source,
                    "summary":     entry.get("summary", ""),
                    "published":   entry.get("published", ""),
                })
        except Exception as e:
            print(f"  ⚠️  Erreur RSS ({feed_url[:50]}…) : {e}")

    return articles


# ──────────────────────────────────────────────
# 3. Récupération du contenu de l'article
# ──────────────────────────────────────────────

def fetch_article_content(url: str) -> str:
    """Tente de récupérer le texte de l'article source (best-effort)."""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; MounjaroNewsBot/1.0)"}
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code != 200:
            return ""
        # Extraction brutale du texte (pas de BeautifulSoup pour réduire les dépendances)
        text = re.sub(r"<script[^>]*>.*?</script>", "", resp.text, flags=re.DOTALL)
        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:4000]  # Claude reçoit les 4000 premiers caractères
    except Exception:
        return ""


# ──────────────────────────────────────────────
# 4. Génération française avec Claude
# ──────────────────────────────────────────────

def generate_french_content(article: dict, content: str, api_key: str) -> tuple[str, str]:
    """Retourne (titre_fr, corps_fr) — le corps est en Markdown, 3 paragraphes."""
    import anthropic

    client = anthropic.Anthropic(api_key=api_key)
    context = content if content else article.get("summary", article["title"])

    prompt = f"""Tu es journaliste santé, spécialiste des médicaments GLP-1, et tu écris en français
pour un site d'actualité grand public.

On te donne un article sur le Mounjaro (tirzépatide). Produis UNIQUEMENT un JSON avec deux champs :
- "titre" : le titre en français, naturel et journalistique, SANS le nom du média
- "texte" : une synthèse en français de 200 à 250 mots, répartie en EXACTEMENT 3 paragraphes
  séparés par une ligne vide

Règles :
- Écris en français uniquement, jamais en anglais
- Ne reproduis jamais le texte original mot pour mot (sauf noms propres)
- Pas de conseil médical, pas de recommandation de traitement
- Vulgarise l'information scientifique sans la déformer
- Commence le premier paragraphe par une phrase d'accroche qui résume l'essentiel :
  elle sert de chapô et sera affichée seule sur la page d'accueil
- Respecte la typographie française (espace avant ? ! : ;)

Titre de l'article : {article['title']}
Source : {article['source_name'] or "non précisée"}
Contenu disponible : {context[:3000]}

Réponds UNIQUEMENT avec le JSON, sans markdown ni commentaire."""

    try:
        message = client.messages.create(
            model=MODEL,
            max_tokens=1200,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = message.content[0].text.strip()
        # Nettoyage au cas où Claude ajoute des backticks
        raw = re.sub(r"^```[a-z]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)
        data = json.loads(raw)
        return data.get("titre", article["title"]).strip(), data.get("texte", "").strip()
    except json.JSONDecodeError:
        print("    ⚠️  Réponse JSON invalide — article ignoré.")
        return article["title"], ""
    except Exception as e:
        print(f"    ⚠️  Erreur Claude : {e}")
        return article["title"], ""


# ──────────────────────────────────────────────
# 5. Création du fichier Hugo Markdown
# ──────────────────────────────────────────────

def slugify(text: str) -> str:
    text = text.lower()
    for accents, plain in (("àáâãäå", "a"), ("èéêë", "e"), ("ìíîï", "i"),
                           ("òóôõö", "o"), ("ùúûü", "u"), ("ç", "c")):
        text = re.sub(f"[{accents}]", plain, text)
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")[:60]


def yaml_str(value: str) -> str:
    """Scalaire YAML entre guillemets (la syntaxe JSON est valide en YAML)."""
    return json.dumps(value, ensure_ascii=False)


def first_sentence(text: str) -> str:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return parts[0].strip() if parts else text.strip()


def create_hugo_article(article: dict, title_fr: str, body: str) -> bool:
    """Génère le fichier Markdown Hugo. Retourne True si créé."""
    now = datetime.now()
    slug = f"{now.strftime('%Y-%m-%d')}-{slugify(title_fr)}"
    filepath = CONTENT_DIR / f"{slug}.md"

    if filepath.exists():
        return False

    lede = first_sentence(body)

    lines = [
        "---",
        f"title: {yaml_str(title_fr)}",
        f"date: {now.strftime('%Y-%m-%dT%H:%M:%S')}+01:00",
        "draft: false",
        f"description: {yaml_str(lede[:160])}",
        f"lede: {yaml_str(lede)}",
    ]
    if article["source_name"]:
        lines.append(f"source_name: {yaml_str(article['source_name'])}")
    lines.append(f"source_url: {yaml_str(article['url'])}")
    lines += ["---", "", body.strip(), ""]

    CONTENT_DIR.mkdir(parents=True, exist_ok=True)
    filepath.write_text("\n".join(lines), encoding="utf-8")
    print(f"  ✅ Article créé : {filepath.name}")
    return True


# ──────────────────────────────────────────────
# 6. Point d'entrée
# ──────────────────────────────────────────────

def main() -> None:
    print("═══════════════════════════════════════════")
    print("  Mounjaro News — Génération quotidienne   ")
    print("═══════════════════════════════════════════")

    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        print("❌ Variable ANTHROPIC_API_KEY manquante.")
        sys.exit(1)

    processed = load_processed()

    print("\n📡 Collecte des flux RSS…")
    candidates = fetch_rss_articles()
    print(f"   {len(candidates)} articles trouvés")

    new_articles = [a for a in candidates if a["url"] not in processed]
    print(f"   {len(new_articles)} nouveaux articles à traiter")

    if not new_articles:
        print("\nℹ️  Aucun nouvel article. Fin du script.")
        return

    created = 0
    for article in new_articles[:MAX_ARTICLES_PER_RUN]:
        print(f"\n🔍 Traitement : {article['title'][:70]}")

        print("   ⬇️  Récupération du contenu…")
        content = fetch_article_content(article["url"])
        if content:
            print(f"   ✓ {len(content)} caractères récupérés")

        print("   🤖 Rédaction en français (Claude)…")
        title_fr, body = generate_french_content(article, content, api_key)

        if not body:
            print("   ⚠️  Contenu vide — article ignoré.")
            processed.add(article["url"])
            continue

        if create_hugo_article(article, title_fr, body):
            created += 1
            processed.add(article["url"])
        else:
            print("   ℹ️  Déjà existant — ignoré.")

        time.sleep(2)  # Pause entre les appels API

    save_processed(processed)
    print(f"\n✓ {created} article(s) créé(s). Terminé.")


if __name__ == "__main__":
    main()
