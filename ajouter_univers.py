#!/usr/bin/env python3
"""
Ajoute les univers narratifs « medecine », « science » et « echecs »
aux compétences du graphe PDA où le contexte est naturel.

Principe : un univers n'est ajouté que s'il porte un contexte mathématique
authentique pour cette compétence. La sélectivité est le but du champ.
"""

import json
from pathlib import Path

DOSSIER = Path(__file__).parent

# ── Mapping compétence -> univers à ajouter ────────────────────────────
AJOUTS = {
    # ARITHMÉTIQUE — sens et écriture des nombres
    "ARI-SEN-A01a": ["science", "echecs"],
    "ARI-SEN-A01b": ["science", "echecs", "medecine"],
    "ARI-SEN-A01c": ["echecs", "science", "medecine"],
    "ARI-SEN-A02c": ["science", "medecine", "echecs"],
    "ARI-SEN-A03":  ["science", "medecine"],
    "ARI-SEN-A04a": ["science", "medecine"],
    "ARI-SEN-A04b": ["science"],
    "ARI-SEN-A04c": ["science", "medecine"],
    "ARI-SEN-A05":  ["science", "echecs"],
    "ARI-SEN-A06":  ["science", "echecs"],
    "ARI-SEN-A07":  ["echecs", "science", "medecine"],
    "ARI-SEN-A08":  ["echecs", "science", "medecine"],
    "ARI-SEN-A10":  ["science", "medecine"],
    "ARI-SEN-A11a": ["echecs", "science"],
    "ARI-SEN-A13":  ["science", "medecine"],

    # ARITHMÉTIQUE — fractions
    "ARI-SEN-B01":  ["medecine", "science"],
    "ARI-SEN-B02":  ["medecine", "science"],
    "ARI-SEN-B03":  ["medecine", "science"],
    "ARI-SEN-B05":  ["medecine", "science"],
    "ARI-SEN-B06":  ["medecine", "science"],
    "ARI-SEN-B07":  ["medecine", "science"],
    "ARI-SEN-B10":  ["medecine", "science"],

    # ARITHMÉTIQUE — décimaux
    "ARI-SEN-C03":  ["science", "medecine"],
    "ARI-SEN-C04":  ["science", "medecine"],
    "ARI-SEN-C08":  ["science", "medecine"],

    # ARITHMÉTIQUE — sens des opérations
    "ARI-SOP-A01":  ["medecine", "science", "echecs"],
    "ARI-SOP-A02a": ["medecine", "science", "echecs"],
    "ARI-SOP-A03a": ["medecine", "science", "echecs"],
    "ARI-SOP-A04":  ["science", "echecs"],
    "ARI-SOP-A05a": ["science", "echecs"],
    "ARI-SOP-A05b": ["science", "echecs"],

    # ARITHMÉTIQUE — opérations
    "ARI-OPE-A01a": ["science", "medecine"],
    "ARI-OPE-A02a": ["medecine", "science", "echecs"],
    "ARI-OPE-A02b": ["science", "echecs"],
    "ARI-OPE-A02c": ["medecine", "science", "echecs"],
    "ARI-OPE-A03a": ["medecine", "science", "echecs"],
    "ARI-OPE-A03b": ["medecine", "science", "echecs"],
    "ARI-OPE-A04a": ["science", "medecine"],
    "ARI-OPE-A04b": ["science", "medecine"],
    "ARI-OPE-A04c": ["science", "medecine"],
    "ARI-OPE-A05":  ["science", "echecs", "medecine"],
    "ARI-OPE-A06a": ["echecs", "science", "medecine"],
    "ARI-OPE-A06b": ["echecs", "science"],
    "ARI-OPE-A06c": ["echecs", "science", "medecine"],
    "ARI-OPE-A07a": ["medecine", "science", "echecs"],
    "ARI-OPE-A08":  ["science", "echecs"],
    "ARI-OPE-A13a": ["echecs", "science"],
    "ARI-OPE-A13b": ["echecs", "science"],
    "ARI-OPE-A14":  ["echecs", "science"],
    "ARI-OPE-C02a": ["medecine", "science"],
    "ARI-OPE-C03a": ["medecine", "science"],

    # GÉOMÉTRIE
    "GEO-A01":   ["echecs", "science", "medecine"],
    "GEO-A02":   ["echecs", "science"],
    "GEO-B03":   ["science", "medecine"],
    "GEO-B05":   ["science"],
    "GEO-C02":   ["echecs", "science"],
    "GEO-C05":   ["echecs", "science"],
    "GEO-D01":   ["echecs", "science"],
    "GEO-D03a":  ["echecs", "science"],

    # MESURE
    "MES-A03":   ["science", "medecine"],
    "MES-A04a":  ["science", "medecine"],
    "MES-A05a":  ["science", "medecine"],
    "MES-A06":   ["science", "echecs"],
    "MES-B01b":  ["science", "echecs"],
    "MES-G01":   ["echecs", "medecine", "science"],
    "MES-G02":   ["echecs", "medecine", "science"],
    "MES-E03":   ["medecine", "science"],
    "MES-F03":   ["medecine", "science"],

    # STATISTIQUE
    "STA-02":    ["science", "medecine"],
    "STA-03a":   ["science", "medecine", "echecs"],
    "STA-04a":   ["science", "medecine"],
    "STA-03b":   ["science", "medecine"],

    # PROBABILITÉ
    "PRO-05a":   ["science", "medecine", "echecs"],
    "PRO-05b":   ["echecs", "science", "medecine"],
    "PRO-08a":   ["echecs", "science"],
}

