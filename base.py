"""
Types de base du moteur mathématique déterministe.

RÈGLE ARCHITECTURALE ABSOLUE
----------------------------
Ce module et tous les générateurs qui en dépendent sont 100 % déterministes.
Aucun LLM n'intervient ici. Le calcul, la génération de l'énoncé, la réponse
correcte et les distracteurs sont produits par du code testable.

Le moteur narratif (LLM) reçoit uniquement :
  - le `contexte_narratif` d'un Probleme (slots sémantiques, sans calcul à faire)
  - le `Resultat` d'une réponse (correct / erreur_typique / erreur_aleatoire)

Le LLM ne calcule jamais, ne vérifie jamais, ne génère jamais de nombre.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any


# ──────────────────────────────────────────────────────────────────────
#  Résultat d'une réponse — pilote le branchement narratif à 3 issues
# ──────────────────────────────────────────────────────────────────────

class TypeResultat(str, Enum):
    CORRECT = "correct"
    ERREUR_TYPIQUE = "erreur_typique"
    ERREUR_ALEATOIRE = "erreur_aleatoire"


@dataclass
class Resultat:
    """Ce que le moteur narratif reçoit après une réponse de l'enfant."""
    type: TypeResultat
    reponse_donnee: Any
    reponse_correcte: Any
    code_erreur: str | None = None
    description_erreur: str | None = None
    competence_id: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        d["type"] = self.type.value
        return d


# ──────────────────────────────────────────────────────────────────────
#  Distracteur — une mauvaise réponse construite depuis une erreur connue
# ──────────────────────────────────────────────────────────────────────

@dataclass
class Distracteur:
    valeur: Any
    code_erreur: str
    description: str


# ──────────────────────────────────────────────────────────────────────
#  Problème — l'unité produite par un générateur
# ──────────────────────────────────────────────────────────────────────

