# Journal des modifications

Tous les changements notables apportés à Piano Jazz Concept seront documentés dans ce fichier.

## 2026-03-28

### Améliorations
- Les boutons en haut de page (connexion admin, notifications, feedback) sont maintenant à gauche, en forme de cercles uniformes, empilés verticalement dans le bandeau bleu
- Le panneau de notifications s'ouvre correctement sans être coupé par le bord de l'écran
- Dans la vue Real Book (index alphabétique), les carrés vert « Théorie » et bleu « Mention » de la légende sont maintenant cliquables : un clic filtre les morceaux par type d'analyse, un second clic enlève le filtre

---

## 2026-03-25 (3)

### Améliorations techniques
- Refonte complète de l'architecture du site pour améliorer la performance et la maintenabilité
- Le style visuel (CSS) est désormais chargé dans un fichier séparé, ce qui accélère le chargement des pages grâce au cache du navigateur
- Nettoyage de boutons et fonctions inutilisés dans l'interface d'administration

## 2026-03-25 (2)

### Nouveaux morceaux
- **36 nouveaux morceaux ajoutés au catalogue** — Le catalogue passe de 255 à 291 morceaux (138 vidéos couvertes sur 232)
  - Standards jazz : Autumn Leaves, Darn That Dream, Some Other Time, Nobody Else But Me, Laurie (Evans), My Wild Irish Rose, Silent Night, Winter Wonderland
  - Génériques TV : TF1 (Cosma), Amicalement vôtre (Barry), La Quatrième Dimension (Constant), Mission Impossible (Schifrin), Rahan (Cosma), Le Cinéma du dimanche soir (Cosma)
  - Musiques de films : Emmanuel/Wings (Colombier), Jurassic Park (Williams), Parade JO 2024 (Le Masne)
  - Compositions d'Étienne : Jamais sans Aya, Le Bal clandé, Vivre avec vous, Just In!
  - Contemporain : Message (Louis Cole), La Que Puede Puede (Ca7riel), Djadja (Aya Nakamura), Grande Main (VBETO)
  - Divers : Le Pénitencier, On Saturday (Yared), Fida'i, Happy Birthday, Amazing Grace (Hancock/Collier), Berceuse pour un gosse malade, Les Choses qu'on ne peut dire à personne (Burgalat), The Quintessence (Quincy Jones), Vivre quand on aime (Legrand)
- Chaque nouveau morceau est classifié Théorie (vert) ou Mention (bleu) dans l'index

### Améliorations
- Nouveau design de l'interface : onglets plus lisibles, filtres simplifiés, icônes restaurées
- Les liens dans les descriptions de vidéos sont maintenant cliquables
- Renommage de l'onglet « Index » en « Real Book »

## 2026-03-25

### Nouveautés
- **Filtre « Profondeur d'analyse »** — Nouveau menu pour distinguer les vidéos d'analyse musicale (Théorie, en vert) des mentions culturelles (Mention, en bleu)
- La profondeur d'analyse est modifiable directement sur chaque carte morceau en mode admin
- Tous les 255 morceaux existants ont été classifiés : 136 Théorie, 119 Mention

### Nouveaux morceaux
- **Chronique culturelle #3** — 12 morceaux extraits avec leurs timestamps
- **Chronique culturelle pilote** — 8 morceaux extraits
- **Chronique culturelle #2** — 10 morceaux extraits avec timestamps
- **Neosoul/Gospel** — 3 morceaux extraits

### Améliorations
- Interface entièrement traduite en français avec bouton de feedback
- Tri par date (les plus récents d'abord) par défaut, avec bascule A-Z
- L'onglet Vidéos est maintenant accessible à tous (pas seulement les admins)
- 35 nouvelles vidéos ajoutées et 17 morceaux extraits

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