# ── Notes pédagogiques spécifiques aux nouveaux univers ────────────────
NOTES_UNIVERS = {
    "ARI-OPE-A06a": "L'échiquier 8×8 est un support visuel idéal pour construire les faits de la table de 8.",
    "ARI-SEN-A11a": "Les cases claires et foncées de l'échiquier alternent — support concret de la parité.",
    "GEO-A02": "La notation algébrique des échecs (e4, d5) est un système de coordonnées authentique.",
    "GEO-C05": "Colonnes et rangées de l'échiquier : perpendicularité vécue, pas abstraite.",
    "MES-G01": "La pendule d'échecs rend la lecture du temps immédiatement conséquente.",
    "MES-E03": "Dosage en mL : contexte médical où la conversion a un enjeu réel et compréhensible.",
    "MES-F03": "Posologie selon la masse corporelle : la conversion g/kg devient une question de sécurité.",
    "ARI-SEN-A10": "Le thermomètre est la droite numérique la plus familière en contexte médical.",
    "STA-03b": "La courbe de température d'un patient est un diagramme à ligne brisée authentique.",
    "PRO-05b": "Aux échecs, évaluer quel coup est le plus probable est la compétence centrale du jeu.",
    "ARI-SEN-A07": "La valeur relative des pièces (pion 1, cavalier 3, tour 5, dame 9) donne un sens immédiat à la comparaison.",
}


def traiter(nom_fichier):
    chemin = DOSSIER / nom_fichier
    data = json.loads(chemin.read_text(encoding="utf-8"))

    modifiees = 0
    notes_ajoutees = 0

    for c in data["competences"]:
        cid = c["id"]
        if cid in AJOUTS:
            actuels = c.get("univers", [])
            nouveaux = [u for u in AJOUTS[cid] if u not in actuels]
            if nouveaux:
                c["univers"] = actuels + nouveaux
                modifiees += 1
        if cid in NOTES_UNIVERS:
            note_existante = c.get("note_pedagogique", "")
            nouvelle = NOTES_UNIVERS[cid]
            if nouvelle not in note_existante:
                c["note_pedagogique"] = (
                    f"{note_existante} {nouvelle}".strip()
                    if note_existante else nouvelle
                )
                notes_ajoutees += 1

    # Mise à jour du meta
    data["meta"]["univers_narratifs"] = [
        "nature", "espace", "cuisine", "sport",
        "construction", "medecine", "science", "echecs"
    ]
    data["meta"]["version"] = "0.2.0"

    chemin.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8"
    )
    print(f"{nom_fichier} : {modifiees} compétences enrichies, {notes_ajoutees} notes ajoutées")


if __name__ == "__main__":
    traiter("pda-arithmetique.json")
    traiter("pda-autres-champs.json")
    print("Terminé.")
