"""
Tests du suivi des connaissances et du planificateur.

Lancer : python tests_bkt.py   (doit être vert)
"""

from __future__ import annotations

import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from base import TypeResultat
from bkt import ProfilApprenant, SEUIL_MAITRISE, profil_pour
from planificateur import Planificateur
from registre import GraphePDA

T0 = datetime(2026, 1, 1, 9, 0, tzinfo=timezone.utc)
echecs: list[str] = []


def verifier(condition, message):
    if not condition:
        echecs.append(message)


def titre(t):
    print(f"\n{t}\n{'-' * len(t)}")


graphe = GraphePDA(Path(__file__).parent)
CID = "ARI-OPE-A07a"


def resultat(cid, issue, rng):
    p = graphe.generer(cid, rng=rng)
    if issue == "correct":
        return p.evaluer(p.reponse)
    if issue == "typique":
        return p.evaluer(p.distracteurs[0].valeur)
    return p.evaluer(99999)


def nouveau():
    return ProfilApprenant("test", graphe), random.Random(1)


def test_monotone_et_convergence():
    profil, rng = nouveau()
    cid = graphe.implementees()[0]
    prec = 0.0
    for i in range(12):
        p = profil.observer(cid, resultat(cid, "correct", rng),
                            maintenant=T0 + timedelta(minutes=i))
        verifier(p > prec, f"maîtrise non croissante au succès {i}")
        prec = p
    verifier(prec >= SEUIL_MAITRISE, f"pas de convergence : {prec:.2f}")
    print(f"  Succès enchaînés ................. maîtrise finale {prec:.2f}")


def test_erreurs_ordonnees():
    base, rng = nouveau()
    cid = graphe.implementees()[0]
    for i in range(3):
        base.observer(cid, resultat(cid, "correct", rng),
                      maintenant=T0 + timedelta(minutes=i))
    etat = base.to_dict()
    t = T0 + timedelta(minutes=5)
    apres = {}
    for issue in ("typique", "aleatoire", "correct"):
        pr = ProfilApprenant.from_dict(etat, graphe)
        apres[issue] = pr.observer(cid, resultat(cid, issue, rng), maintenant=t)
    verifier(apres["typique"] < apres["aleatoire"] < apres["correct"],
             f"ordre des issues faux : {apres}")
    print(f"  Typique < aléatoire < correct .... "
          f"{apres['typique']:.2f} < {apres['aleatoire']:.2f} < {apres['correct']:.2f}")


def test_oubli():
    profil, rng = nouveau()
    cid = graphe.implementees()[0]
    for i in range(8):
        profil.observer(cid, resultat(cid, "correct", rng),
                        maintenant=T0 + timedelta(minutes=i))
    t_fin = T0 + timedelta(minutes=8)
    avant = profil.maitrise(cid, t_fin)
    demi = profil.etats[cid].demi_vie_h
    apres = profil.maitrise(cid, t_fin + timedelta(hours=demi))
    verifier(abs(apres - avant / 2) < 1e-6, "la maîtrise ne baisse pas de moitié à la demi-vie")
    verifier(cid in profil.maitrisees(t_fin), "compétence non maîtrisée juste après")
    verifier(cid not in profil.maitrisees(t_fin + timedelta(hours=demi)), "oubli non pris en compte")
    verifier(cid in dict(profil.a_reviser(t_fin + timedelta(hours=demi))), "révision non planifiée")
    print(f"  Oubli ............................ {avant:.2f} → {apres:.2f} en {demi:.0f} h")


def test_espacement():
    cid = graphe.implementees()[0]
    rng = random.Random(2)

    masse, _ = nouveau()
    for i in range(12):
        masse.observer(cid, resultat(cid, "correct", rng),
                       maintenant=T0 + timedelta(seconds=10 * i))
    verifier(masse.etats[cid].nb_revues == 0, "pratique massée comptée comme révision")
    demi0 = masse.etats[cid].demi_vie_h

    espace, _ = nouveau()
    t = T0
    for _ in range(5):
        espace.observer(cid, resultat(cid, "correct", rng), maintenant=t)
        t += timedelta(hours=espace.etats[cid].demi_vie_h)
    e = espace.etats[cid]
    verifier(e.nb_revues == 4, f"révisions espacées attendues 4, obtenues {e.nb_revues}")
    verifier(e.demi_vie_h > 2.3 ** 3 * demi0 * 0.99, "demi-vie non allongée")
    verifier(e.demi_vie_h < 1000 * 24, "demi-vie aberrante")
    print(f"  Espacement ....................... massé {demi0:.0f} h · espacé "
          f"{e.demi_vie_h / 24:.1f} j ({e.nb_revues} révisions)")


