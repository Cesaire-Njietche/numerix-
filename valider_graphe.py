#!/usr/bin/env python3
"""
Validation du graphe de compétences PDA — Imhotep.

Vérifie :
  1. Unicité des identifiants
  2. Existence de tous les prérequis référencés
  3. Absence de cycle dans le graphe de dépendances
  4. Cohérence temporelle (un prérequis ne peut pas être introduit après)
  5. Présence des champs obligatoires

Usage : python valider_graphe.py
"""

import json
import sys
from pathlib import Path
from collections import defaultdict

DOSSIER = Path(__file__).parent
FICHIERS = ["pda-arithmetique.json", "pda-autres-champs.json"]

CHAMPS_OBLIGATOIRES = ["id", "libelle", "annee_intro", "annee_maitrise", "cycle", "prerequis"]


def charger():
    competences = {}
    for nom in FICHIERS:
        chemin = DOSSIER / nom
        if not chemin.exists():
            print(f"  fichier introuvable : {nom}")
            continue
        data = json.loads(chemin.read_text(encoding="utf-8"))
        for c in data["competences"]:
            if c["id"] in competences:
                print(f"  DOUBLON : {c['id']} présent dans plusieurs fichiers")
            competences[c["id"]] = {**c, "_fichier": nom}
    return competences


def valider_champs(competences):
    erreurs = []
    for cid, c in competences.items():
        for champ in CHAMPS_OBLIGATOIRES:
            if champ not in c:
                erreurs.append(f"{cid} : champ manquant « {champ} »")
        if c.get("generable") and not c.get("generateur"):
            erreurs.append(f"{cid} : marqué generable mais sans générateur")
    return erreurs


def valider_prerequis(competences):
    erreurs = []
    for cid, c in competences.items():
        for p in c.get("prerequis", []):
            if p not in competences:
                erreurs.append(f"{cid} : prérequis inconnu « {p} »")
    return erreurs


def detecter_cycles(competences):
    BLANC, GRIS, NOIR = 0, 1, 2
    couleur = {cid: BLANC for cid in competences}
    cycles = []

    def visiter(cid, chemin):
        couleur[cid] = GRIS
        for p in competences[cid].get("prerequis", []):
            if p not in competences:
                continue
            if couleur[p] == GRIS:
                idx = chemin.index(p) if p in chemin else 0
                cycles.append(" -> ".join(chemin[idx:] + [cid, p]))
            elif couleur[p] == BLANC:
                visiter(p, chemin + [cid])
        couleur[cid] = NOIR

    for cid in competences:
        if couleur[cid] == BLANC:
            visiter(cid, [])
    return cycles


def valider_coherence_temporelle(competences):
    avertissements = []
    for cid, c in competences.items():
        for p in c.get("prerequis", []):
            if p not in competences:
                continue
            prereq = competences[p]
            if prereq["annee_intro"] > c["annee_intro"]:
                avertissements.append(
                    f"{cid} (intro {c['annee_intro']}) dépend de {p} "
                    f"introduit plus tard (intro {prereq['annee_intro']})"
                )
    return avertissements


def statistiques(competences):
    par_cycle = defaultdict(int)
    par_annee = defaultdict(int)
    par_champ = defaultdict(int)
    par_univers = defaultdict(int)
    generables = 0
    erreurs_typiques = 0

    for c in competences.values():
        par_cycle[c["cycle"]] += 1
        par_annee[c["annee_intro"]] += 1
        champ = c.get("champ") or c["_fichier"].replace("pda-", "").replace(".json", "")
        if champ.startswith("arith"):
            champ = "arithmetique"
        par_champ[champ] += 1
        if c.get("generable"):
            generables += 1
        erreurs_typiques += len(c.get("erreurs_typiques", []))
        for u in c.get("univers", []):
            par_univers[u] += 1

    return {
        "total": len(competences),
        "generables": generables,
        "erreurs_typiques": erreurs_typiques,
        "par_cycle": dict(par_cycle),
        "par_annee_intro": dict(sorted(par_annee.items())),
        "par_champ": dict(par_champ),
        "par_univers": dict(sorted(par_univers.items(), key=lambda x: -x[1])),
    }


def racines(competences):
    return [cid for cid, c in competences.items() if not c.get("prerequis")]


def profondeur_max(competences):
    memo = {}

    def prof(cid):
        if cid in memo:
            return memo[cid]
        prereqs = [p for p in competences[cid].get("prerequis", []) if p in competences]
        memo[cid] = 0 if not prereqs else 1 + max(prof(p) for p in prereqs)
        return memo[cid]

    return max((prof(c) for c in competences), default=0), memo


def main():
    print("=" * 62)
    print("  VALIDATION DU GRAPHE PDA — IMHOTEP")
    print("=" * 62)

    competences = charger()
    if not competences:
        print("\nAucune compétence chargée.")
        sys.exit(1)

    print(f"\n{len(competences)} compétences chargées.\n")

    bloquant = False

    err_champs = valider_champs(competences)
    print(f"[1] Champs obligatoires ......... {'OK' if not err_champs else str(len(err_champs)) + ' erreur(s)'}")
    for e in err_champs:
        print(f"      {e}")
        bloquant = True

    err_prereq = valider_prerequis(competences)
    print(f"[2] Prérequis existants ......... {'OK' if not err_prereq else str(len(err_prereq)) + ' erreur(s)'}")
    for e in err_prereq:
        print(f"      {e}")
        bloquant = True

    cycles = detecter_cycles(competences)
    print(f"[3] Absence de cycle ............ {'OK' if not cycles else str(len(cycles)) + ' cycle(s)'}")
    for c in cycles:
        print(f"      {c}")
        bloquant = True

    avert = valider_coherence_temporelle(competences)
    print(f"[4] Cohérence temporelle ........ {'OK' if not avert else str(len(avert)) + ' avertissement(s)'}")
    for a in avert:
        print(f"      {a}")

    print("\n" + "-" * 62)
    print("  STATISTIQUES")
    print("-" * 62)

    s = statistiques(competences)
    print(f"\nTotal compétences ............... {s['total']}")
    print(f"Générables (moteur math) ........ {s['generables']}")
    print(f"Erreurs typiques cataloguées .... {s['erreurs_typiques']}")

    print("\nPar champ :")
    for k, v in s["par_champ"].items():
        print(f"   {k:.<28} {v}")

    print("\nPar cycle :")
    for k, v in sorted(s["par_cycle"].items()):
        print(f"   cycle {k} .................... {v}")

    print("\nPar année d'introduction :")
    for k, v in s["par_annee_intro"].items():
        print(f"   {k}re/e année ................ {v}")

    print("\nPar univers narratif :")
    for k, v in s["par_univers"].items():
        print(f"   {k:.<28} {v}")

    r = racines(competences)
    print(f"\nPoints d'entrée (sans prérequis) : {len(r)}")
    for cid in sorted(r):
        print(f"   {cid} — {competences[cid]['libelle'][:52]}")

    p_max, memo = profondeur_max(competences)
    print(f"\nProfondeur maximale du graphe ... {p_max}")
    plus_profonds = sorted(memo.items(), key=lambda x: -x[1])[:3]
    for cid, d in plus_profonds:
        print(f"   niveau {d} — {cid}")

    print("\n" + "=" * 62)
    if bloquant:
        print("  RÉSULTAT : erreurs bloquantes à corriger")
        sys.exit(1)
    print("  RÉSULTAT : graphe valide")
    print("=" * 62)


if __name__ == "__main__":
    main()
