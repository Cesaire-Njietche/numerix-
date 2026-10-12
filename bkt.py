"""
Suivi des connaissances (BKT) avec oubli.

Deux écarts volontaires par rapport au BKT classique :
  - trois issues : une erreur typique pèse plus lourd qu'une erreur aléatoire
    (l'enfant n'a pas deviné, il a appliqué une conception erronée) ;
  - oubli : la maîtrise décroît avec une demi-vie qui s'allonge à chaque
    révision *espacée*. Des succès enchaînés en quelques minutes ne comptent pas.

Aucun LLM ici. La maîtrise est une probabilité de 0 à 1.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any

from base import Resultat, TypeResultat

SEUIL_MAITRISE = 0.9
FACTEUR_DEMI_VIE = 2.3          # 1 j → 2,3 → 5,3 → 12,2 → 28
SEUIL_ESPACEMENT = 0.5          # un succès compte si écoulé >= 0,5 × demi-vie
LENTEUR = 2.0                   # réponse > 2 × temps cible : succès moins probant
POIDS_ERREUR_TYPIQUE = 3.0      # divise p(slip) : la mauvaise réponse était ciblée


@dataclass(frozen=True)
class ParamsBKT:
    p_init: float
    p_learn: float
    p_slip: float
    p_guess: float
    demi_vie_h: float


PROFILS: dict[str, ParamsBKT] = {
    "faits_numeriques": ParamsBKT(0.10, 0.25, 0.10, 0.20, 18.0),
    "conceptuel":       ParamsBKT(0.10, 0.12, 0.10, 0.20, 72.0),
    "procedural":       ParamsBKT(0.10, 0.20, 0.10, 0.20, 36.0),
}


def profil_pour(graphe, competence_id: str) -> str:
    """Route une compétence vers un profil d'après son générateur."""
    gen = graphe.get(competence_id).get("generateur") or ""
    if "faits" in gen:
        return "faits_numeriques"
    if "sens" in gen:
        return "conceptuel"
    return "procedural"


@dataclass
class EtatCompetence:
    p: float                    # maîtrise à l'instant `dernier`
    demi_vie_h: float
    dernier: str                # ISO 8601 UTC
    nb_revues: int = 0
    nb_obs: int = 0
    pic: float = 0.0            # plus haute maîtrise atteinte


def _maintenant() -> datetime:
    return datetime.now(timezone.utc)


def _heures(depuis: str, jusqua: datetime) -> float:
    return max(0.0, (jusqua - datetime.fromisoformat(depuis)).total_seconds() / 3600)


def _maitrise(e: EtatCompetence, t: datetime) -> float:
    return e.p * 0.5 ** (_heures(e.dernier, t) / e.demi_vie_h)


class ProfilApprenant:
    """Un profil par enfant. C'est lui qu'on persiste (to_dict / from_dict)."""

    def __init__(self, enfant_id: str, graphe):
        self.enfant_id = enfant_id
        self.graphe = graphe
        self.etats: dict[str, EtatCompetence] = {}
        self._miscs: dict[str, set[str]] = {}       # competence → codes d'erreur actifs

    # ── Observation ─────────────────────────────────────────────────

    def observer(
        self,
        competence_id: str,
        resultat: Resultat,
        temps_reponse_ms: float | None = None,
        temps_cible_ms: float | None = None,
        maintenant: datetime | None = None,
    ) -> float:
        """Enregistre une réponse. Retourne la nouvelle maîtrise."""
        t = maintenant or _maintenant()
        prm = PROFILS[profil_pour(self.graphe, competence_id)]
        e = self.etats.get(competence_id)
        if e is None:
            e = EtatCompetence(prm.p_init, prm.demi_vie_h, t.isoformat())
            ecoule = 0.0
        else:
            ecoule = _heures(e.dernier, t)
        p = _maitrise(e, t)

        lent = bool(temps_reponse_ms and temps_cible_ms
                    and temps_reponse_ms > LENTEUR * temps_cible_ms)

        if resultat.type == TypeResultat.CORRECT:
            guess = min(0.5, prm.p_guess * 2) if lent else prm.p_guess
            post = p * (1 - prm.p_slip) / (p * (1 - prm.p_slip) + (1 - p) * guess)
            # révision espacée : seul un vrai délai allonge la demi-vie
            if e.nb_obs and ecoule >= SEUIL_ESPACEMENT * e.demi_vie_h:
                e.demi_vie_h *= FACTEUR_DEMI_VIE
                e.nb_revues += 1
            self._miscs.get(competence_id, set()).clear()
        else:
            slip = prm.p_slip
            if resultat.type == TypeResultat.ERREUR_TYPIQUE:
                slip /= POIDS_ERREUR_TYPIQUE
                if resultat.code_erreur:
                    self._miscs.setdefault(competence_id, set()).add(resultat.code_erreur)
            post = p * slip / (p * slip + (1 - p) * (1 - prm.p_guess))

        e.p = post + (1 - post) * prm.p_learn
        e.dernier = t.isoformat()
        e.nb_obs += 1
        e.pic = max(e.pic, e.p)
        self.etats[competence_id] = e
        return e.p

    # ── Lectures ────────────────────────────────────────────────────

    def maitrise(self, competence_id: str, maintenant: datetime | None = None) -> float:
        e = self.etats.get(competence_id)
        return _maitrise(e, maintenant or _maintenant()) if e else 0.0

    def maitrisees(self, maintenant: datetime | None = None) -> set[str]:
        t = maintenant or _maintenant()
        return {c for c, e in self.etats.items() if _maitrise(e, t) >= SEUIL_MAITRISE}

    def a_reviser(self, maintenant: datetime | None = None) -> list[tuple[str, float]]:
        """Compétences déjà maîtrisées dont la maîtrise a retombé, les plus urgentes d'abord."""
        t = maintenant or _maintenant()
        dues = [(c, _maitrise(e, t)) for c, e in self.etats.items()
                if e.pic >= SEUIL_MAITRISE and _maitrise(e, t) < SEUIL_MAITRISE]
        return sorted(dues, key=lambda x: x[1])

    def misconceptions_actives(self) -> dict[str, list[str]]:
        """{code_erreur: [compétences]} — pour le tableau de bord parent."""
        out: dict[str, list[str]] = {}
        for comp, codes in self._miscs.items():
            for code in codes:
                out.setdefault(code, []).append(comp)
        return {k: sorted(v) for k, v in out.items()}

    def resume(self, maintenant: datetime | None = None) -> dict[str, Any]:
        return {
            "enfant_id": self.enfant_id,
            "nb_competences": len(self.etats),
            "nb_observations": sum(e.nb_obs for e in self.etats.values()),
            "maitrisees": sorted(self.maitrisees(maintenant)),
            "a_reviser": self.a_reviser(maintenant),
            "misconceptions": self.misconceptions_actives(),
        }

    # ── Persistance ─────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "enfant_id": self.enfant_id,
            "etats": {c: asdict(e) for c, e in self.etats.items()},
            "misconceptions": {c: sorted(v) for c, v in self._miscs.items() if v},
        }

    @classmethod
    def from_dict(cls, etat: dict, graphe) -> "ProfilApprenant":
        profil = cls(etat["enfant_id"], graphe)
        profil.etats = {c: EtatCompetence(**e) for c, e in etat.get("etats", {}).items()}
        profil._miscs = {c: set(v) for c, v in etat.get("misconceptions", {}).items()}
        return profil


__all__ = ["ProfilApprenant", "EtatCompetence", "ParamsBKT", "PROFILS",
           "SEUIL_MAITRISE", "profil_pour"]
