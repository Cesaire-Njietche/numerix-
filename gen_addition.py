"""
Générateurs du champ additif.

  gen_faits_addition          — ARI-OPE-A02a / A02c
  gen_calcul_mental_add_soustr — ARI-OPE-A03a
  gen_terme_manquant_add_soustr — ARI-OPE-A05

Tous déterministes. Aucun LLM.
"""

from __future__ import annotations

import random

from base import (
    Probleme, Distracteur, assembler_choix, borne_par_cycle, echelle
)


# ══════════════════════════════════════════════════════════════════════
#  1. gen_faits_addition — ARI-OPE-A02a / A02c
# ══════════════════════════════════════════════════════════════════════

def gen_faits_addition(
    rng: random.Random,
    termes_max: int = 10,
    mode: str = "construction",
    operation: str | None = None,
    difficulte_cible: float | None = None,
    **_,
) -> Probleme:
    """Faits numériques de l'addition (0+0 à 10+10) et soustractions correspondantes.

    Erreurs typiques (PDA / Imhotep) :
      - erreur_plus_un    : résultat décalé de 1 (surcomptage)
      - confusion_proche  : confond avec un fait numérique voisin
      - lenteur           : géré par le temps de réponse, pas par un distracteur
    """
    if operation is None:
        operation = rng.choice(["addition", "soustraction"])

    a, b = _tirer_termes_additifs(rng, termes_max, difficulte_cible)

    if operation == "addition":
        reponse = a + b
        enonce = f"{a} + {b} = ?"
        contexte = {
            "operation": "addition",
            "sens": "reunion",
            "terme_1": a,
            "terme_2": b,
            "resultat": reponse,
            "role_resultat": "total",
        }
        distracteurs = [
            Distracteur(reponse + 1, "erreur_plus_un",
                        "Résultat décalé de 1 vers le haut (surcomptage)"),
            Distracteur(reponse - 1, "erreur_plus_un",
                        "Résultat décalé de 1 vers le bas (surcomptage)"),
            Distracteur(a + b + 2, "confusion_proche",
                        "Confond avec le fait numérique voisin"),
            Distracteur(abs(a - b), "operation_inverse",
                        "Soustrait au lieu d'additionner"),
        ]
    else:
        total = a + b
        reponse = a
        enonce = f"{total} − {b} = ?"
        contexte = {
            "operation": "soustraction",
            "sens": "retrait",
            "depart": total,
            "retire": b,
            "resultat": reponse,
            "role_resultat": "reste",
        }
        distracteurs = [
            Distracteur(reponse + 1, "erreur_plus_un",
                        "Résultat décalé de 1 (surcomptage)"),
            Distracteur(reponse - 1, "erreur_plus_un",
                        "Résultat décalé de 1 (surcomptage)"),
            Distracteur(total + b, "operation_inverse",
                        "Additionne au lieu de soustraire"),
            Distracteur(b, "confusion_proche",
                        "Donne le terme retiré au lieu du reste"),
        ]

    rng.shuffle(distracteurs)
    choix, retenus = assembler_choix(reponse, distracteurs, rng)

    diff = _difficulte_fait_additif(a, b)

    return Probleme(
        competence_id="ARI-OPE-A02c" if mode == "maitrise" else "ARI-OPE-A02a",
        generateur="gen_faits_addition",
        enonce_math=enonce,
        reponse=reponse,
        distracteurs=retenus,
        choix=choix,
        contexte_narratif=contexte,
        cles_reponse=["resultat"],
        difficulte=diff,
        metadonnees={
            "mode": mode,
            "franchit_dix": (a + b > 10) and (a < 10 and b < 10),
            "est_double": a == b,
            "temps_cible_ms": 4000 if mode == "maitrise" else None,
        },
    )


def _tirer_termes_additifs(rng, termes_max, difficulte_cible):
    """Sélectionne deux termes, en visant la difficulté demandée si fournie."""
    if difficulte_cible is None:
        return rng.randint(0, termes_max), rng.randint(0, termes_max)

    candidats = [
        (a, b)
        for a in range(termes_max + 1)
        for b in range(termes_max + 1)
    ]
    candidats.sort(key=lambda p: abs(_difficulte_fait_additif(*p) - difficulte_cible))
    pool = candidats[:12]
    return rng.choice(pool)


def _difficulte_fait_additif(a: int, b: int) -> float:
    """Le franchissement de la dizaine est le vrai obstacle, pas la taille."""
    score = 0.0
    if a == 0 or b == 0:
        score += 0.0
    elif a == 1 or b == 1:
        score += 0.10
    elif a == b:
        score += 0.25            # doubles : mémorisés tôt
    elif a + b == 10:
        score += 0.30            # compléments à 10 : enseignés explicitement
    else:
        score += 0.50
    if a + b > 10 and a < 10 and b < 10:
        score += 0.35            # franchissement de la dizaine
    score += echelle(max(a, b), 0, 10) * 0.15
    return round(min(1.0, score), 2)


