# Piano Jazz Concept - Catalogue Vidéo

![Piano Jazz Concept](static/images/header_banner.png)


## 📖 Description

Application web permettant d'explorer et de cataloguer les vidéos YouTube de la chaîne **Piano Jazz Concept** d'Étienne Guéreau. Cette application analyse automatiquement les 193 vidéos de la chaîne et extrait les métadonnées des 177 morceaux de jazz analysés.

Lien vers le site : https://pianojazzconcept.pythonanywhere.com

🔗 **Chaîne YouTube** : [Piano Jazz Concept](https://www.youtube.com/@Pianojazzconcept)
🌐 **Site officiel** : [pianojazzconcept.com](https://www.pianojazzconcept.com)

---

## ✨ Fonctionnalités

### 🎵 Navigation des Morceaux
- **177 morceaux** extraits automatiquement des 193 vidéos YouTube
- Recherche par titre, compositeur, interprète
- Filtrage par catégorie, style, époque, compositeur, interprète
- Tri alphabétique ou thématique
- Navigation alphabétique avec ancres de défilement
- Lecture vidéo intégrée avec miniatures cliquables

### 📊 Métadonnées Enrichies (IA)
Chaque morceau contient des informations détaillées extraites automatiquement par intelligence artificielle :
- **Titre du morceau**
- **Compositeur** (ex: George Gershwin, Duke Ellington)
- **Interprète** (ex: Bill Evans, Brad Mehldau)
- **Album** et **label discographique**
- **Année d'enregistrement** et **année de composition**
- **Style musical** (jazz, standards, bossa nova, etc.)
- **Époque** (années 1950s, 1960s, etc.)
- **Artistes invités** mentionnés dans la vidéo
- **Notes contextuelles** sur l'analyse
- **Horodatages** des morceaux dans les vidéos

### 🎬 Catégorisation des Vidéos
Les vidéos sont automatiquement classées par type :
- **Génériques TV** (Mission Impossible, Amicalement Vôtre, etc.)
- **BO Films** (Michel Legrand, Gabriel Yared, etc.)
- **Chansons/Standards** (jazz standards, variété française)
- **Jeux Vidéo** (Zelda, etc.)
- **Théorie/Analyse** (harmonie, modes, improvisation)
- **Interviews/Culture** (entretiens avec musiciens)
- **Autres** (divers contenus)

### 🛠️ Mode Administrateur
Interface avancée pour la gestion et l'enrichissement du catalogue :
- Édition inline de toutes les métadonnées
- Fonction Annuler (Cmd+Z) pour revenir en arrière
- Ré-extraction LLM pour affiner les métadonnées d'une vidéo
- Récupération automatique des transcriptions YouTube
- Éditeur de "Master Prompt" pour l'extraction IA
- Ajout/suppression de morceaux
- Catégorisation manuelle des vidéos
- Mode performance (miniatures basse résolution)

---

## 🏗️ Architecture Technique

### Technologies Utilisées
- **Backend** : Python 3, Flask
- **Base de données** : SQLite
- **Scraping** : YouTube Data API v3
- **Extraction IA** : OpenAI GPT-4o-mini
- **Frontend** : HTML5, CSS3, JavaScript vanilla
- **Transcriptions** : youtube-transcript-api

### Structure du Projet
```
Piano Jazz Concept/
├── app.py                      # Application Flask principale
├── database/
│   └── piano_jazz_videos.db    # Base SQLite (193 vidéos, 177 morceaux)
├── utils/
│   ├── scrape_youtube.py       # Scraping YouTube Data API
│   ├── llm_full_extract.py     # Extraction IA des métadonnées
│   └── count_songs.py          # Statistiques base de données
├── templates/
│   └── index.html              # Interface utilisateur
├── static/
│   └── images/                 # Bannière, favicon, icônes
├── config/
│   ├── admin_config.py         # Configuration admin
│   └── prompt_template.txt     # Prompt d'extraction IA
├── requirements.txt            # Dépendances Python
└── README.md                   # Ce fichier
```

### Base de Données

**Table `videos`** (193 entrées)
- Métadonnées brutes des vidéos YouTube
- Titre, description, URL, date de publication
- Vignettes (thumbnail_url)
- Type de vidéo (catégorisation)

**Table `songs`** (177 entrées)
- Morceaux individuels extraits des vidéos
- Métadonnées enrichies par IA
- Liens vers les vidéos sources (via `video_id`)
- Une vidéo peut contenir 0, 1 ou plusieurs morceaux

---

## 📊 Statistiques du Projet

### Développement
- **Date de début** : 30 septembre 2025 (12h13)
- **Durée de développement** : ~8 heures (en une journée)
- **Nombre de commits** : 54 commits
- **Lignes de code** : ~2 874 lignes (Python, HTML, CSS)
- **Développeur** : ColinusM (avec assistance IA Claude)

### Données
- **Vidéos indexées** : 193 vidéos YouTube
- **Morceaux extraits** : 177 morceaux de jazz
- **Compositeurs** : Duke Ellington, George Gershwin, Bill Evans, John Coltrane, et bien d'autres
- **Interprètes** : Brad Mehldau, Michel Legrand, Herbie Hancock, et bien d'autres
- **Styles** : Jazz standards, bossa nova, jazz modal, bebop, etc.

### Évolution des Fonctionnalités (Chronologie)

**30 septembre 2025 - Matin (12h13 - 14h30)**
1. ✅ **12h13** : Commit initial - Scraping YouTube et catalogue basique
2. ✅ **12h27** : Ajout scraping descriptions complètes et outils d'analyse
3. ✅ **12h31** : Affichage par morceaux individuels (au lieu de vidéos)
4. ✅ **12h40** : Filtrage par type + descriptions extensibles
5. ✅ **12h44** : Amélioration détection artistes dans les titres
6. ✅ **13h38** : Réorganisation projet + enrichissement LLM
7. ✅ **13h40** : Interface affichage métadonnées enrichies
8. ✅ **13h46** : Enrichissement LLM intelligent avec contexte
9. ✅ **14h22** : Mode admin avec édition inline + fonction Annuler
10. ✅ **14h27** : Filtrage métadonnées enrichies + complétion LLM
11. ✅ **14h27** : Préparation déploiement (requirements.txt, config prod)

**30 septembre 2025 - Après-midi (14h49 - 17h30)**
12. ✅ **14h49** : Simplification lecture depuis table `songs` uniquement
13. ✅ **15h05** : Documentation stratégie enrichissement LLM
14. ✅ **15h17** : Spécification super-prompt extraction complète
15. ✅ **15h24** : Implémentation extraction métadonnées complètes
16. ✅ **15h48** : Ré-extraction par vidéo avec prompt conservateur
17. ✅ **15h52** : Guidance prompt par vidéo + éditeur master prompt
18. ✅ **15h57** : Affichage vignettes YouTube sur cartes vidéo
19. ✅ **16h03** : Éditeur Master Prompt pliable avec bouton réduire
20. ✅ **16h32** : Bouton "Tout Afficher" + feature transcriptions + doc
21. ✅ **16h34** : Documentation fonctionnalités admin + rappel restart
22. ✅ **16h41** : Fix API transcriptions (attributs objet vs clés dict)
23. ✅ **16h46** : Feature catégorisation type de vidéo
24. ✅ **16h48** : Fix bouton "Tout Afficher" pour liste complète
25. ✅ **16h52** : Sync filtres avec catégories + bouton "Tout Afficher"
26. ✅ **16h55** : Fix label compteur "vidéo(s)" en mode vidéos
27. ✅ **17h22** : Fix affichage métadonnées après ré-extraction
28. ✅ **17h30** : Tooltips info-bulles + édition inline tous champs

**30 septembre 2025 - Fin d'après-midi (17h32 - 19h30)**
29. ✅ **17h32** : Boutons ré-extraction/transcription compacts minimalistes
30. ✅ **17h38** : Fond éditeur prompt + barre recherche blanc (vs noir)
31. ✅ **17h44** : Intégration bannière header site Piano Jazz Concept
32. ✅ **17h52** : Conversion UI couleurs schéma gris/blanc minimal
33. ✅ **18h10** : Liens croisés morceaux↔vidéos + doc améliorée
34. ✅ **18h21** : Suppression morceaux + support Annuler
35. ✅ **18h40** : Grammaire française correcte + placeholder compact
36. ✅ **19h00** : Titre morceau comme en-tête principal en mode morceaux
37. ✅ **19h09** : Raffinement styling bouton arc-en-ciel + animation
38. ✅ **19h18** : Fix affichage titre vidéo + icônes YouTube/favicon
39. ✅ **19h29** : Lecture vidéo inline avec miniatures cliquables

**30 septembre 2025 - Soirée (19h37 - 20h40)**
40. ✅ **19h37** : Bouton YouTube minimaliste + texte bouton + favicon
41. ✅ **19h43** : Notification sauvegarde minimaliste catégorisation
42. ✅ **19h51** : Filtrage video_type pour vue YouTube Videos
43. ✅ **19h54** : Conservation titre vidéo original en vue YouTube Videos
44. ✅ **19h57** : Mise à jour base données (vidéos + morceaux)
45. ✅ **20h18** : Mise à jour base données (vidéos + morceaux)
46. ✅ **20h23** : Bouton + sur cartes vidéo pour créer entrées morceaux
47. ✅ **20h29** : Mise à jour base données (derniers changements)
48. ✅ **20h33** : **🎉 Enrichissement base 177 morceaux (193 vidéos) via LLM**
49. ✅ **20h39** : Ajout openai + youtube-transcript-api à requirements.txt

---


```



### Scraping YouTube (Optionnel)
Pour mettre à jour les données YouTube :
```bash
cd utils
python scrape_youtube.py
```
*Nécessite une clé API YouTube Data v3 (à configurer dans `scrape_youtube.py`)*

### Enrichissement LLM (Optionnel)
Pour ré-extraire les métadonnées avec l'IA :
```bash
cd utils
python llm_full_extract.py
```
*Nécessite une clé API OpenAI (à configurer dans `llm_full_extract.py`)*

---

## 🎯 Cas d'Usage

### Pour les Mélomanes
- Découvrir tous les standards de jazz analysés par Étienne Guéreau
- Retrouver l'analyse d'un morceau spécifique (ex: "My Funny Valentine")
- Explorer les analyses par compositeur (ex: tous les morceaux de Duke Ellington)
- Comparer différentes versions d'un même standard

### Pour les Musiciens
- Étudier les analyses harmoniques détaillées
- Trouver des morceaux par style ou époque
- Accéder rapidement aux horodatages des analyses
- Consulter les notes contextuelles sur chaque morceau

### Pour les Chercheurs
- Base de données structurée de 177 analyses musicales
- Métadonnées enrichies (compositeur, interprète, album, label, année)
- Exportation possible vers d'autres formats
- API potentielle pour applications tierces

---

## 🤖 Intelligence Artificielle

### Extraction Automatique des Métadonnées
L'application utilise **OpenAI GPT-4o-mini** pour extraire automatiquement les métadonnées des vidéos :

**Processus d'extraction :**
1. **Analyse du titre et de la description** de chaque vidéo YouTube
2. **Extraction intelligente** des informations :
   - Titre du morceau (détecté dans le titre/description)
   - Compositeur (ex: "Jerome Kern" dans "Yesterdays (J. Kern)")
   - Interprète (ex: "Brad Mehldau" dans "avec Brad Mehldau")
   - Contexte de l'analyse (solo analysé, comparaison de versions, etc.)
3. **Enrichissement avec connaissances musicales** :
   - L'IA utilise sa base de connaissances du jazz pour compléter :
     - Albums célèbres (ex: "Kind of Blue" pour "So What")
     - Labels discographiques (ex: "Blue Note", "Verve")
     - Années d'enregistrement des versions célèbres
     - Styles musicaux et époques
4. **Approche conservative** :
   - Retourne une liste vide si aucun morceau n'est clairement identifié
   - Ne génère pas de fausses informations
   - Distingue l'analysant (Étienne) des artistes catalogués

**Prompt d'extraction personnalisable :**
Le "Master Prompt" peut être édité en mode admin pour affiner l'extraction selon vos besoins.

---

## 📧 Contact & Contributions

**Développeur** : ColinusM
**Chaîne YouTube** : [Piano Jazz Concept](https://www.youtube.com/@Pianojazzconcept)
**Site officiel** : [pianojazzconcept.com](https://www.pianojazzconcept.com)

### Contribuer
Les contributions sont les bienvenues ! N'hésitez pas à :
- Signaler des bugs via les issues GitHub
- Proposer des améliorations
- Corriger les métadonnées des morceaux
- Ajouter de nouvelles fonctionnalités

---

## 📄 Licence

Ce projet est développé dans un cadre éducatif et de recherche musicale.
Toutes les vidéos et contenus musicaux appartiennent à leurs auteurs respectifs.

**© 2025 Piano Jazz Concept - Étienne Guéreau**

---

## 🙏 Remerciements

- **Étienne Guéreau** pour sa chaîne Piano Jazz Concept et ses analyses musicales exceptionnelles
- **OpenAI** pour l'API GPT-4o-mini utilisée pour l'extraction des métadonnées
- **YouTube Data API v3** pour l'accès aux métadonnées des vidéos
- **Anthropic Claude** pour l'assistance au développement de cette application

---

**Note** : Cette application est un projet non officiel destiné à faciliter l'exploration du contenu de la chaîne Piano Jazz Concept. Pour le contenu pédagogique officiel, rendez-vous sur [pianojazzconcept.com](https://www.pianojazzconcept.com).
