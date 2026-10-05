# Graphe de compétences PDA — Cycles 1 et 2

Couche 1 de l'architecture Numerix. C'est la fondation : le moteur mathématique, le knowledge tracing et le planificateur de révision espacée s'y branchent tous.

## Contenu

| Fichier | Rôle |
|---|---|
| `pda-arithmetique.json` | 51 compétences — cœur du MVP |
| `pda-autres-champs.json` | 24 compétences — géométrie, mesure, statistique, probabilité |
| `valider_graphe.py` | Validation structurelle + statistiques |
| `ajouter_univers.py` | Script d'enrichissement des univers narratifs (historique) |

**Source :** Progression des apprentissages — Mathématique, Primaire (MELS, 6 octobre 2009), document prescriptif du ministère de l'Éducation du Québec.

Couvre la 1re à la 4e année (cycles 1 et 2). Le cycle 3 (5e–6e) reste à faire.

---

## Structure d'une compétence

```json
{
  "id": "ARI-OPE-A06a",
  "ref_pda": "Opérations — A.6.a",
  "section": "operations",
  "libelle": "Construire les faits numériques de la multiplication...",
  "annee_intro": 3,
  "annee_maitrise": 3,
  "cycle": 2,
  "prerequis": ["ARI-SOP-A03a", "ARI-SEN-A01c"],
  "generable": true,
  "generateur": "gen_faits_multiplication",
  "parametres": { "facteurs_max": 10 },
  "erreurs_typiques": [
    { "code": "table_voisine", "desc": "Donne le résultat de la table voisine (7×8 = 54)" }
  ],
  "univers": ["nature", "cuisine", "construction", "sport", "espace"],
  "vocabulaire": ["multiplication", "facteur", "produit"],
  "note_pedagogique": "..."
}
```

### Champs issus de la PDA (ne pas inventer)

`ref_pda`, `libelle`, `annee_intro`, `annee_maitrise`, `cycle`, `vocabulaire`, `symboles`

Ces champs reflètent le document ministériel. Toute modification doit être vérifiée contre le PDF officiel.

### Champs propres à Numerix

`id`, `prerequis`, `generable`, `generateur`, `parametres`, `erreurs_typiques`, `univers`, `note_pedagogique`

Ce sont nos décisions produit. C'est là que se trouve la valeur ajoutée.

---

## Convention d'identifiants

```
ARI-SEN-A01a
│   │   │
│   │   └─ Référence PDA (section.numéro.sous-item)
│   └───── Section
└───────── Champ
```

**Champs :** `ARI` arithmétique · `GEO` géométrie · `MES` mesure · `STA` statistique · `PRO` probabilité

**Sections arithmétique :** `SEN` sens et écriture des nombres · `SOP` sens des opérations · `OPE` opérations sur des nombres

---

## Les trois champs qui font tourner le produit

### `generateur`

Nom de la fonction du moteur mathématique déterministe qui produit un problème pour cette compétence. Le LLM ne voit jamais cette couche. Chaque générateur doit :

1. Produire un énoncé paramétré
2. Retourner la bonne réponse
3. Retourner des distracteurs construits à partir des `erreurs_typiques`

### `erreurs_typiques`

C'est le champ qui permet le branchement narratif à trois issues. Sans lui, une mauvaise réponse est juste « fausse ». Avec lui, on sait *pourquoi* l'enfant s'est trompé, et l'histoire peut réagir de façon spécifique.

- `correct` → le héros réussit
- `erreur_typique` (distracteur connu) → complication narrative ciblée
- `erreur_aléatoire` → détour narratif générique

110 erreurs typiques sont catalogées. C'est le catalogue le plus difficile à reconstituer pour un concurrent.

### `univers`

Univers narratifs où cette compétence s'intègre naturellement. Huit univers disponibles :

`nature` · `espace` · `cuisine` · `sport` · `construction` · `medecine` · `science` · `echecs`