def test_serialisation():
    profil, rng = nouveau()
    for cid in graphe.implementees()[:3]:
        profil.observer(cid, resultat(cid, "correct", rng), maintenant=T0)
    cid = graphe.implementees()[0]
    profil.observer(cid, resultat(cid, "typique", rng), maintenant=T0 + timedelta(hours=1))
    copie = ProfilApprenant.from_dict(profil.to_dict(), graphe)
    verifier(copie.to_dict() == profil.to_dict(), "aller-retour to_dict/from_dict différent")
    verifier(copie.misconceptions_actives() == profil.misconceptions_actives(),
             "misconceptions perdues")
    verifier(bool(profil.misconceptions_actives()), "erreur typique non enregistrée")
    print(f"  Sérialisation .................... aller-retour identique")


def test_profils():
    verifier(profil_pour(graphe, "ARI-OPE-A07a") in
             ("faits_numeriques", "conceptuel", "procedural"), "profil inconnu")
    noms = {profil_pour(graphe, c) for c in graphe.implementees()}
    verifier(len(noms) >= 2, "routage des profils trop pauvre")
    print(f"  Profils routés ................... {sorted(noms)}")


def test_planificateur():
    for univers in ("nature", "espace", "cuisine", "sport",
                    "construction", "medecine", "science", "echecs"):
        profil = ProfilApprenant("p", graphe)
        planif = Planificateur(graphe, profil, univers, 4, random.Random(3))
        t = T0
        motifs = set()
        for _ in range(60):
            probleme, sel = planif.prochain_probleme(t)
            motifs.add(sel.motif)
            verifier(probleme.metadonnees.get("motif") == sel.motif, "motif absent des métadonnées")
            verifier(probleme.fuite_detectee() == [], f"fuite via planificateur ({univers})")
            r = probleme.evaluer(probleme.reponse)
            profil.observer(sel.competence_id, r, maintenant=t)
            t += timedelta(minutes=2)
        verifier("nouvelle" in motifs, f"{univers} : aucune compétence nouvelle")

    # un grand saut de temps déclenche des révisions
    profil = ProfilApprenant("p", graphe)
    planif = Planificateur(graphe, profil, "echecs", 4, random.Random(4))
    t = T0
    for _ in range(40):
        probleme, sel = planif.prochain_probleme(t)
        profil.observer(sel.competence_id, probleme.evaluer(probleme.reponse), maintenant=t)
        t += timedelta(minutes=1)
    t += timedelta(days=10)
    _, sel = planif.prochain_probleme(t)
    verifier(sel.motif == "revision", f"révision attendue après 10 jours, obtenu {sel.motif}")
    cal = planif.calendrier_revision(30, t)
    verifier(bool(cal) and cal == sorted(cal, key=lambda x: x[1]), "calendrier vide ou désordonné")
    print(f"  Planificateur .................... 8 mondes × 60 questions · "
          f"révision après 10 j · {len(cal)} échéances")


def main():
    print("=" * 64)
    print("  TESTS DU SUIVI DES CONNAISSANCES ET DU PLANIFICATEUR")
    print("=" * 64)
    titre("1. Modèle de maîtrise")
    test_monotone_et_convergence()
    test_erreurs_ordonnees()
    test_oubli()
    test_espacement()
    test_profils()
    test_serialisation()
    titre("2. Planificateur")
    test_planificateur()

    print("\n" + "=" * 64)
    if echecs:
        print(f"  {len(echecs)} ÉCHEC(S)")
        for e in echecs[:20]:
            print(f"   - {e}")
        print("=" * 64)
        sys.exit(1)
    print("  TOUS LES TESTS PASSENT")
    print("=" * 64)


if __name__ == "__main__":
    main()
