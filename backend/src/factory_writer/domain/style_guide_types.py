import enum


class StatutSource(enum.StrEnum):
    EN_ATTENTE = "EN_ATTENTE"
    EN_COURS = "EN_COURS"
    TERMINE = "TERMINE"
    ERREUR = "ERREUR"


class StatutPack(enum.StrEnum):
    BROUILLON = "BROUILLON"
    APPROUVE = "APPROUVE"
    ACTIF = "ACTIF"


class TypeRegle(enum.StrEnum):
    VOIX = "VOIX"
    TON = "TON"
    FORMATAGE = "FORMATAGE"
    PROMESSE_INTERDITE = "PROMESSE_INTERDITE"


class NiveauContrainte(enum.StrEnum):
    HARD = "HARD"
    SOFT = "SOFT"
