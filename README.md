# Mounjaro News

Veille quotidienne sur le Mounjaro (tirzépatide), **en français uniquement** —
[mounjaronews.info](https://mounjaronews.info/)

Site statique [Hugo](https://gohugo.io/) avec un thème sur mesure (aucun thème externe,
aucun sous-module). Les articles sont générés chaque matin à partir de flux RSS
(Google News, PubMed) puis rédigés en français par Claude.

## Structure

```
assets/css/main.css        Feuille de style unique (tokens, clair/sombre)
layouts/                   Thème sur mesure
  _default/baseof.html     Squelette HTML
  _default/list.html       Archives paginées + recherche client
  _default/single.html     Pages simples (mentions légales)
  index.html               Accueil : une + derniers articles
  index.json               Index de recherche (tous les articles)
  posts/single.html        Page article
  partials/typo.html       Espaces insécables françaises (? ! : ; « »)
content/posts/             Un fichier Markdown par article
scripts/generate_articles.py   Génération quotidienne (Claude + RSS)
scripts/migrate_to_fr.py       Migration bilingue → français (ponctuel, idempotent)
```

## Format d'un article

```yaml
---
title: "Titre en français, sans le nom du média"
date: 2026-08-03T10:39:01+01:00
draft: false
description: "Phrase d'accroche (< 160 caractères, méta description)"
lede: "Phrase d'accroche affichée sur les cartes d'accueil"
source_name: "Le Figaro Santé"   # facultatif, absent si le média est inconnu
source_url: "https://…"
---

Le texte de l'article, en 3 paragraphes.
```

Le corps de l'article est du Markdown normal : `.Content`, `.Summary`, le temps de
lecture et le flux RSS fonctionnent nativement.

## Développement

```bash
hugo server
```

## Génération manuelle d'articles

```bash
ANTHROPIC_API_KEY=sk-… python3 scripts/generate_articles.py
```

Le workflow `.github/workflows/daily-update.yml` fait tourner ce script chaque jour à 8 h
(Paris), commite les nouveaux articles et déploie le site.
