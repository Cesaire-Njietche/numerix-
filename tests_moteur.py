#!/usr/bin/env python3
"""
Tests du moteur mathématique déterministe.

Ce fichier est la garantie que le LLM ne peut pas introduire d'erreur
mathématique : tout ce qui est calculé ici est vérifié ici.

Usage : python tests_moteur.py
"""

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from base import TypeResultat
from registre import (
    GraphePDA, REGISTRE,
    gen_faits_addition, gen_calcul_mental_add_soustr,
    gen_terme_manquant_add_soustr, gen_faits_multiplication,
    gen_sens_multiplication_division, gen_mult_div_personnelle,
)

CURRICULUM = Path(__file__).parent 
N = 400   # itérations par test

echecs = []


def verifier(condition, message):
    if not condition:
        echecs.append(message)
    return condition


def titre(t):
    print(f"\n{t}")
    print("-" * len(t))


# ══════════════════════════════════════════════════════════════════════
#  1. Justesse mathématique
# ══════════════════════════════════════════════════════════════════════

def test_justesse_faits_addition():
    rng = random.Random(1)
    for _ in range(N):
        p = gen_faits_addition(rng)
        e = p.enonce_math.replace("−", "-").replace(" = ?", "")
        attendu = eval(e)
        verifier(p.reponse == attendu,
                 f"faits_addition : {p.enonce_math} → {p.reponse}, attendu {attendu}")
    print(f"  gen_faits_addition ............... {N} problèmes vérifiés")