# ══════════════════════════════════════════════════════════════════════
#  2. gen_calcul_mental_add_soustr — ARI-OPE-A03a
# ══════════════════════════════════════════════════════════════════════

def gen_calcul_mental_add_soustr(
    rng: random.Random,
    cycle: int = 1,
    max_c1: int = 100,
    max_c2: int = 1000,
    operation: str | None = None,
    forcer_retenue: bool | None = None,
    **_,
) -> Probleme:
    """Somme ou différence de deux nombres naturels par processus personnels.

    Erreurs typiques :
      - oubli_retenue  : oublie la retenue
      - emprunt_rate   : soustrait le petit chiffre du grand, colonne par colonne
    """
    borne = borne_par_cycle(cycle, max_c1, max_c2)
    if operation is None:
        operation = rng.choice(["addition", "soustraction"])

    if forcer_retenue is None:
        forcer_retenue = rng.random() < 0.6   # majorité de cas avec obstacle

    if operation == "addition":
        a, b = _paire_addition(rng, borne, forcer_retenue)
        reponse = a + b
        enonce = f"{a} + {b} = ?"
        contexte = {
            "operation": "addition",
            "sens": "reunion",
            "terme_1": a, "terme_2": b,
            "resultat": reponse,
            "role_resultat": "total",
        }
        distracteurs = [
            Distracteur(_sans_retenue_addition(a, b), "oubli_retenue",
                        "Oublie la retenue lors de l'addition"),
            Distracteur(reponse + 10, "retenue_ajoutee_deux_fois",
                        "Reporte la retenue deux fois"),
            Distracteur(abs(a - b), "operation_inverse",
                        "Soustrait au lieu d'additionner"),
        ]
    else:
        a, b = _paire_soustraction(rng, borne, forcer_retenue)
        reponse = a - b
        enonce = f"{a} − {b} = ?"
        contexte = {
            "operation": "soustraction",
            "sens": "retrait",
            "depart": a, "retire": b,
            "resultat": reponse,
            "role_resultat": "reste",
        }
        distracteurs = [
            Distracteur(_emprunt_rate(a, b), "emprunt_rate",
                        "Soustrait le petit chiffre du grand dans chaque colonne"),
            Distracteur(a + b, "operation_inverse",
                        "Additionne au lieu de soustraire"),
            Distracteur(reponse - 10, "oubli_retenue",
                        "Erreur de dizaine lors de l'emprunt"),
        ]

    rng.shuffle(distracteurs)
    choix, retenus = assembler_choix(reponse, distracteurs, rng)

    return Probleme(
        competence_id="ARI-OPE-A03a",
        generateur="gen_calcul_mental_add_soustr",
        enonce_math=enonce,
        reponse=reponse,
        distracteurs=retenus,
        choix=choix,
        contexte_narratif=contexte,
        cles_reponse=["resultat"],
        difficulte=echelle(max(contexte.get("terme_1", a), b), 0, borne) * 0.6
                   + (0.4 if forcer_retenue else 0.0),
        metadonnees={"cycle": cycle, "avec_obstacle": forcer_retenue},
    )