@dataclass
class Probleme:
    competence_id: str
    generateur: str

    enonce_math: str
    """L'expression mathématique pure, affichée à l'enfant. Ex : « 48 ÷ 8 = ? »"""

    reponse: Any
    distracteurs: list[Distracteur]
    choix: list[Any]

    contexte_narratif: dict[str, Any] = field(default_factory=dict)
    """Slots sémantiques passés au LLM. Ne contient JAMAIS de calcul à effectuer.

    Ex : {"operation": "division", "sens": "partage", "total": 48,
          "nb_groupes": 8, "par_groupe": 6, "role_resultat": "taille_du_groupe"}
    """

    cles_reponse: list[str] = field(default_factory=list)
    """Clés de `contexte_narratif` qui révèlent la réponse.

    Elles sont retirées avant l'envoi au LLM pour la MISE EN SCÈNE, et
    réintroduites seulement pour le DÉNOUEMENT, une fois l'enfant a répondu.
    Chaque générateur doit les déclarer.
    """

    difficulte: float = 0.5
    """0.0 = le plus facile de cette compétence, 1.0 = le plus difficile."""

    metadonnees: dict[str, Any] = field(default_factory=dict)

    # ── Évaluation ──────────────────────────────────────────────────

    def evaluer(self, reponse_donnee: Any) -> Resultat:
        """Vérifie une réponse. Point d'entrée unique — jamais de LLM ici."""
        if self._equivalent(reponse_donnee, self.reponse):
            return Resultat(
                type=TypeResultat.CORRECT,
                reponse_donnee=reponse_donnee,
                reponse_correcte=self.reponse,
                competence_id=self.competence_id,
            )

        for d in self.distracteurs:
            if self._equivalent(reponse_donnee, d.valeur):
                return Resultat(
                    type=TypeResultat.ERREUR_TYPIQUE,
                    reponse_donnee=reponse_donnee,
                    reponse_correcte=self.reponse,
                    code_erreur=d.code_erreur,
                    description_erreur=d.description,
                    competence_id=self.competence_id,
                )

        return Resultat(
            type=TypeResultat.ERREUR_ALEATOIRE,
            reponse_donnee=reponse_donnee,
            reponse_correcte=self.reponse,
            competence_id=self.competence_id,
        )

    @staticmethod
    def _equivalent(a: Any, b: Any) -> bool:
        # JSON clients send tuples (quotient, reste) as lists
        if isinstance(a, list):
            a = tuple(a)
        if isinstance(b, list):
            b = tuple(b)
        if isinstance(a, tuple) and isinstance(b, tuple):
            return a == b
        try:
            return abs(float(a) - float(b)) < 1e-9
        except (TypeError, ValueError):
            return str(a).strip().lower() == str(b).strip().lower()

    # ── Sérialisation ───────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "competence_id": self.competence_id,
            "generateur": self.generateur,
            "enonce_math": self.enonce_math,
            "reponse": self.reponse,
            "choix": self.choix,
            "distracteurs": [asdict(d) for d in self.distracteurs],
            "contexte_narratif": self.contexte_narratif,
            "difficulte": self.difficulte,
            "metadonnees": self.metadonnees,
        }

    # ── Deux charges distinctes pour le moteur narratif ─────────────

    def pour_le_llm_mise_en_scene(self) -> dict:
        """AVANT la réponse de l'enfant : de quoi écrire la situation.

        Toute clé listée dans `cles_reponse` est retirée. Le LLM ne peut
        donc pas révéler la réponse, même par accident, même si on le lui
        demandait : elle n'est pas dans son contexte.
        """
        contexte = {
            k: v for k, v in self.contexte_narratif.items()
            if k not in self.cles_reponse
        }
        return {
            "phase": "mise_en_scene",
            "enonce_math": self.enonce_math,
            "contexte_narratif": contexte,
            "choix_affiches": self.choix,
        }

    def pour_le_llm_denouement(self, resultat: "Resultat") -> dict:
        """APRÈS la réponse : de quoi écrire la conséquence narrative.

        Ici le LLM reçoit le résultat — mais uniquement pour le raconter.
        Il ne calcule toujours rien : le verdict est déjà rendu.
        """
        return {
            "phase": "denouement",
            "issue": resultat.type.value,
            "contexte_narratif": self.contexte_narratif,
            "code_erreur": resultat.code_erreur,
            "nature_de_l_erreur": resultat.description_erreur,
            "consigne": {
                "correct": "Le héros réussit. Ce que l'enfant a calculé rend l'action possible.",
                "erreur_typique": "Complication narrative ciblée sur cette erreur précise. "
                                  "Jamais un échec — un détour qui crée l'envie de réessayer.",
                "erreur_aleatoire": "Un imprévu relance la situation. Ni jugement, ni correction explicite.",
            }[resultat.type.value],
        }

    def fuite_detectee(self) -> list[str]:
        """Contrôle : la charge de mise en scène révèle-t-elle la réponse ?

        Une valeur déjà présente dans `enonce_math` n'est PAS une fuite :
        l'enfant la lit de toute façon. Dans « 4 + 0 = ? », le terme 4 égale
        la réponse par coïncidence arithmétique, pas par indiscrétion.

        Utilisé par les tests. Retourne les clés fautives — vide si étanche.
        """
        visibles = self._nombres_de_l_enonce()
        charge = self.pour_le_llm_mise_en_scene()
        fautives = []
        for cle, val in charge["contexte_narratif"].items():
            if not self._equivalent_pour_fuite(val, self.reponse):
                continue
            if isinstance(val, (int, float)) and float(val) in visibles:
                continue      # donnée de l'énoncé, pas une fuite
            fautives.append(cle)
        return fautives

    def _nombres_de_l_enonce(self) -> set[float]:
        import re
        return {float(n) for n in re.findall(r"-?\d+(?:[.,]\d+)?",
                                             self.enonce_math.replace(",", "."))}

    @staticmethod
    def _equivalent_pour_fuite(val: Any, reponse: Any) -> bool:
        if isinstance(reponse, tuple):
            return isinstance(val, (tuple, list)) and tuple(val) == reponse
        if isinstance(val, (dict, list, tuple)):
            return False
        try:
            return abs(float(val) - float(reponse)) < 1e-9
        except (TypeError, ValueError):
            return str(val).strip().lower() == str(reponse).strip().lower()


