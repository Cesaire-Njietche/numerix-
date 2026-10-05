"""
Générateurs du champ multiplicatif.

  gen_faits_multiplication        — ARI-OPE-A06a / A06c
  gen_sens_multiplication_division — ARI-SOP-A03a
  gen_mult_div_personnelle        — ARI-OPE-A07a

Tous déterministes. Aucun LLM.
"""

from __future__ import annotations

import random

from base import Probleme, Distracteur, assembler_choix, echelle


# ══════════════════════════════════════════════════════════════════════
#  4. gen_faits_multiplication — ARI-OPE-A06a / A06c
# ══════════════════════════════════════════════════════════════════════

def gen_faits_multiplication(
    rng: random.Random,
    facteurs_max: int = 10,
    mode: str = "construction",
    operation: str | None = None,
    difficulte_cible: float | None = None,
    tables_cibles: list[int] | None = None,
    **_,
) -> Probleme:
    """Faits numériques de la multiplication (0×0 à 10×10) et divisions correspondantes.

    Erreurs typiques :
      - table_voisine    : résultat de la table voisine (7×8 = 54)
      - addition_facteurs: additionne les facteurs
      - zero_un          : confusion sur les propriétés de 0 et 1
    """
    if operation is None:
        operation = rng.choice(["multiplication", "division"])

    a, b = _tirer_facteurs(rng, facteurs_max, difficulte_cible, tables_cibles)

    if operation == "multiplication":
        reponse = a * b
        enonce = f"{a} × {b} = ?"
        contexte = {
            "operation": "multiplication",
            "sens": "addition_repetee",
            "nb_groupes": a,
            "par_groupe": b,
            "resultat": reponse,
            "role_resultat": "total",
        }
        distracteurs = [
            Distracteur(a * (b + 1), "table_voisine",
                        f"Résultat de {a} × {b + 1} au lieu de {a} × {b}"),
            Distracteur(a * (b - 1), "table_voisine",
                        f"Résultat de {a} × {b - 1} au lieu de {a} × {b}"),
            Distracteur(a + b, "addition_facteurs",
                        "Additionne les facteurs au lieu de multiplier"),
        ]
        if a in (0, 1) or b in (0, 1):
            distracteurs.insert(0, Distracteur(
                a if b in (0, 1) else b, "zero_un",
                "Confusion sur la propriété de 0 ou de 1"))
    else:
        if b == 0:
            b = rng.randint(1, facteurs_max)
        produit = a * b
        reponse = a
        enonce = f"{produit} ÷ {b} = ?"
        contexte = {
            "operation": "division",
            "sens": "partage",
            "total": produit,
            "nb_groupes": b,
            "par_groupe": reponse,
            "resultat": reponse,
            "role_resultat": "taille_du_groupe",
        }
        distracteurs = [
            Distracteur(reponse + 1, "table_voisine", "Résultat de la table voisine"),
            Distracteur(max(reponse - 1, 0), "table_voisine", "Résultat de la table voisine"),
            Distracteur(produit - b, "operation_inverse",
                        "Soustrait au lieu de diviser"),
            Distracteur(b, "division_inversee", "Inverse dividende et diviseur"),
        ]

    rng.shuffle(distracteurs)
    choix, retenus = assembler_choix(reponse, distracteurs, rng)

    return Probleme(
        competence_id="ARI-OPE-A06c" if mode == "maitrise" else "ARI-OPE-A06a",
        generateur="gen_faits_multiplication",
        enonce_math=enonce,
        reponse=reponse,
        distracteurs=retenus,
        choix=choix,
        contexte_narratif=contexte,
        cles_reponse=(["resultat"] if operation == "multiplication"
                      else ["resultat", "par_groupe"]),
        difficulte=_difficulte_fait_multiplicatif(a, b),
        metadonnees={
            "mode": mode,
            "table": max(a, b),
            "est_carre": a == b,
            "temps_cible_ms": 5000 if mode == "maitrise" else None,
        },
    )


def _tirer_facteurs(rng, facteurs_max, difficulte_cible, tables_cibles):
    if tables_cibles:
        a = rng.choice(tables_cibles)
        b = rng.randint(0, facteurs_max)
        return (a, b) if rng.random() < 0.5 else (b, a)

    if difficulte_cible is None:
        return rng.randint(0, facteurs_max), rng.randint(0, facteurs_max)

    candidats = [(a, b) for a in range(facteurs_max + 1) for b in range(facteurs_max + 1)]
    candidats.sort(key=lambda p: abs(_difficulte_fait_multiplicatif(*p) - difficulte_cible))
    return rng.choice(candidats[:12])


