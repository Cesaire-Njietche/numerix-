"""
Registre des générateurs.

Point d'entrée unique de la couche mathématique. L'orchestrateur ne connaît
que ce module : il demande un problème pour une compétence, il reçoit un
Probleme. Il ne sait pas quel générateur a été appelé.
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Callable

from base import Probleme
from gen_addition import (
    gen_faits_addition,
    gen_calcul_mental_add_soustr,
    gen_terme_manquant_add_soustr,
)
from gen_multiplication import (
    gen_faits_multiplication,
    gen_sens_multiplication_division,
    gen_mult_div_personnelle,
)


REGISTRE: dict[str, Callable[..., Probleme]] = {
    "gen_faits_addition": gen_faits_addition,
    "gen_calcul_mental_add_soustr": gen_calcul_mental_add_soustr,
    "gen_terme_manquant_add_soustr": gen_terme_manquant_add_soustr,
    "gen_faits_multiplication": gen_faits_multiplication,
    "gen_sens_multiplication_division": gen_sens_multiplication_division,
    "gen_mult_div_personnelle": gen_mult_div_personnelle,
}


class GraphePDA:
    """Charge le graphe de compétences et route vers le bon générateur."""

    def __init__(self, dossier_curriculum: str | Path):
        self.dossier = Path(dossier_curriculum)
        self.competences: dict[str, dict] = {}
        self._charger()

    def _charger(self):
        for nom in ("pda-arithmetique.json", "pda-autres-champs.json"):
            chemin = self.dossier / nom
            if not chemin.exists():
                continue
            data = json.loads(chemin.read_text(encoding="utf-8"))
            for c in data["competences"]:
                self.competences[c["id"]] = c

    # ── Interrogation ───────────────────────────────────────────────

    def get(self, competence_id: str) -> dict:
        if competence_id not in self.competences:
            raise KeyError(f"Compétence inconnue : {competence_id}")
        return self.competences[competence_id]

    def implementees(self) -> list[str]:
        """Compétences dont le générateur existe déjà."""
        return sorted(
            cid for cid, c in self.competences.items()
            if c.get("generateur") in REGISTRE
        )

    def par_univers(self, univers: str) -> list[str]:
        return sorted(
            cid for cid, c in self.competences.items()
            if univers in c.get("univers", []) and c.get("generateur") in REGISTRE
        )

    def par_annee(self, annee: int) -> list[str]:
        return sorted(
            cid for cid, c in self.competences.items()
            if c.get("annee_intro", 99) <= annee <= c.get("annee_maitrise", 0)
            and c.get("generateur") in REGISTRE
        )

    def prerequis_satisfaits(
        self,
        competence_id: str,
        maitrisees: set[str],
        ignorer_non_implementes: bool = True,
    ) -> bool:
        """Vérifie que les prérequis sont maîtrisés.

        `ignorer_non_implementes` : tant que les 75 générateurs ne sont pas
        tous écrits, un prérequis sans générateur ne peut pas être « maîtrisé »
        par l'enfant et bloquerait tout le parcours. On le neutralise donc.
        À repasser à False une fois la couverture complète.
        """
        implementees = set(self.implementees())
        for p in self.get(competence_id).get("prerequis", []):
            if p in maitrisees:
                continue
            if ignorer_non_implementes and p not in implementees:
                continue
            return False
        return True

    def disponibles(
        self,
        maitrisees: set[str],
        ignorer_non_implementes: bool = True,
    ) -> list[str]:
        """Compétences débloquées : prérequis satisfaits, pas encore maîtrisées."""
        return sorted(
            cid for cid in self.implementees()
            if cid not in maitrisees
            and self.prerequis_satisfaits(cid, maitrisees, ignorer_non_implementes)
        )

    # ── Génération ──────────────────────────────────────────────────

    def generer(
        self,
        competence_id: str,
        rng: random.Random | None = None,
        seed: int | None = None,
        **surcharges,
    ) -> Probleme:
        """Produit un problème pour une compétence donnée.

        Les paramètres du graphe PDA sont appliqués d'abord, puis les
        surcharges de l'appelant (utile pour viser une difficulté précise).
        """
        comp = self.get(competence_id)
        nom_gen = comp.get("generateur")

        if nom_gen not in REGISTRE:
            raise NotImplementedError(
                f"Générateur « {nom_gen} » non implémenté "
                f"(compétence {competence_id}). "
                f"{len(REGISTRE)} générateurs disponibles."
            )

        if rng is None:
            rng = random.Random(seed)

        params = dict(comp.get("parametres") or {})
        params["cycle"] = comp.get("cycle", 1)
        params.update(surcharges)

        probleme = REGISTRE[nom_gen](rng, **params)

        # Le graphe est la source de vérité pour l'identité et les univers
        probleme.competence_id = competence_id
        probleme.metadonnees.setdefault("univers_compatibles", comp.get("univers", []))
        probleme.metadonnees.setdefault("libelle", comp.get("libelle"))
        probleme.metadonnees.setdefault("ref_pda", comp.get("ref_pda"))
        probleme.contexte_narratif.setdefault(
            "univers_compatibles", comp.get("univers", [])
        )
        return probleme

    def generer_pour_univers(
        self,
        univers: str,
        annee: int,
        rng: random.Random | None = None,
        seed: int | None = None,
        maitrisees: set[str] | None = None,
        **surcharges,
    ) -> Probleme:
        """Tire une compétence adaptée à l'univers et à l'année, puis génère."""
        rng = rng or random.Random(seed)
        maitrisees = maitrisees or set()

        candidats = [
            cid for cid in self.par_univers(univers)
            if self.competences[cid].get("annee_intro", 99) <= annee
            and self.prerequis_satisfaits(cid, maitrisees)
        ]
        if not candidats:
            raise ValueError(
                f"Aucune compétence implémentée pour univers={univers}, année={annee}"
            )
        return self.generer(rng.choice(candidats), rng=rng, **surcharges)


__all__ = ["REGISTRE", "GraphePDA", "Probleme"]
