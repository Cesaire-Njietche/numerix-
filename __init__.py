"""
Moteur mathématique déterministe — Imhotep.

Couche 2 de l'architecture. Aucun LLM n'intervient ici.
"""

from .base import Probleme, Distracteur, Resultat, TypeResultat
from .registre import REGISTRE, GraphePDA
from .gen_addition import (
    gen_faits_addition,
    gen_calcul_mental_add_soustr,
    gen_terme_manquant_add_soustr,
)
from .gen_multiplication import (
    gen_faits_multiplication,
    gen_sens_multiplication_division,
    gen_mult_div_personnelle,
)

__version__ = "0.1.0"

__all__ = [
    "Probleme", "Distracteur", "Resultat", "TypeResultat",
    "REGISTRE", "GraphePDA",
    "gen_faits_addition",
    "gen_calcul_mental_add_soustr",
    "gen_terme_manquant_add_soustr",
    "gen_faits_multiplication",
    "gen_sens_multiplication_division",
    "gen_mult_div_personnelle",
]
