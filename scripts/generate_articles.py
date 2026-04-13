#!/usr/bin/env python3
"""
Mounjaro News — Générateur d'articles quotidiens bilingues
==========================================================
1. Scrape les dernières actualités Mounjaro via Google News RSS + PubMed RSS
2. Filtre les articles déjà traités (fichier .processed_urls)
3. Pour chaque nouvelle source :
   - Récupère le contenu de l'article
   - Génère via Claude AI :
       * Un résumé reformulé en FRANÇAIS (200-250 mots)
       * Une traduction/reformulation en ANGLAIS (200-250 mots)
4. Crée un fichier Hugo Markdown avec les deux versions en frontmatter

Variables d'environnement :
  ANTHROPIC_API_KEY   Clé API Anthropic (obligatoire)
"""

import os
import sys
import json
import time
import hashlib
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import requests
import feedparser


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

def fetch_rss_articles() -> list[dict]:
    """Récupère les articles depuis tous les flux RSS."""
    articles = []
    seen_titles = set()

    for feed_url in RSS_FEEDS:
        try:
            print(f"  📡 {feed_url[:70]}…")
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:10]:
                title = entry.get("title", "").strip()
                url   = entry.get("link", "").strip()
                # Nettoie les titres Google News (format "Titre - Source")
                title = re.sub(r'\s+[-–]\s+\S+\s*$', '', title).strip()

                if not title or not url or len(title) < MIN_TITLE_LENGTH:
                    continue
                if title.lower() in seen_titles:
                    continue

                seen_titles.add(title.lower())
                articles.append({
                    "title":       title,
                    "url":         url,
                    "source_name": urlparse(url).netloc.replace("www.", ""),
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
        text = re.sub(r'<script[^>]*>.*?</script>', '', resp.text, flags=re.DOTALL)
        text = re.sub(r'<style[^>]*>.*?</style>',  '', text,      flags=re.DOTALL)
        text = re.sub(r'<[^>]+>',                  ' ', text)
        text = re.sub(r'\s+',                       ' ', text).strip()
        return text[:4000]  # Claude reçoit les 4000 premiers caractères
    except Exception:
        return ""


# ──────────────────────────────────────────────
# 4. Génération bilingue avec Claude
# ──────────────────────────────────────────────

def generate_bilingual_content(article: dict, content: str, api_key: str) -> tuple[str, str, str]:
    """
    Retourne (resume_fr, resume_en, titre_fr).
    """
    import anthropic

    client  = anthropic.Anthropic(api_key=api_key)
    context = content if content else article.get("summary", article["title"])

    prompt = f"""Tu es un journaliste de santé spécialisé dans les médicaments GLP-1.
On te donne un article sur le Mounjaro (tirzépatide).
Produis UNIQUEMENT un JSON avec trois champs :
- "title_fr" : traduction/adaptation en français du titre, naturelle et journalistique (garder le nom du média à la fin si présent, ex. "- The Guardian")
- "fr" : reformulation en français (200-250 mots), claire, factuelle, accessible au grand public
- "en" : reformulation en anglais (200-250 mots), clear, factual, accessible

Règles :
- Ne jamais reproduire le texte original mot pour mot (sauf noms propres)
- Pas de conseil médical, pas de recommandation de traitement
- Si l'info est scientifique, la vulgariser
- Commencer "fr" par une phrase d'accroche forte
- Commencer "en" par a strong hook sentence
- Si le titre est déjà en français, recopie-le tel quel dans "title_fr"

Titre de l'article : {article['title']}
Source : {article['source_name']}
Contenu disponible : {context[:3000]}

Réponds UNIQUEMENT avec le JSON, sans markdown ni commentaire."""

    try:
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=900,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = message.content[0].text.strip()
        # Nettoyage au cas où Claude ajoute des backticks
        raw = re.sub(r'^```[a-z]*\n?', '', raw)
        raw = re.sub(r'\n?```$',       '', raw)
        data = json.loads(raw)
        return data.get("fr", ""), data.get("en", ""), data.get("title_fr", article['title'])
    except json.JSONDecodeError:
        # Fallback si JSON malformé
        return raw[:500], "", article['title']
    except Exception as e:
        print(f"    ⚠️  Erreur Claude : {e}")
        return "", "", article['title']


# ──────────────────────────────────────────────
# 5. Création du fichier Hugo Markdown
# ──────────────────────────────────────────────

def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r'[àáâãäå]', 'a', text)
    text = re.sub(r'[èéêë]',   'e', text)
    text = re.sub(r'[ìíîï]',   'i', text)
    text = re.sub(r'[òóôõö]',  'o', text)
    text = re.sub(r'[ùúûü]',   'u', text)
    text = re.sub(r'[ç]',      'c', text)
    text = re.sub(r'[^a-z0-9]+', '-', text)
    return text.strip('-')[:60]


def escape_yaml(s: str) -> str:
    """Échappe une chaîne pour un champ YAML inline."""
    s = s.replace('\\', '\\\\').replace('"', '\\"')
    return s


def create_hugo_article(article: dict, fr_content: str, en_content: str, title_fr: str = "") -> bool:
    """Génère le fichier Markdown Hugo. Retourne True si créé."""
    now      = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    slug     = f"{date_str}-{slugify(article['title'])}"
    filepath = CONTENT_DIR / f"{slug}.md"

    if filepath.exists():
        return False

    # Résumé court pour la carte d'accueil (première phrase du fr)
    summary_fr = (fr_content.split('.')[0] + '.') if fr_content else article['title']

    # Conversion du contenu en YAML multiline (| block scalar)
    def to_yaml_block(text: str) -> str:
        if not text:
            return '""'
        lines = text.replace('\r', '').split('\n')
        indented = '\n'.join('  ' + l for l in lines)
        return '|\n' + indented

    frontmatter = f"""---
title: "{escape_yaml(article['title'])}"
title_fr: "{escape_yaml(title_fr or article['title'])}"
date: {now.strftime("%Y-%m-%dT%H:%M:%S")}+01:00
draft: false
description: "{escape_yaml(summary_fr[:160])}"
source_name: "{escape_yaml(article['source_name'])}"
source_url: "{article['url']}"
summary_fr: "{escape_yaml(summary_fr)}"
content_fr: {to_yaml_block(fr_content)}
content_en: {to_yaml_block(en_content)}
---
"""

    # Corps Markdown minimal (le vrai contenu est dans le frontmatter)
    body = f"""<!-- Article généré automatiquement par Mounjaro News -->
<!-- Source : [{article['source_name']}]({article['url']}) -->
"""

    CONTENT_DIR.mkdir(parents=True, exist_ok=True)
    filepath.write_text(frontmatter + body, encoding="utf-8")
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

    # 1. Collecte des articles
    print("\n📡 Collecte des flux RSS…")
    candidates = fetch_rss_articles()
    print(f"   {len(candidates)} articles trouvés")

    # 2. Filtrage des déjà traités
    new_articles = [a for a in candidates if a["url"] not in processed]
    print(f"   {len(new_articles)} nouveaux articles à traiter")

    if not new_articles:
        print("\nℹ️  Aucun nouvel article. Fin du script.")
        return

    # 3. Traitement
    created = 0
    for article in new_articles[:MAX_ARTICLES_PER_RUN]:
        print(f"\n🔍 Traitement : {article['title'][:70]}")

        # Récupération du contenu
        print("   ⬇️  Récupération du contenu…")
        content = fetch_article_content(article["url"])
        if content:
            print(f"   ✓ {len(content)} caractères récupérés")

        # Génération bilingue
        print("   🤖 Génération bilingue (Claude)…")
        fr, en, title_fr = generate_bilingual_content(article, content, api_key)

        if not fr:
            print("   ⚠️  Contenu vide — article ignoré.")
            processed.add(article["url"])
            continue

        # Création du fichier Hugo
        if create_hugo_article(article, fr, en, title_fr):
            created += 1
            processed.add(article["url"])
        else:
            print(f"   ℹ️  Déjà existant — ignoré.")

        time.sleep(2)  # Pause entre les appels API

    save_processed(processed)
    print(f"\n✓ {created} article(s) créé(s). Terminé.")


if __name__ == "__main__":
    main()