# ──────────────────────────────────────────────────────────────────────
#  Helpers partagés
# ──────────────────────────────────────────────────────────────────────

def assembler_choix(
    reponse: Any,
    distracteurs: list[Distracteur],
    rng: random.Random,
    nb_choix: int = 4,
    borne_min: int | None = 0,
) -> tuple[list[Any], list[Distracteur]]:
    """Construit la liste de choix présentée à l'enfant.

    Garantit : pas de doublon, pas de distracteur égal à la réponse,
    exactement `nb_choix` options, ordre mélangé.
    Complète avec des distracteurs de remplissage si nécessaire.
    """
    retenus: list[Distracteur] = []
    vues = {_cle(reponse)}

    for d in distracteurs:
        c = _cle(d.valeur)
        if c in vues:
            continue
        if borne_min is not None and isinstance(d.valeur, (int, float)) and d.valeur < borne_min:
            continue
        vues.add(c)
        retenus.append(d)
        if len(retenus) == nb_choix - 1:
            break

    # ── Remplissage : numérique ────────────────────────────────────
    if isinstance(reponse, (int, float)):
        ecart = 1
        while len(retenus) < nb_choix - 1 and ecart < 40:
            for signe in (1, -1):
                cand = reponse + signe * ecart
                if borne_min is not None and cand < borne_min:
                    continue
                if _cle(cand) in vues:
                    continue
                vues.add(_cle(cand))
                retenus.append(Distracteur(
                    valeur=cand,
                    code_erreur="ecart_proche",
                    description=f"Écart de {ecart} par rapport au résultat",
                ))
                if len(retenus) == nb_choix - 1:
                    break
            ecart += 1

    # ── Remplissage : couple (quotient, reste) ─────────────────────
    elif isinstance(reponse, tuple) and len(reponse) == 2 \
            and all(isinstance(x, int) for x in reponse):
        q, r = reponse
        candidats = [
            ((q + 1, r), "ecart_quotient", "Quotient décalé de 1"),
            ((q - 1, r), "ecart_quotient", "Quotient décalé de 1"),
            ((q, r + 1), "ecart_reste", "Reste décalé de 1"),
            ((q, max(r - 1, 0)), "ecart_reste", "Reste décalé de 1"),
            ((q + 1, max(r - 1, 0)), "ecart_mixte", "Quotient et reste tous deux décalés"),
        ]
        for val, code, desc in candidats:
            if len(retenus) == nb_choix - 1:
                break
            if val[0] < 0 or val[1] < 0 or _cle(val) in vues:
                continue
            vues.add(_cle(val))
            retenus.append(Distracteur(val, code, desc))

    if len(retenus) < nb_choix - 1:
        raise ValueError(
            f"Impossible d'assembler {nb_choix} choix distincts pour la réponse "
            f"{reponse!r} : seulement {len(retenus)} distracteur(s) valide(s). "
            f"Le générateur doit fournir plus de distracteurs non dégénérés."
        )

    choix = [reponse] + [d.valeur for d in retenus]
    rng.shuffle(choix)
    return choix, retenus


def _cle(v: Any) -> Any:
    if isinstance(v, float) and v.is_integer():
        return int(v)
    if isinstance(v, (list, tuple)):
        return tuple(v)
    return v


def borne_par_cycle(cycle: int, max_c1: int, max_c2: int) -> int:
    """Les balises de la PDA : < 1000 au cycle 1, < 100 000 au cycle 2."""
    return max_c1 if cycle <= 1 else max_c2


def echelle(valeur: float, bas: float, haut: float) -> float:
    """Normalise une valeur dans [0, 1] pour le champ difficulte."""
    if haut <= bas:
        return 0.5
    return max(0.0, min(1.0, (valeur - bas) / (haut - bas)))
