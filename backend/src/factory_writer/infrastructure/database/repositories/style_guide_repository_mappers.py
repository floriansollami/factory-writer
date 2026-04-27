from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import PurePosixPath
from typing import Any, cast

from factory_writer.application.ports.style_guide_ingestion import StyleGuideChunkCandidate
from factory_writer.domain.style_guide_types import NiveauContrainte, TypeRegle
from factory_writer.infrastructure.database.models.poc_ingestion import StylePack, StyleRule


def upsert_layout_parse_step(
    *,
    steps: Any | None,
    parser_resource_id: str,
    mode: str,
    latency_ms: int | None,
    operation_id: str | None,
    output_uri: str | None,
) -> list[dict[str, Any]]:
    normalized_steps = [dict(step) for step in steps] if isinstance(steps, list) else []

    existing_step = next(
        (step for step in normalized_steps if step.get("step_kind") == "LAYOUT_PARSE"),
        None,
    )

    step_payload: dict[str, Any] = {
        "step_kind": "LAYOUT_PARSE",
        "provider": "google_document_ai",
        "processor_kind": "layout_parser",
        "mode": mode,
        "processor_resource_name": parser_resource_id,
        "status": "SUCCEEDED" if mode == "online" or existing_step is not None else "RUNNING",
    }

    if latency_ms is not None:
        step_payload["latency_ms"] = latency_ms
    if operation_id is not None:
        step_payload["provider_job_id"] = operation_id
    if output_uri is not None:
        step_payload["output_uri"] = output_uri

    processor_version = PurePosixPath(parser_resource_id).name
    if processor_version:
        step_payload["processor_version"] = processor_version

    if existing_step is None:
        normalized_steps.append(step_payload)
        return normalized_steps

    existing_step.update(step_payload)
    return normalized_steps


def upsert_llm_draft_pack_step(
    *,
    steps: Any | None,
    prompt_registry_provider: str,
    prompt_name: str,
    prompt_version: str,
    llm_model: str,
    llm_temperature: float,
    llm_max_tokens: int,
    llm_response_format: str,
    status: str,
    system_prompt_hash: str | None,
    user_prompt_hash: str | None,
) -> list[dict[str, Any]]:
    normalized_steps = [dict(step) for step in steps] if isinstance(steps, list) else []

    existing_step = next(
        (step for step in normalized_steps if step.get("step_kind") == "LLM_DRAFT_PACK"),
        None,
    )

    step_payload: dict[str, Any] = {
        "step_kind": "LLM_DRAFT_PACK",
        "provider": "litellm",
        "status": status,
        "prompt_registry_provider": prompt_registry_provider,
        "prompt_name": prompt_name,
        "prompt_version": prompt_version,
        "llm_model": llm_model,
        "llm_temperature": llm_temperature,
        "llm_max_tokens": llm_max_tokens,
        "llm_response_format": llm_response_format,
    }

    if system_prompt_hash is not None:
        step_payload["system_prompt_hash"] = system_prompt_hash
    if user_prompt_hash is not None:
        step_payload["user_prompt_hash"] = user_prompt_hash

    if existing_step is None:
        normalized_steps.append(step_payload)
        return normalized_steps

    existing_step.update(step_payload)
    return normalized_steps


def build_rule_evidence_json(chunk: StyleGuideChunkCandidate) -> dict[str, Any]:
    evidence_json = dict(chunk.evidence_json)
    evidence_json["index_chunk"] = chunk.index_chunk
    evidence_json["provider_id"] = chunk.provider_id
    return evidence_json


def find_pack_rule(pack: StylePack, rule_id: uuid.UUID) -> StyleRule:
    rule = next((candidate for candidate in pack.style_rules if candidate.id == rule_id), None)
    if rule is None:
        raise KeyError(str(rule_id))
    return cast(StyleRule, rule)


def ordered_pack_rules(rules: list[StyleRule]) -> list[StyleRule]:
    return sorted(
        rules,
        key=lambda rule: (
            rule.created_at or datetime.min.replace(tzinfo=UTC),
            str(rule.id),
        ),
    )


def normalize_rule_text(value: str) -> str:
    normalized = value.strip()
    if len(normalized) < 8:
        raise ValueError("La règle doit être explicite.")
    return normalized


def normalize_taxonomie_code(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def current_taxonomie_code(rule: StyleRule) -> str | None:
    if rule.taxonomie_produit is None:
        return None
    return str(rule.taxonomie_produit.famille_code)


def validate_rule_invariants(
    *,
    type_regle: TypeRegle,
    niveau_contrainte: NiveauContrainte,
    taxonomie_code: str | None,
) -> None:
    if type_regle == TypeRegle.TON and taxonomie_code is None:
        raise ValueError("Une règle de ton doit cibler une famille produit.")
    if type_regle != TypeRegle.TON and taxonomie_code is not None:
        raise ValueError("Seules les règles de ton peuvent cibler une famille produit.")
    if type_regle == TypeRegle.PROMESSE_INTERDITE and niveau_contrainte != NiveauContrainte.HARD:
        raise ValueError("Une promesse interdite doit toujours être en niveau HARD.")