def test_justesse_calcul_mental():
    rng = random.Random(2)
    for cycle in (1, 2):
        for _ in range(N // 2):
            p = gen_calcul_mental_add_soustr(rng, cycle=cycle)
            e = p.enonce_math.replace("−", "-").replace(" = ?", "")
            attendu = eval(e)
            verifier(p.reponse == attendu,
                     f"calcul_mental : {p.enonce_math} → {p.reponse}, attendu {attendu}")
            verifier(p.reponse >= 0, f"calcul_mental : résultat négatif {p.enonce_math}")
    print(f"  gen_calcul_mental_add_soustr ..... {N} problèmes vérifiés")


def test_justesse_faits_multiplication():
    rng = random.Random(3)
    for _ in range(N):
        p = gen_faits_multiplication(rng)
        e = (p.enonce_math.replace("×", "*").replace("÷", "//")
             .replace(" = ?", ""))
        attendu = eval(e)
        verifier(p.reponse == attendu,
                 f"faits_mult : {p.enonce_math} → {p.reponse}, attendu {attendu}")
    print(f"  gen_faits_multiplication ......... {N} problèmes vérifiés")


def test_justesse_terme_manquant():
    rng = random.Random(4)
    for _ in range(N):
        p = gen_terme_manquant_add_soustr(rng, cycle=rng.choice([1, 2]))
        resolu = p.enonce_math.replace("?", str(p.reponse))
        g, d = resolu.replace("−", "-").split("=")
        verifier(eval(g.strip()) == eval(d.strip()),
                 f"terme_manquant : {p.enonce_math} avec ?={p.reponse} ne vérifie pas")
    print(f"  gen_terme_manquant_add_soustr .... {N} problèmes vérifiés")


def test_justesse_division_reste():
    rng = random.Random(5)
    avec_reste = 0
    for _ in range(N):
        p = gen_mult_div_personnelle(rng)
        if p.contexte_narratif["operation"] == "division":
            total = p.contexte_narratif["total"]
            div = p.contexte_narratif["nb_groupes"]
            q, r = p.reponse
            verifier(q * div + r == total,
                     f"division : {q}×{div}+{r} ≠ {total}")
            verifier(0 <= r < div, f"division : reste {r} invalide pour diviseur {div}")
            if r > 0:
                avec_reste += 1
        else:
            e = p.enonce_math.replace("×", "*").replace(" = ?", "")
            verifier(p.reponse == eval(e),
                     f"mult 3 chiffres : {p.enonce_math} → {p.reponse}")
    print(f"  gen_mult_div_personnelle ......... {N} problèmes vérifiés "
          f"({avec_reste} avec reste non nul)")


def test_coherence_sens_operations():
    rng = random.Random(6)
    for _ in range(N):
        p = gen_sens_multiplication_division(rng)
        c = p.contexte_narratif
        verifier(c["nb_groupes"] * c["par_groupe"] == c["total"],
                 f"sens : {c['nb_groupes']}×{c['par_groupe']} ≠ {c['total']}")
        verifier(p.metadonnees["sans_calcul"] is True,
                 "sens : devrait être marqué sans_calcul")
    print(f"  gen_sens_multiplication_division .. {N} problèmes vérifiés")


# ══════════════════════════════════════════════════════════════════════
#  2. Intégrité des choix
# ══════════════════════════════════════════════════════════════════════

def test_integrite_choix():
    rng = random.Random(7)
    generateurs = [
        (gen_faits_addition, {}),
        (gen_calcul_mental_add_soustr, {"cycle": 2}),
        (gen_terme_manquant_add_soustr, {"cycle": 1}),
        (gen_faits_multiplication, {}),
        (gen_sens_multiplication_division, {}),
        (gen_mult_div_personnelle, {}),
    ]
    for gen, kwargs in generateurs:
        for _ in range(N // 4):
            p = gen(rng, **kwargs)
            nom = gen.__name__

            verifier(len(p.choix) == 4,
                     f"{nom} : {len(p.choix)} choix au lieu de 4")
            verifier(p.reponse in p.choix,
                     f"{nom} : la réponse n'est pas dans les choix")

            cles = [tuple(c) if isinstance(c, (list, tuple)) else c for c in p.choix]
            verifier(len(set(cles)) == len(cles),
                     f"{nom} : doublon dans les choix {p.choix}")

            for d in p.distracteurs:
                verifier(d.valeur != p.reponse,
                         f"{nom} : distracteur égal à la réponse")
                verifier(d.code_erreur and d.description,
                         f"{nom} : distracteur sans code ou description")
    print(f"  Intégrité des choix .............. 6 générateurs × {N // 4} vérifiés")


# ══════════════════════════════════════════════════════════════════════
#  3. Branchement à trois issues
# ══════════════════════════════════════════════════════════════════════

def test_branchement_trois_issues():
    rng = random.Random(8)
    compteur = {t: 0 for t in TypeResultat}

    for _ in range(N):
        p = gen_faits_multiplication(rng)

        r = p.evaluer(p.reponse)
        verifier(r.type == TypeResultat.CORRECT, "bonne réponse non reconnue")
        compteur[r.type] += 1

        if p.distracteurs:
            d = p.distracteurs[0]
            r = p.evaluer(d.valeur)
            verifier(r.type == TypeResultat.ERREUR_TYPIQUE,
                     f"distracteur {d.valeur} non reconnu comme erreur typique")
            verifier(r.code_erreur == d.code_erreur, "code d'erreur incorrect")
            compteur[r.type] += 1

        aberrant = 99999
        r = p.evaluer(aberrant)
        verifier(r.type == TypeResultat.ERREUR_ALEATOIRE,
                 "réponse aberrante non classée comme erreur aléatoire")
        compteur[r.type] += 1

    print(f"  Branchement 3 issues ............. "
          f"correct={compteur[TypeResultat.CORRECT]} "
          f"typique={compteur[TypeResultat.ERREUR_TYPIQUE]} "
          f"aléatoire={compteur[TypeResultat.ERREUR_ALEATOIRE]}")


# ══════════════════════════════════════════════════════════════════════
#  4. Déterminisme
# ══════════════════════════════════════════════════════════════════════

def test_determinisme():
    for nom, gen in REGISTRE.items():
        a = gen(random.Random(42))
        b = gen(random.Random(42))
        verifier(a.enonce_math == b.enonce_math,
                 f"{nom} : énoncé non reproductible avec la même graine")
        verifier(a.reponse == b.reponse,
                 f"{nom} : réponse non reproductible")
        verifier(a.choix == b.choix,
                 f"{nom} : ordre des choix non reproductible")
    print(f"  Déterminisme ..................... {len(REGISTRE)} générateurs reproductibles")


# ══════════════════════════════════════════════════════════════════════
#  5. Étanchéité vis-à-vis du LLM
# ══════════════════════════════════════════════════════════════════════

def test_etancheite_llm():
    """Le LLM de MISE EN SCÈNE ne doit jamais pouvoir lire la réponse.

    Ce test ne se contente pas de vérifier l'absence de la clé « reponse » :
    il compare chaque valeur du contexte transmis à la réponse attendue.
    C'est la seule version du test qui a du sens — la première laissait
    passer « resultat: 48 » dans le contexte narratif.
    """
    rng = random.Random(9)
    total_fuites = 0

    for nom, gen in REGISTRE.items():
        for _ in range(120):
            p = gen(rng)
            charge = p.pour_le_llm_mise_en_scene()

            verifier("reponse" not in charge, f"{nom} : clé reponse présente")
            verifier("distracteurs" not in charge, f"{nom} : clé distracteurs présente")

            fuites = p.fuite_detectee()
            if fuites:
                total_fuites += 1
                verifier(False,
                         f"{nom} : la réponse {p.reponse!r} fuit via "
                         f"contexte_narratif{fuites}")

            verifier(p.cles_reponse, f"{nom} : cles_reponse non déclarées")

    print(f"  Mise en scène — étanchéité ....... {len(REGISTRE)} générateurs × 120 "
          f"— {total_fuites} fuite(s)")

    # Le dénouement, lui, DOIT contenir le résultat : c'est son rôle
    rng = random.Random(13)
    for nom, gen in REGISTRE.items():
        p = gen(rng)
        r = p.evaluer(p.reponse)
        d = p.pour_le_llm_denouement(r)
        verifier(d["issue"] == "correct", f"{nom} : issue du dénouement incorrecte")
        verifier("consigne" in d, f"{nom} : consigne narrative absente")
        verifier(d["contexte_narratif"] == p.contexte_narratif,
                 f"{nom} : dénouement privé du contexte complet")
    print(f"  Dénouement — contexte complet .... {len(REGISTRE)} générateurs OK")


# ══════════════════════════════════════════════════════════════════════
#  6. Progression de difficulté
# ══════════════════════════════════════════════════════════════════════

def test_difficulte_monotone():
    rng = random.Random(10)
    faciles, difficiles = [], []
    for _ in range(150):
        faciles.append(gen_faits_multiplication(rng, difficulte_cible=0.1).difficulte)
        difficiles.append(gen_faits_multiplication(rng, difficulte_cible=0.9).difficulte)
    mf, md = sum(faciles) / len(faciles), sum(difficiles) / len(difficiles)
    verifier(md > mf + 0.2,
             f"difficulté non discriminante : facile={mf:.2f} difficile={md:.2f}")
    print(f"  Ciblage de difficulté ............ facile={mf:.2f} · difficile={md:.2f}")

    rng = random.Random(11)
    fa = [gen_faits_addition(rng, difficulte_cible=0.1).difficulte for _ in range(150)]
    da = [gen_faits_addition(rng, difficulte_cible=0.9).difficulte for _ in range(150)]
    mfa, mda = sum(fa) / len(fa), sum(da) / len(da)
    verifier(mda > mfa + 0.2,
             f"addition : difficulté non discriminante {mfa:.2f} / {mda:.2f}")
    print(f"                                     addition facile={mfa:.2f} · difficile={mda:.2f}")


# ══════════════════════════════════════════════════════════════════════
#  7. Intégration avec le graphe PDA
# ══════════════════════════════════════════════════════════════════════

def test_integration_graphe():
    if not CURRICULUM.exists():
        print("  Intégration graphe ............... ignoré (curriculum/ absent)")
        return

    g = GraphePDA(CURRICULUM)
    impl = g.implementees()
    verifier(len(impl) > 0, "aucune compétence implémentée détectée")
    print(f"  Compétences couvertes ............ {len(impl)} / {len(g.competences)}")

    rng = random.Random(12)
    for cid in impl:
        for _ in range(20):
            p = g.generer(cid, rng=rng)
            verifier(p.competence_id == cid,
                     f"{cid} : identifiant non propagé")
            verifier(p.metadonnees.get("univers_compatibles"),
                     f"{cid} : univers non propagés depuis le graphe")
            verifier(p.reponse in p.choix,
                     f"{cid} : réponse absente des choix")
    print(f"  Génération via graphe ............ {len(impl)} compétences × 20 OK")

    for univers in ("nature", "espace", "cuisine", "sport",
                    "construction", "medecine", "science", "echecs"):
        dispo = g.par_univers(univers)
        verifier(len(dispo) > 0, f"univers {univers} : aucune compétence implémentée")
    print(f"  Couverture des 8 univers ......... OK")

    # Parcours progressif simulé
    maitrisees = set()
    etapes = 0
    while etapes < 30:
        dispo = g.disponibles(maitrisees)
        if not dispo:
            break
        maitrisees.add(dispo[0])
        etapes += 1
    verifier(etapes >= 5, f"parcours bloqué après {etapes} étapes")
    print(f"  Parcours progressif .............. {etapes} compétences débloquées en chaîne")


# ══════════════════════════════════════════════════════════════════════

def main():
    print("=" * 64)
    print("  TESTS DU MOTEUR MATHÉMATIQUE DÉTERMINISTE — IMHOTEP")
    print("=" * 64)

    titre("1. Justesse mathématique")
    test_justesse_faits_addition()
    test_justesse_calcul_mental()
    test_justesse_faits_multiplication()
    test_justesse_terme_manquant()
    test_justesse_division_reste()
    test_coherence_sens_operations()

    titre("2. Intégrité des choix")
    test_integrite_choix()

    titre("3. Branchement narratif")
    test_branchement_trois_issues()

    titre("4. Déterminisme")
    test_determinisme()

    titre("5. Étanchéité vis-à-vis du LLM")
    test_etancheite_llm()

    titre("6. Progression de difficulté")
    test_difficulte_monotone()

    titre("7. Intégration avec le graphe PDA")
    test_integration_graphe()

    print("\n" + "=" * 64)
    if echecs:
        print(f"  {len(echecs)} ÉCHEC(S)")
        for e in echecs[:20]:
            print(f"   - {e}")
        if len(echecs) > 20:
            print(f"   ... et {len(echecs) - 20} autres")
        print("=" * 64)
        sys.exit(1)
    print("  TOUS LES TESTS PASSENT")
    print("=" * 64)


if __name__ == "__main__":
    main()
