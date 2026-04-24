import pytest

from factory_writer.application.prompts.style_guide_extract_rules.v1.output_schema import (
    DraftStylePackExtractionV1,
    DraftStyleRuleV1,
)
from factory_writer.application.services.style_guide_ingestion_service import (
    _validate_draft_pack_candidate,
)
from factory_writer.domain.style_guide_types import NiveauContrainte, TypeRegle


def test_validate_draft_pack_candidate_normalizes_business_rules() -> None:
    candidate = DraftStylePackExtractionV1(
        regles=[
            DraftStyleRuleV1(
                source_evidence_provider_id="chunk-1",
                citation_source="voix doit rester elegante",
                type_regle=TypeRegle.VOIX,
                niveau_contrainte=NiveauContrainte.HARD,
                texte_regle="  La voix doit rester elegante.  ",
                famille_code="mobilier_jardin",
            ),
            DraftStyleRuleV1(
                source_evidence_provider_id="chunk-1",
                citation_source="sans entretien pour toujours",
                type_regle=TypeRegle.PROMESSE_INTERDITE,
                niveau_contrainte=NiveauContrainte.SOFT,
                texte_regle="sans entretien pour toujours",
                famille_code=None,
            ),
        ],
    )

    validated = _validate_draft_pack_candidate(
        candidate=candidate,
        chunk_contents={
            "chunk-1": "La voix doit rester elegante. Formulation interdite: sans entretien pour toujours."
        },
        famille_codes={"mobilier_jardin"},
    )

    assert validated.regles[0].texte_regle == "La voix doit rester elegante."
    assert validated.regles[0].famille_code is None
    assert validated.regles[1].niveau_contrainte == NiveauContrainte.HARD


def test_validate_draft_pack_candidate_rejects_unknown_fragment() -> None:
    candidate = _candidate(
        DraftStyleRuleV1(
            source_evidence_provider_id="unknown-chunk",
            citation_source="La voix doit rester elegante",
            type_regle=TypeRegle.VOIX,
            niveau_contrainte=NiveauContrainte.HARD,
            texte_regle="La voix doit rester elegante.",
            famille_code=None,
        )
    )

    with pytest.raises(ValueError, match="source_evidence_provider_id inconnu"):
        _validate_draft_pack_candidate(
            candidate=candidate,
            chunk_contents={"chunk-1": "La voix doit rester elegante."},
            famille_codes={"mobilier_jardin"},
        )


def test_validate_draft_pack_candidate_rejects_unknown_family() -> None:
    candidate = _candidate(
        DraftStyleRuleV1(
            source_evidence_provider_id="chunk-1",
            citation_source="vocabulaire de matiere",
            type_regle=TypeRegle.TON,
            niveau_contrainte=NiveauContrainte.SOFT,
            texte_regle="Privilegier un vocabulaire de matiere.",
            famille_code="famille_inventee",
        )
    )

    with pytest.raises(ValueError, match="famille_code inconnu"):
        _validate_draft_pack_candidate(
            candidate=candidate,
            chunk_contents={"chunk-1": "Privilegier un vocabulaire de matiere."},
            famille_codes={"mobilier_jardin"},
        )


def test_validate_draft_pack_candidate_rejects_unsupported_citation() -> None:
    candidate = _candidate(
        DraftStyleRuleV1(
            source_evidence_provider_id="chunk-1",
            citation_source="claim invente par le modele",
            type_regle=TypeRegle.VOIX,
            niveau_contrainte=NiveauContrainte.HARD,
            texte_regle="La voix doit rester elegant et premium.",
            famille_code=None,
        )
    )

    with pytest.raises(ValueError, match="citation_source introuvable"):
        _validate_draft_pack_candidate(
            candidate=candidate,
            chunk_contents={"chunk-1": "Le texte doit rester elegant et premium."},
            famille_codes={"mobilier_jardin"},
        )


def test_validate_draft_pack_candidate_requires_family_for_tone() -> None:
    candidate = _candidate(
        DraftStyleRuleV1(
            source_evidence_provider_id="chunk-1",
            citation_source="vocabulaire de matiere",
            type_regle=TypeRegle.TON,
            niveau_contrainte=NiveauContrainte.SOFT,
            texte_regle="Privilegier un vocabulaire de matiere.",
            famille_code=None,
        )
    )

    with pytest.raises(ValueError, match="regle TON doit cibler une famille"):
        _validate_draft_pack_candidate(
            candidate=candidate,
            chunk_contents={"chunk-1": "Privilegier un vocabulaire de matiere."},
            famille_codes={"mobilier_jardin"},
        )


def test_validate_draft_pack_candidate_rejects_duplicate_rule_with_conflicting_constraint() -> None:
    candidate = DraftStylePackExtractionV1(
        regles=[
            DraftStyleRuleV1(
                source_evidence_provider_id="chunk-1",
                citation_source="Limiter le texte a trois phrases",
                type_regle=TypeRegle.FORMATAGE,
                niveau_contrainte=NiveauContrainte.HARD,
                texte_regle="Limiter le texte a trois phrases.",
                famille_code=None,
            ),
            DraftStyleRuleV1(
                source_evidence_provider_id="chunk-1",
                citation_source="Limiter le texte a trois phrases",
                type_regle=TypeRegle.FORMATAGE,
                niveau_contrainte=NiveauContrainte.SOFT,
                texte_regle="  Limiter   le texte a trois phrases. ",
                famille_code=None,
            ),
        ],
    )

    with pytest.raises(ValueError, match="dupliquee avec niveaux de contrainte"):
        _validate_draft_pack_candidate(
            candidate=candidate,
            chunk_contents={"chunk-1": "Limiter le texte a trois phrases."},
            famille_codes={"mobilier_jardin"},
        )


def _candidate(rule: DraftStyleRuleV1) -> DraftStylePackExtractionV1:
    return DraftStylePackExtractionV1(
        regles=[rule],
    )