def _paire_addition(rng, borne, avec_retenue):
    for _ in range(80):
        a = rng.randint(10, borne - 10)
        b = rng.randint(10, borne - a) if borne - a > 10 else rng.randint(1, 9)
        if _a_une_retenue(a, b) == avec_retenue:
            return a, b
    return rng.randint(10, borne // 2), rng.randint(10, borne // 2)


def _paire_soustraction(rng, borne, avec_emprunt):
    for _ in range(80):
        a = rng.randint(20, borne)
        b = rng.randint(1, a - 1)
        if _a_un_emprunt(a, b) == avec_emprunt:
            return a, b
    a = rng.randint(20, borne)
    return a, rng.randint(1, a - 1)


def _a_une_retenue(a: int, b: int) -> bool:
    while a > 0 or b > 0:
        if (a % 10) + (b % 10) >= 10:
            return True
        a, b = a // 10, b // 10
    return False


def _a_un_emprunt(a: int, b: int) -> bool:
    while b > 0:
        if (a % 10) < (b % 10):
            return True
        a, b = a // 10, b // 10
    return False


def _sans_retenue_addition(a: int, b: int) -> int:
    """Simule l'erreur : additionne chaque colonne sans propager la retenue."""
    res, pos = 0, 1
    while a > 0 or b > 0:
        res += ((a % 10) + (b % 10)) % 10 * pos
        a, b, pos = a // 10, b // 10, pos * 10
    return res


def _emprunt_rate(a: int, b: int) -> int:
    """Simule l'erreur : |chiffre_a − chiffre_b| colonne par colonne."""
    res, pos = 0, 1
    while a > 0 or b > 0:
        res += abs((a % 10) - (b % 10)) * pos
        a, b, pos = a // 10, b // 10, pos * 10
    return res


# ══════════════════════════════════════════════════════════════════════
#  3. gen_terme_manquant_add_soustr — ARI-OPE-A05
# ══════════════════════════════════════════════════════════════════════

FORMES_ADDITIVES = ["a+b=?", "a+?=c", "?+b=c", "a-b=?", "a-?=c", "?-b=c"]


def gen_terme_manquant_add_soustr(
    rng: random.Random,
    cycle: int = 1,
    max_c1: int = 100,
    max_c2: int = 1000,
    formes: list[str] | None = None,
    forme: str | None = None,
    **kwargs,
) -> Probleme:
    """Terme manquant dans une équation additive.

    Erreurs typiques :
      - operation_directe : applique l'opération visible au lieu de l'inverse
      - position_ignoree  : traite ?−b=c comme b−?=c
    """
    # Le graphe PDA fournit « max » comme alias de borne
    alias_max = kwargs.get("max")
    borne = alias_max if alias_max is not None else borne_par_cycle(cycle, max_c1, max_c2)
    formes = [f for f in (formes or FORMES_ADDITIVES) if f in FORMES_ADDITIVES]
    forme = forme or rng.choice(formes or FORMES_ADDITIVES)

    a = rng.randint(2, max(4, borne // 2))
    b = rng.randint(1, max(2, borne // 2))
    c = a + b

    if forme == "a+b=?":
        enonce, reponse = f"{a} + {b} = ?", c
        distracteurs = [
            Distracteur(abs(a - b), "operation_directe", "Soustrait au lieu d'additionner"),
            Distracteur(c + 1, "erreur_plus_un", "Résultat décalé de 1"),
            Distracteur(c - 1, "erreur_plus_un", "Résultat décalé de 1"),
        ]
        inconnue = "total"

    elif forme == "a+?=c":
        enonce, reponse = f"{a} + ? = {c}", b
        distracteurs = [
            Distracteur(a + c, "operation_directe", "Additionne au lieu de soustraire"),
            Distracteur(c, "position_ignoree", "Donne le total au lieu du terme manquant"),
            Distracteur(a, "position_ignoree", "Recopie le terme connu"),
        ]
        inconnue = "terme_2"

    elif forme == "?+b=c":
        enonce, reponse = f"? + {b} = {c}", a
        distracteurs = [
            Distracteur(b + c, "operation_directe", "Additionne au lieu de soustraire"),
            Distracteur(c, "position_ignoree", "Donne le total au lieu du terme manquant"),
            Distracteur(b, "position_ignoree", "Recopie le terme connu"),
        ]
        inconnue = "terme_1"

    elif forme == "a-b=?":
        enonce, reponse = f"{c} − {b} = ?", a
        distracteurs = [
            Distracteur(c + b, "operation_directe", "Additionne au lieu de soustraire"),
            Distracteur(a + 1, "erreur_plus_un", "Résultat décalé de 1"),
            Distracteur(b, "position_ignoree", "Donne le terme retiré"),
        ]
        inconnue = "reste"

    elif forme == "a-?=c":
        enonce, reponse = f"{c} − ? = {a}", b
        distracteurs = [
            Distracteur(c + a, "operation_directe", "Additionne au lieu de soustraire"),
            Distracteur(a, "position_ignoree", "Recopie le résultat visible"),
            Distracteur(c, "position_ignoree", "Recopie le départ"),
        ]
        inconnue = "retire"

    else:  # "?-b=c"
        enonce, reponse = f"? − {b} = {a}", c
        distracteurs = [
            Distracteur(abs(a - b), "operation_directe", "Soustrait au lieu d'additionner"),
            Distracteur(a, "position_ignoree", "Recopie le résultat visible"),
            Distracteur(b, "position_ignoree", "Recopie le terme retiré"),
        ]
        inconnue = "depart"

    rng.shuffle(distracteurs)
    choix, retenus = assembler_choix(reponse, distracteurs, rng)

    difficulte = 0.25 if forme in ("a+b=?", "a-b=?") else 0.65
    if forme == "?-b=c":
        difficulte = 0.85     # la forme la plus difficile du lot

    return Probleme(
        competence_id="ARI-OPE-A05",
        generateur="gen_terme_manquant_add_soustr",
        enonce_math=enonce,
        reponse=reponse,
        distracteurs=retenus,
        choix=choix,
        contexte_narratif={
            "operation": "addition" if "+" in enonce else "soustraction",
            "sens": "information_manquante",
            "forme": forme,
            "inconnue": inconnue,
            "valeurs_connues": {"a": a, "b": b, "total": c},
            "resultat": reponse,
            "role_resultat": inconnue,
            "amorce_narrative": "une information manque dans le plan",
        },
        # « valeurs_connues » contient a, b et le total : selon la forme,
        # l'un des trois EST la réponse. On retire le bloc entier.
        cles_reponse=["resultat", "valeurs_connues", "role_resultat"],
        difficulte=difficulte,
        metadonnees={"cycle": cycle, "forme": forme},
    )