Toutes les compétences ne vont pas partout. Le calcul de périmètre vit bien dans `construction` et `sport`, mal dans `espace`. La sélectivité est le but du champ — un univers ajouté partout ne veut plus rien dire.

**Couverture actuelle :**

| Univers | Compétences | Force particulière |
|---|---|---|
| `science` | 75 | Univers universel — la mesure et la donnée touchent tout |
| `medecine` | 52 | Fractions, décimaux, masses, capacités, temps |
| `construction` | 44 | Géométrie, périmètre, aire, valeur de position |
| `echecs` | 43 | Coordonnées, table de 8, parité, probabilité, temps |
| `nature` | 41 | Dénombrement, partage, régularités |
| `cuisine` | 39 | Fractions, ratios, conversions de capacité |
| `espace` | 32 | Grands nombres, estimation, suites |
| `sport` | 29 | Comparaison, statistique, mesure de temps |

Chaque univers porte assez de compétences pour soutenir un parcours complet de la 1re à la 4e année sans jamais en sortir.

### Notes sur les trois univers ajoutés

**`echecs`** — l'échiquier 8×8 est un support concret pour la table de 8 ; les cases claires/foncées enseignent la parité ; la notation algébrique (e4, d5) est un vrai système de coordonnées ; la pendule rend la lecture du temps conséquente ; et évaluer quel coup est le plus probable est littéralement la compétence centrale du jeu.

**`medecine`** — le dosage selon la masse corporelle donne un enjeu réel aux conversions g/kg et L/mL ; le thermomètre est la droite numérique la plus familière ; la courbe de température est un diagramme à ligne brisée authentique ; le demi-comprimé est une fraction vécue.

**`science`** — univers le plus large (75/75) parce que mesurer, estimer, organiser des données et chercher des régularités traverse toute la mathématique du primaire. À utiliser avec discernement narratif : sa largeur en fait un bon univers par défaut, pas un univers d'identité forte.

---

## Validation

```bash
python valider_graphe.py
```

Vérifie :
1. Unicité des identifiants
2. Existence de tous les prérequis
3. Absence de cycle dans le graphe
4. Cohérence temporelle (un prérequis ne peut pas être introduit après)
5. Champs obligatoires présents

À exécuter après **chaque** modification. Un graphe avec un cycle bloque le planificateur en boucle infinie.

---

## État actuel

```
75 compétences · 110 erreurs typiques · 8 univers narratifs
Cycle 1 : 43 · Cycle 2 : 32
Profondeur maximale : 9 niveaux
Points d'entrée : 10 compétences sans prérequis
Version : 0.2.0
```

**Chaîne la plus profonde** (9 niveaux) : de la comptine jusqu'au calcul écrit sur les décimaux. C'est le squelette du parcours guidé.

---

## Comment étendre

**Ajouter une compétence :**
1. Trouver la ligne exacte dans le PDF officiel de la PDA
2. Copier `libelle` et `ref_pda` verbatim
3. Lire les colonnes d'années pour `annee_intro` / `annee_maitrise`
4. Définir les `prerequis` — quelle compétence doit être maîtrisée avant ?
5. Cataloguer au moins 2 `erreurs_typiques` (demander à un enseignant si nécessaire)
6. Choisir les `univers` où le contexte est naturel
7. Lancer `valider_graphe.py`

**Ajouter le cycle 3 (5e–6e) :** créer `pda-cycle3.json` avec la même structure, l'ajouter à la liste `FICHIERS` dans `valider_graphe.py`.

---

## Prochaine couche

Le moteur mathématique déterministe — un générateur par valeur de `generateur` référencée ici. 75 générateurs au total, mais seulement une douzaine sont nécessaires pour un premier parcours jouable.

Priorité pour le MVP :
`gen_faits_addition` · `gen_faits_multiplication` · `gen_calcul_mental_add_soustr` ·
`gen_sens_multiplication_division` · `gen_mult_div_personnelle` · `gen_terme_manquant_add_soustr`

Ces six couvrent un parcours complet de la 1re à la 4e année.