def _difficulte_fait_multiplicatif(a: int, b: int) -> float:
    """×0, ×1, ×10 sont triviaux. ×6, ×7, ×8 sont les plus coûteux à mémoriser."""
    faciles = {0, 1, 10}
    moyens = {2, 5, 9}
    if a in faciles or b in faciles:
        return 0.1
    score = 0.35
    if a == b:
        score = 0.30                        # carrés : ancrés visuellement
    elif a in moyens or b in moyens:
        score = 0.45
    else:
        score = 0.75                        # 3,4,6,7,8 entre eux
    score += echelle(max(a, b), 2, 10) * 0.2
    return round(min(1.0, score), 2)


# ══════════════════════════════════════════════════════════════════════
#  5. gen_sens_multiplication_division — ARI-SOP-A03a
# ══════════════════════════════════════════════════════════════════════
#  Ce générateur ne demande PAS de calculer. Il demande de reconnaître
#  la structure de la situation — compétence C1 du PFÉQ.
# ══════════════════════════════════════════════════════════════════════

SENS_MULTIPLICATIFS = [
    "disposition_rectangulaire",
    "addition_repetee",
    "partage",
    "contenance",
]


def gen_sens_multiplication_division(
    rng: random.Random,
    sens: str | list[str] | None = None,
    max_val: int = 100,
    format_question: str | None = None,
    **kwargs,
) -> Probleme:
    """Reconnaître la structure d'une situation multiplicative ou de division.

    Deux formats :
      - "expression"  : quelle expression traduit la situation ?
      - "role"        : que représente le résultat ?

    Erreurs typiques :
      - partage_vs_contenance   : confond « combien par groupe » et « combien de groupes »
      - addition_au_lieu_mult   : additionne les deux nombres

    `sens` accepte une chaîne ou une liste — le graphe PDA fournit une liste
    d'options ; l'appelant peut imposer un sens précis.
    """
    alias_max = kwargs.get("max")
    if alias_max is not None:
        max_val = alias_max

    if sens is None:
        sens = rng.choice(SENS_MULTIPLICATIFS)
    elif isinstance(sens, (list, tuple)):
        valides = [s for s in sens if s in SENS_MULTIPLICATIFS]
        sens = rng.choice(valides or SENS_MULTIPLICATIFS)

    format_question = format_question or rng.choice(["expression", "role"])

    # nb_groupes doit différer de par_groupe : sinon « total ÷ nb_groupes » et
    # « total ÷ par_groupe » sont la même expression, et le distracteur
    # partage_vs_contenance devient indistinguable de la réponse.
    nb_groupes = rng.randint(2, 12)
    plafond = min(12, max(3, max_val // nb_groupes))
    candidats = [v for v in range(2, plafond + 1) if v != nb_groupes]
    par_groupe = rng.choice(candidats) if candidats else nb_groupes + 1
    total = nb_groupes * par_groupe

    if sens in ("disposition_rectangulaire", "addition_repetee"):
        # On connaît les groupes, on cherche le total → multiplication
        contexte = {
            "operation": "multiplication",
            "sens": sens,
            "nb_groupes": nb_groupes,
            "par_groupe": par_groupe,
            "total": total,
            "resultat": total,
            "role_resultat": "total",
            "inconnue": "total",
        }
        if format_question == "expression":
            enonce = (f"Il y a {nb_groupes} groupes de {par_groupe}. "
                      f"Quelle expression donne le total ?")
            reponse = f"{nb_groupes} × {par_groupe}"
            distracteurs = [
                Distracteur(f"{nb_groupes} + {par_groupe}", "addition_au_lieu_mult",
                            "Additionne les deux nombres au lieu de multiplier"),
                Distracteur(f"{total} ÷ {par_groupe}", "operation_inverse",
                            "Divise alors que le total est inconnu"),
                Distracteur(f"{nb_groupes} − {par_groupe}", "addition_au_lieu_mult",
                            "Soustrait les deux nombres"),
            ]
        else:
            enonce = (f"On calcule {nb_groupes} × {par_groupe}. "
                      f"Que représente le résultat ?")
            reponse = "le nombre total d'objets"
            distracteurs = [
                Distracteur("le nombre de groupes", "partage_vs_contenance",
                            "Confond le total avec le nombre de groupes"),
                Distracteur("le nombre dans chaque groupe", "partage_vs_contenance",
                            "Confond le total avec la taille d'un groupe"),
                Distracteur("la différence entre les deux nombres", "addition_au_lieu_mult",
                            "Interprète l'opération comme une comparaison"),
            ]

    elif sens == "partage":
        # On connaît le total et le NOMBRE de groupes → on cherche la TAILLE
        contexte = {
            "operation": "division",
            "sens": "partage",
            "total": total,
            "nb_groupes": nb_groupes,
            "par_groupe": par_groupe,
            "resultat": par_groupe,
            "role_resultat": "taille_du_groupe",
            "inconnue": "par_groupe",
        }
        if format_question == "expression":
            enonce = (f"On partage {total} objets également entre {nb_groupes} groupes. "
                      f"Quelle expression donne le nombre par groupe ?")
            reponse = f"{total} ÷ {nb_groupes}"
            distracteurs = [
                Distracteur(f"{total} ÷ {par_groupe}", "partage_vs_contenance",
                            "Divise par la taille du groupe au lieu du nombre de groupes"),
                Distracteur(f"{total} × {nb_groupes}", "operation_inverse",
                            "Multiplie au lieu de diviser"),
                Distracteur(f"{total} − {nb_groupes}", "addition_au_lieu_mult",
                            "Soustrait au lieu de diviser"),
            ]
        else:
            enonce = (f"On partage {total} objets entre {nb_groupes} groupes. "
                      f"On calcule {total} ÷ {nb_groupes}. Que représente le résultat ?")
            reponse = "le nombre d'objets dans chaque groupe"
            distracteurs = [
                Distracteur("le nombre de groupes", "partage_vs_contenance",
                            "Confond taille du groupe et nombre de groupes"),
                Distracteur("le nombre total d'objets", "operation_inverse",
                            "Confond le résultat avec le point de départ"),
                Distracteur("le nombre d'objets restants", "reste_ignore",
                            "Interprète le quotient comme un reste"),
            ]

    else:  # contenance
        # On connaît le total et la TAILLE des groupes → on cherche le NOMBRE
        contexte = {
            "operation": "division",
            "sens": "contenance",
            "total": total,
            "nb_groupes": nb_groupes,
            "par_groupe": par_groupe,
            "resultat": nb_groupes,
            "role_resultat": "nombre_de_groupes",
            "inconnue": "nb_groupes",
        }
        if format_question == "expression":
            enonce = (f"On répartit {total} objets par paquets de {par_groupe}. "
                      f"Quelle expression donne le nombre de paquets ?")
            reponse = f"{total} ÷ {par_groupe}"
            distracteurs = [
                Distracteur(f"{total} ÷ {nb_groupes}", "partage_vs_contenance",
                            "Divise par le nombre de groupes au lieu de leur taille"),
                Distracteur(f"{total} × {par_groupe}", "operation_inverse",
                            "Multiplie au lieu de diviser"),
                Distracteur(f"{par_groupe} ÷ {total}", "division_inversee",
                            "Inverse dividende et diviseur"),
            ]
        else:
            enonce = (f"On répartit {total} objets par paquets de {par_groupe}. "
                      f"On calcule {total} ÷ {par_groupe}. Que représente le résultat ?")
            reponse = "le nombre de paquets"
            distracteurs = [
                Distracteur("le nombre d'objets par paquet", "partage_vs_contenance",
                            "Confond nombre de groupes et taille du groupe"),
                Distracteur("le nombre total d'objets", "operation_inverse",
                            "Confond le résultat avec le point de départ"),
                Distracteur("le nombre d'objets restants", "reste_ignore",
                            "Interprète le quotient comme un reste"),
            ]

    rng.shuffle(distracteurs)
    choix, retenus = assembler_choix(reponse, distracteurs, rng, borne_min=None)

    difficulte = {
        "addition_repetee": 0.30,
        "disposition_rectangulaire": 0.40,
        "partage": 0.60,
        "contenance": 0.80,      # le sens le plus difficile du 2e cycle
    }[sens]

    return Probleme(
        competence_id="ARI-SOP-A03a",
        generateur="gen_sens_multiplication_division",
        enonce_math=enonce,
        reponse=reponse,
        distracteurs=retenus,
        choix=choix,
        contexte_narratif=contexte,
        # Au format « role », role_resultat EST la réponse formulée autrement.
        cles_reponse=["resultat", "role_resultat", "inconnue"],
        difficulte=difficulte,
        metadonnees={"sens": sens, "format": format_question, "sans_calcul": True},
    )


# ══════════════════════════════════════════════════════════════════════
#  6. gen_mult_div_personnelle — ARI-OPE-A07a
# ══════════════════════════════════════════════════════════════════════

def gen_mult_div_personnelle(
    rng: random.Random,
    dividende_max: int = 999,
    diviseur_max: int = 9,
    operation: str | None = None,
    avec_reste: bool | None = None,
    **_,
) -> Probleme:
    """Produit ou quotient d'un nombre à 3 chiffres par un nombre à 1 chiffre.
    Le reste est exprimé selon le contexte — c'est le cœur pédagogique.

    Erreurs typiques :
      - reste_ignore             : ignore le reste alors que le contexte l'exige
      - reste_superieur_diviseur : laisse un reste plus grand que le diviseur
    """
    if operation is None:
        operation = rng.choice(["multiplication", "division"])

    if operation == "multiplication":
        a = rng.randint(100, min(999, dividende_max))
        b = rng.randint(2, diviseur_max)
        reponse = a * b
        enonce = f"{a} × {b} = ?"
        contexte = {
            "operation": "multiplication",
            "sens": "addition_repetee",
            "nb_groupes": b,
            "par_groupe": a,
            "resultat": reponse,
            "role_resultat": "total",
            "a_un_reste": False,
        }
        distracteurs = [
            Distracteur(_mult_sans_retenue(a, b), "oubli_retenue",
                        "Oublie la retenue dans la multiplication"),
            Distracteur(a * (b - 1), "table_voisine", "Utilise la table voisine"),
            Distracteur(a + b, "addition_facteurs", "Additionne au lieu de multiplier"),
        ]
        metadonnees = {"reste": 0}

    else:
        b = rng.randint(2, diviseur_max)
        if avec_reste is None:
            avec_reste = rng.random() < 0.65     # majorité avec reste : c'est le but
        if avec_reste:
            quotient = rng.randint(10, max(11, dividende_max // b))
            reste = rng.randint(1, b - 1)
            a = quotient * b + reste
        else:
            quotient = rng.randint(10, max(11, dividende_max // b))
            reste = 0
            a = quotient * b

        reponse = (quotient, reste)
        enonce = f"{a} ÷ {b} = ? (avec reste)"
        contexte = {
            "operation": "division",
            "sens": "partage",
            "total": a,
            "nb_groupes": b,
            "par_groupe": quotient,
            "reste": reste,
            "resultat": quotient,
            "role_resultat": "taille_du_groupe",
            "a_un_reste": reste > 0,
            "amorce_narrative": (
                f"il reste {reste} — que fait-on de ce qui ne rentre pas ?"
                if reste > 0 else "tout se répartit exactement"
            ),
        }
        distracteurs = [
            Distracteur((quotient + 1, reste), "arrondi_quotient",
                        "Arrondit le quotient vers le haut sans traiter le reste"),
            Distracteur((quotient - 1, reste + b), "reste_superieur_diviseur",
                        "Laisse un reste plus grand que le diviseur"),
        ]
        if reste > 0:
            # Le piège central : ignorer un reste qui existe
            distracteurs.insert(0, Distracteur(
                (quotient, 0), "reste_ignore",
                "Ignore le reste alors que le contexte l'exige"))
        else:
            # Division exacte : le piège est d'inventer un reste
            distracteurs.insert(0, Distracteur(
                (quotient, 1), "reste_invente",
                "Invente un reste alors que la division est exacte"))
            distracteurs.append(Distracteur(
                (quotient - 1, b), "reste_superieur_diviseur",
                "Laisse un reste égal au diviseur au lieu de compléter le quotient"))
        metadonnees = {"reste": reste, "quotient": quotient, "diviseur": b}

    rng.shuffle(distracteurs)
    choix, retenus = assembler_choix(reponse, distracteurs, rng, borne_min=None)

    return Probleme(
        competence_id="ARI-OPE-A07a",
        generateur="gen_mult_div_personnelle",
        enonce_math=enonce,
        reponse=reponse,
        distracteurs=retenus,
        choix=choix,
        contexte_narratif=contexte,
        cles_reponse=(["resultat"] if operation == "multiplication"
                      else ["resultat", "par_groupe", "reste",
                            "a_un_reste", "amorce_narrative"]),
        difficulte=0.55 if operation == "multiplication" else (
            0.80 if metadonnees.get("reste", 0) > 0 else 0.60),
        metadonnees=metadonnees,
    )


def _mult_sans_retenue(a: int, b: int) -> int:
    """Simule l'erreur : multiplie chaque chiffre sans propager la retenue."""
    res, pos = 0, 1
    while a > 0:
        res += ((a % 10) * b) % 10 * pos
        a, pos = a // 10, pos * 10
    return res
