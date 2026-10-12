"""
Planificateur : quelle question vient ensuite.

Ordre de priorité : révision (maîtrise retombée) → consolidation (compétence
en cours) → nouvelle (prérequis satisfaits) → entretien (tout est maîtrisé).
Pur et déterministe pour un `rng` donné. Aucun LLM.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from base import Probleme
from bkt import ProfilApprenant, SEUIL_MAITRISE, _maitrise


@dataclass
class Selection:
    competence_id: str
    motif: str          # revision | consolidation | nouvelle | entretien


class Planificateur:
    def __init__(self, graphe, profil: ProfilApprenant, univers: str, annee: int,
                 rng: random.Random | None = None):
        self.graphe = graphe
        self.profil = profil
        self.univers = univers
        self.annee = annee
        self.rng = rng or random.Random()

    def choisir(self, maintenant: datetime | None = None) -> Selection:
        t = maintenant or datetime.now(timezone.utc)
        impl = set(self.graphe.implementees())
        du_monde = [c for c in self.graphe.par_univers(self.univers)
                    if self.graphe.get(c).get("annee_intro", 99) <= self.annee]

        # la révision ignore le monde : même compétence, nouvelle histoire
        dues = [c for c, _ in self.profil.a_reviser(t) if c in impl]
        if dues:
            return Selection(dues[0], "revision")

        maitrisees = self.profil.maitrisees(t)
        en_cours = [c for c in du_monde
                    if c in self.profil.etats and c not in maitrisees]
        if en_cours:
            return Selection(
                min(en_cours, key=lambda c: self.profil.maitrise(c, t)), "consolidation")

        nouvelles = [c for c in du_monde
                     if c not in self.profil.etats
                     and self.graphe.prerequis_satisfaits(c, maitrisees)]
        if nouvelles:
            premiere = min(self.graphe.get(c).get("annee_intro", 99) for c in nouvelles)
            return Selection(self.rng.choice(
                [c for c in nouvelles
                 if self.graphe.get(c).get("annee_intro", 99) == premiere]), "nouvelle")

        entretien = sorted(maitrisees & impl) or du_monde
        if not entretien:
            raise ValueError(
                f"Aucune compétence implémentée pour univers={self.univers}, "
                f"année={self.annee}")
        return Selection(self.rng.choice(entretien), "entretien")

    def prochain_probleme(self, maintenant: datetime | None = None
                          ) -> tuple[Probleme, Selection]:
        sel = self.choisir(maintenant)
        probleme = self.graphe.generer(sel.competence_id, rng=self.rng)
        probleme.metadonnees["motif"] = sel.motif
        return probleme, sel

    def calendrier_revision(self, jours: int = 30, maintenant: datetime | None = None
                            ) -> list[tuple[str, datetime]]:
        """Compétences maîtrisées avec la date où leur maîtrise passera sous le seuil."""
        t = maintenant or datetime.now(timezone.utc)
        horizon = t + timedelta(days=jours)
        out = []
        for c, e in self.profil.etats.items():
            if e.pic < SEUIL_MAITRISE:
                continue
            p = _maitrise(e, t)
            heures = 0.0 if p <= SEUIL_MAITRISE else e.demi_vie_h * math.log2(p / SEUIL_MAITRISE)
            echeance = t + timedelta(hours=heures)
            if echeance <= horizon:
                out.append((c, echeance))
        return sorted(out, key=lambda x: x[1])


__all__ = ["Planificateur", "Selection"]
