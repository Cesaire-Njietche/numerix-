#!/usr/bin/env python3
"""
Démonstration du moteur mathématique déterministe.

Montre ce que le moteur produit et, surtout, ce que le moteur narratif
recevrait — pour vérifier de visu que le LLM n'a jamais accès à la réponse.

Usage : python demo_moteur.py
"""

import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from registre import GraphePDA, REGISTRE
from base import TypeResultat

CURRICULUM = Path(__file__).parent 


def ligne(c="─", n=66):
    print(c * n)


def montrer_probleme(p, rng):
    print(f"\n  {p.enonce_math}")
    print(f"  Compétence : {p.competence_id} — {p.metadonnees.get('libelle', '')[:44]}")
    print(f"  Difficulté : {p.difficulte:.2f}")
    print(f"  Choix      : {p.choix}")
    print(f"  Réponse    : {p.reponse}")

    if p.distracteurs:
        print("  Pièges :")
        for d in p.distracteurs:
            print(f"     {str(d.valeur):<22} [{d.code_erreur}] {d.description}")


def montrer_branchement(p):
    print("\n  Branchement à trois issues :")

    r = p.evaluer(p.reponse)
    print(f"     réponse {str(p.reponse):<18} → {r.type.value.upper()}")

    if p.distracteurs:
        d = p.distracteurs[0]
        r = p.evaluer(d.valeur)
        print(f"     réponse {str(d.valeur):<18} → {r.type.value.upper()}"
              f"  ({r.code_erreur})")
        print(f"         le moteur narratif sait pourquoi : {r.description_erreur}")

    r = p.evaluer(777777)
    print(f"     réponse {'777777':<18} → {r.type.value.upper()}")


def montrer_charge_llm(p):
    print("\n  PHASE 1 — MISE EN SCÈNE (avant la réponse de l'enfant)")
    print("  Le LLM écrit la situation. Il ne connaît PAS la réponse.\n")
    charge = p.pour_le_llm_mise_en_scene()
    charge["contexte_narratif"].pop("univers_compatibles", None)
    for l in json.dumps(charge, ensure_ascii=False, indent=2).split("\n"):
        print(f"     {l}")

    fuites = p.fuite_detectee()
    print(f"\n     Contrôle de fuite : {fuites if fuites else 'aucune'}")
    print(f"     Clés retirées     : {p.cles_reponse}")

    print("\n\n  PHASE 2 — DÉNOUEMENT (après la réponse)")
    print("  Le LLM raconte la conséquence. Le verdict est déjà rendu.\n")
    r = p.evaluer(p.distracteurs[0].valeur)
    d = p.pour_le_llm_denouement(r)
    d["contexte_narratif"] = {k: v for k, v in d["contexte_narratif"].items()
                              if k != "univers_compatibles"}
    for l in json.dumps(d, ensure_ascii=False, indent=2).split("\n"):
        print(f"     {l}")
    print("\n     → Le LLM n'a toujours rien calculé. Il habille un verdict.")


def main():
    rng = random.Random(2026)
    g = GraphePDA(CURRICULUM)

    print("=" * 66)
    print("  MOTEUR MATHÉMATIQUE DÉTERMINISTE — DÉMONSTRATION")
    print("=" * 66)
    print(f"\n  {len(REGISTRE)} générateurs · "
          f"{len(g.implementees())} compétences couvertes sur {len(g.competences)}")

    # ── Un exemple par générateur ────────────────────────────────────
    print("\n")
    ligne("═")
    print("  UN EXEMPLE PAR GÉNÉRATEUR")
    ligne("═")

    exemples = [
        ("ARI-OPE-A02a", "Faits d'addition (1re année)"),
        ("ARI-OPE-A03a", "Calcul mental additif"),
        ("ARI-OPE-A05",  "Terme manquant"),
        ("ARI-OPE-A06a", "Faits de multiplication (3e année)"),
        ("ARI-SOP-A03a", "Sens de la multiplication et de la division"),
        ("ARI-OPE-A07a", "Division avec reste (4e année)"),
    ]

    for cid, titre in exemples:
        print(f"\n{titre}")
        ligne()
        p = g.generer(cid, rng=rng)
        montrer_probleme(p, rng)

    # ── Branchement détaillé ─────────────────────────────────────────
    print("\n")
    ligne("═")
    print("  BRANCHEMENT NARRATIF — LE CŒUR DU PRODUIT")
    ligne("═")

    p = g.generer("ARI-OPE-A07a", rng=random.Random(7), operation="division",
                  avec_reste=True)
    montrer_probleme(p, rng)
    montrer_branchement(p)

    # ── Étanchéité ───────────────────────────────────────────────────
    print("\n")
    ligne("═")
    print("  ÉTANCHÉITÉ — CE QUE LE LLM VOIT")
    ligne("═")
    montrer_charge_llm(p)

    # ── Génération par univers ───────────────────────────────────────
    print("\n")
    ligne("═")
    print("  GÉNÉRATION PAR UNIVERS ET PAR ANNÉE")
    ligne("═")

    for univers in ["echecs", "medecine", "science", "cuisine", "nature"]:
        dispo = g.par_univers(univers)
        print(f"\n  {univers.upper():<14} {len(dispo)} compétences implémentées")
        rng_u = random.Random(sum(map(ord, univers)))
        try:
            p = g.generer_pour_univers(univers, annee=4, rng=rng_u)
            ctx = p.contexte_narratif
            print(f"     exemple : {p.enonce_math}")
            print(f"     sens    : {ctx.get('operation')} / {ctx.get('sens')}")
            print(f"     slots   : {', '.join(k for k in ctx if k not in ('univers_compatibles',))}")
        except ValueError as e:
            print(f"     {e}")

    # ── Parcours progressif ──────────────────────────────────────────
    print("\n")
    ligne("═")
    print("  PARCOURS PROGRESSIF SIMULÉ")
    ligne("═")
    print("\n  Un enfant qui maîtrise une compétence en débloque d'autres :\n")

    maitrisees: set[str] = set()
    for etape in range(1, 9):
        dispo = g.disponibles(maitrisees)
        if not dispo:
            break
        choisie = dispo[0]
        comp = g.get(choisie)
        print(f"   {etape}. {choisie:<16} {comp['libelle'][:44]}")
        maitrisees.add(choisie)

    print(f"\n  {len(maitrisees)} compétences enchaînées sans blocage.")

    print("\n" + "=" * 66)
    print("  Aucun LLM n'est intervenu dans ce qui précède.")
    print("=" * 66)


if __name__ == "__main__":
    main()
