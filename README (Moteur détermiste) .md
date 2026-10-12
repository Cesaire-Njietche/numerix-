# Moteur mathématique déterministe

Couche 2 de l'architecture Numerix. **Aucun LLM n'intervient ici.**

Le calcul, la génération des énoncés, la vérification des réponses et la construction des distracteurs sont du code Python testable. C'est ce qui garantit qu'un enfant ne recevra jamais une réponse mathématique fausse, quelle que soit l'insistance avec laquelle il affirme le contraire.

---

## Les six générateurs

| Générateur | Compétences PDA | Années |
|---|---|---|
| `gen_faits_addition` | ARI-OPE-A02a / A02c | 1re–2e |
| `gen_calcul_mental_add_soustr` | ARI-OPE-A03a | 1re–4e |
| `gen_terme_manquant_add_soustr` | ARI-OPE-A05 | 2e–4e |
| `gen_faits_multiplication` | ARI-OPE-A06a / A06c | 3e–4e |
| `gen_sens_multiplication_division` | ARI-SOP-A03a | 3e |
| `gen_mult_div_personnelle` | ARI-OPE-A07a | 4e |

Ces six couvrent un parcours complet de la 1re à la 4e année.

---

## La règle d'étanchéité

Le moteur narratif reçoit **deux charges distinctes**, jamais la même.

### Phase 1 — mise en scène (`pour_le_llm_mise_en_scene()`)

Envoyée *avant* que l'enfant réponde. Toute clé listée dans `cles_reponse` est retirée du contexte.

```python
{
  "phase": "mise_en_scene",
  "enonce_math": "340 ÷ 7 = ? (avec reste)",
  "contexte_narratif": {
    "operation": "division",
    "sens": "partage",
    "total": 340,
    "nb_groupes": 7
  },
  "choix_affiches": [[49,4], [47,11], [48,0], [48,4]]
}
```

Le LLM ne peut pas révéler la réponse : **elle n'est pas dans son contexte.** Ce n'est pas une consigne qu'on lui demande de respecter, c'est une impossibilité structurelle.

### Phase 2 — dénouement (`pour_le_llm_denouement(resultat)`)

Envoyée *après* la réponse. Le verdict est déjà rendu par `Probleme.evaluer()`. Le LLM reçoit le contexte complet et une consigne narrative — il habille une conclusion, il n'en produit aucune.

```python
{
  "phase": "denouement",
  "issue": "erreur_typique",
  "code_erreur": "arrondi_quotient",
  "nature_de_l_erreur": "Arrondit le quotient vers le haut sans traiter le reste",
  "consigne": "Complication narrative ciblée sur cette erreur précise..."
}
```

### Le contrôle automatique

`Probleme.fuite_detectee()` compare chaque valeur du contexte de mise en scène à la réponse attendue, en excluant les nombres déjà visibles dans l'énoncé (dans `4 + 0 = ?`, le terme 4 égale la réponse par coïncidence arithmétique — l'enfant le lit de toute façon).

La suite de tests exécute ce contrôle 720 fois. Il doit toujours retourner zéro.

---

## Le branchement à trois issues

C'est ce qui distingue Numerix d'une application de calcul mental.

```python
p = graphe.generer("ARI-OPE-A07a")
resultat = p.evaluer(reponse_enfant)

resultat.type            # CORRECT | ERREUR_TYPIQUE | ERREUR_ALEATOIRE
resultat.code_erreur     # "reste_ignore", "table_voisine", ...
resultat.description_erreur
```

| Issue | Ce que le moteur narratif en fait |
|---|---|
| `CORRECT` | Le héros réussit. Le calcul rend l'action possible. |
| `ERREUR_TYPIQUE` | Complication ciblée sur cette erreur précise. Jamais un échec — un détour. |
| `ERREUR_ALEATOIRE` | Un imprévu relance la situation. Ni jugement, ni correction explicite. |

Les distracteurs ne sont pas des nombres au hasard : chacun simule une erreur documentée dans le graphe PDA. `_sans_retenue_addition()` reproduit exactement ce que fait un enfant qui oublie la retenue. `_emprunt_rate()` reproduit la soustraction colonne par colonne du plus petit chiffre au plus grand.

C'est pour ça que le moteur sait *pourquoi* l'enfant s'est trompé, et pas seulement *qu'il* s'est trompé.

---

## Usage

```python
import random
from registre import GraphePDA

g = GraphePDA(".")

# Par compétence
p = g.generer("ARI-OPE-A06a", seed=42)

# Par univers et par année
p = g.generer_pour_univers("echecs", annee=3, seed=42)

# En visant une difficulté
p = g.generer("ARI-OPE-A06a", difficulte_cible=0.8)

# Parcours progressif
maitrisees = {"ARI-OPE-A02a"}
suivantes = g.disponibles(maitrisees)
```

Toute génération est reproductible à graine fixe — condition nécessaire pour rejouer une session, déboguer un parcours, ou écrire des tests stables.

---

## Tests

```bash
python tests_moteur.py
```

Sept familles de vérifications :

1. **Justesse mathématique** — 2400 problèmes recalculés indépendamment
2. **Intégrité des choix** — 4 options distinctes, réponse présente, aucun distracteur dégénéré
3. **Branchement à trois issues** — les trois chemins se déclenchent correctement
4. **Déterminisme** — même graine, même problème
5. **Étanchéité** — 720 contrôles de fuite vers le LLM
6. **Progression de difficulté** — le ciblage discrimine réellement
7. **Intégration au graphe PDA** — génération via les 8 compétences couvertes, 8 univers, parcours enchaîné

---

## Ajouter un générateur

1. Écrire la fonction dans `gen_addition.py` ou `gen_multiplication.py` (ou un nouveau module par champ)
2. Signature : `def mon_gen(rng: random.Random, **params) -> Probleme`
3. Déclarer `cles_reponse` — les clés du contexte qui révèlent la réponse
4. Fournir au moins 3 distracteurs, chacun avec un `code_erreur` présent dans le graphe PDA
5. Enregistrer dans `REGISTRE` (`registre.py`)
6. Lancer `tests_moteur.py` — les sept familles s'appliquent automatiquement

Le générateur doit tolérer les paramètres du graphe PDA tels quels : certains champs y sont des listes (`sens`, `formes`) et certains alias diffèrent (`max` vs `max_val`). Absorber les inconnus avec `**kwargs`.

---

## Dette connue

`GraphePDA.prerequis_satisfaits(..., ignorer_non_implementes=True)` neutralise les prérequis dont le générateur n'existe pas encore. Sans ça, aucune compétence ne serait atteignable tant que les 75 générateurs ne sont pas écrits.

**À repasser à `False`** une fois la couverture complète.
