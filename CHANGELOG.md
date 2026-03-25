# Journal des modifications

Tous les changements notables apportés à Piano Jazz Concept seront documentés dans ce fichier.

## 2026-03-25

### Nouvelles fonctionnalités
- **Filtre "Profondeur d'analyse"** — Nouveau menu déroulant pour distinguer les vidéos d'analyse musicale (Théorie) des mentions culturelles (Mention) (`064fafa`)
- **Champ éditable en admin** — Le champ `analysis_depth` est modifiable directement sur chaque carte morceau
- **Classification automatique** — Les 255 morceaux ont été classifiés : 136 Théorie, 119 Mention

### Données
- **Chronique culturelle #3** — 12 morceaux extraits avec timestamps précis via Whisper (`c2d9364`, `5cad825`)
- **Chronique culturelle pilote** — 8 morceaux extraits (`770bd58`)
- **Chronique culturelle #2** — 10 morceaux extraits avec timestamps (`a138009`, `7a4fa94`)
- **Neosoul/Gospel** — 3 morceaux extraits (`581fa72`)

### Améliorations
- **Interface traduite en français** avec bouton de feedback par email (`5beee62`)
- **Tri par date (récents)** comme vue par défaut, avec bascule A-Z (`9ef9052`)
- **Onglet Vidéos** accessible à tous les utilisateurs (`1087165`)
- **35 nouvelles vidéos** scrappées et 17 morceaux extraits (`371dd2d`)

## 2025-10-19

### Nouvelles fonctionnalités
- **Bouton cerveau (🧠)** - Extrait les morceaux d'une vidéo individuelle en mode admin
- **Bouton auto-actualisation** - Rafraîchit le catalogue avec les dernières vidéos YouTube
- **Ré-extraction intelligente** - Corrige automatiquement les vidéos sans morceaux extraits

### Corrections majeures
- **Les modifications persistent correctement** - Les changements sur les cartes (compositeur, interprète, style, etc.) sont bien enregistrés
- **Les suppressions fonctionnent** - Les cartes supprimées restent supprimées après actualisation
- **Actualisation du catalogue corrigée** - L'auto-actualisation fonctionne correctement sur le site déployé

### Améliorations
- **Meilleure détection des morceaux** - Les génériques TV et musiques de films sont maintenant bien reconnus
- **Titres plus clairs** - Les vidéos au format "Titre du morceau (Compositeur)" sont correctement identifiées
- Cliquer sur la miniature ouvre directement la vidéo YouTube
