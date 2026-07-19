#!/usr/bin/env python3
"""Lightweight agent-style reaction parser for ChemKit.

This intentionally stays small: common names and clear transformations
are handled locally; ambiguous chemistry is returned as questions for
the user instead of being guessed.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


ALIASES: dict[str, dict[str, str]] = {
    "乙酸": {"name": "acetic acid", "smiles": "CC(=O)O", "source": "common reagent table"},
    "醋酸": {"name": "acetic acid", "smiles": "CC(=O)O", "source": "common reagent table"},
    "acetic acid": {"name": "acetic acid", "smiles": "CC(=O)O", "source": "common reagent table"},
    "AcOH": {"name": "acetic acid", "smiles": "CC(=O)O", "source": "common reagent table"},
    "紫苏醇": {
        "name": "perillyl alcohol",
        "smiles": "CC(=C)C1CCC(=CC1)CO",
        "source": "local cache",
    },
    "perillyl alcohol": {
        "name": "perillyl alcohol",
        "smiles": "CC(=C)C1CCC(=CC1)CO",
        "source": "local cache",
    },
    "紫苏醇乙酸酯": {
        "name": "perillyl acetate",
        "smiles": "CC(=C)C1CCC(=CC1)COC(=O)C",
        "source": "local inferred ester product cache",
    },
    "perillyl acetate": {
        "name": "perillyl acetate",
        "smiles": "CC(=C)C1CCC(=CC1)COC(=O)C",
        "source": "local inferred ester product cache",
    },
}


@dataclass(frozen=True)
class ParsedStructure:
    id: str
    role: str
    name: str
    smiles: str
    source: str
    status: str = "verified"

    def as_dict(self) -> dict[str, str]:
        return {
            "id": self.id,
            "role": self.role,
            "name": self.name,
            "smiles": self.smiles,
            "source": self.source,
            "status": self.status,
        }


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def resolve_alias(text: str, aliases: list[str]) -> dict[str, str] | None:
    lower = text.lower()
    for alias in aliases:
        if alias.lower() in lower:
            return ALIASES[alias]
    return None


def parse_reaction_text(text: str) -> dict[str, Any]:
    if should_use_openai_agent():
        agent_result = parse_with_openai_agent(text)
        if agent_result.get("ok") or agent_result.get("questions"):
            agent_result.setdefault("parser_mode", "openai")
            return agent_result

    result = parse_with_rules(text)
    result["parser_mode"] = "rules"
    return result


def parser_status() -> dict[str, Any]:
    has_key = bool(os.environ.get("OPENAI_API_KEY"))
    return {
        "agent_available": has_key,
        "mode": "openai" if should_use_openai_agent() else "rules",
        "model": os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        "note": "OPENAI_API_KEY detected" if has_key else "No OPENAI_API_KEY; using lightweight rule parser",
    }


def should_use_openai_agent() -> bool:
    if os.environ.get("CHEMKIT_AGENT_MODE", "auto").lower() == "rules":
        return False
    return bool(os.environ.get("OPENAI_API_KEY"))


def parse_with_rules(text: str) -> dict[str, Any]:
    prompt = normalize_text(text)
    questions: list[str] = []
    warnings: list[str] = []

    perillyl = resolve_alias(prompt, ["紫苏醇", "perillyl alcohol"])
    acetic = resolve_alias(prompt, ["乙酸", "醋酸", "acetic acid", "AcOH"])

    is_esterification = any(term in prompt.lower() for term in ["酯化", "esterification", "dCC".lower(), "dmap"])
    has_dcc = "dcc" in prompt.lower()
    has_dmap = "dmap" in prompt.lower()

    if perillyl and acetic and is_esterification:
        product = ALIASES["perillyl acetate"]
        reactants = [
            ParsedStructure("r1", "R1", perillyl["name"], perillyl["smiles"], perillyl["source"]).as_dict(),
            ParsedStructure("r2", "R2", acetic["name"], acetic["smiles"], acetic["source"]).as_dict(),
        ]
        products = [
            ParsedStructure("p1", "P1", product["name"], product["smiles"], product["source"], "inferred").as_dict()
        ]
        if has_dcc or has_dmap:
            above = ["DCC, DMAP"]
        else:
            above = []
            questions.append("是否使用 DCC, DMAP 作为酯化条件？")
        below = ["CH₂Cl₂, 0 °C"]
        warnings.append("溶剂/温度未由输入明确给出，暂用默认 CH₂Cl₂, 0 °C。")
        return {
            "ok": True,
            "spec": {
                "title": "perillyl alcohol esterification",
                "reactants": reactants,
                "products": products,
                "conditions": {"above": above, "below": below, "yield": ""},
                "style": "chemdraw_compact",
            },
            "questions": questions,
            "warnings": warnings,
        }

    if "甲基紫苏酯" in prompt:
        questions.append("“甲基紫苏酯”有歧义：你是指紫苏酸甲酯，还是甲基丙烯酸紫苏酯？")

    if not perillyl and ("紫苏" in prompt or "perillyl" in prompt.lower()):
        questions.append("请确认紫苏相关化合物的具体结构或 SMILES。")
    if not acetic and ("酸" in prompt or "acid" in prompt.lower()):
        questions.append("请确认酸组分的具体名称或 SMILES。")
    if not questions:
        questions.append("我还不能可靠解析这个反应。请补充反应物、产物或 SMILES。")

    return {"ok": False, "spec": None, "questions": questions, "warnings": warnings}


def parse_with_openai_agent(text: str) -> dict[str, Any]:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return {"ok": False, "spec": None, "questions": [], "warnings": ["OPENAI_API_KEY is not set."]}

    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    schema = reaction_spec_schema()
    prompt = f"""
Parse this chemistry request into a ChemKit single-step reaction spec.

Rules:
- Return ok=false and one or more questions if any structure is ambiguous.
- Use SMILES only when you are chemically confident.
- Prefer common ACS/ChemDraw route conditions.
- Do not invent yields.
- For DCC/DMAP esterifications, put DCC, DMAP above the arrow and solvent/temperature below only if stated or safe as a warning default.
- Use Unicode subscripts in condition strings, e.g. CH₂Cl₂.

User request:
{text}
""".strip()
    payload = {
        "model": model,
        "input": [
            {"role": "system", "content": [{"type": "input_text", "text": "You are a careful chemistry reaction parser for RDKit route drawing."}]},
            {"role": "user", "content": [{"type": "input_text", "text": prompt}]},
        ],
        "text": {
            "format": {
                "type": "json_schema",
                "name": "chemkit_reaction_parse",
                "schema": schema,
                "strict": True,
            }
        },
    }
    request = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            body = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        fallback = parse_with_rules(text)
        fallback.setdefault("warnings", []).append(f"OpenAI agent unavailable; fell back to rules: {exc}")
        fallback["parser_mode"] = "rules-fallback"
        return fallback

    try:
        output_text = extract_response_text(body)
        parsed = json.loads(output_text)
    except (ValueError, json.JSONDecodeError) as exc:
        fallback = parse_with_rules(text)
        fallback.setdefault("warnings", []).append(f"OpenAI agent returned an unusable response; fell back to rules: {exc}")
        fallback["parser_mode"] = "rules-fallback"
        return fallback

    parsed.setdefault("warnings", [])
    parsed.setdefault("questions", [])
    return parsed


def extract_response_text(body: dict[str, Any]) -> str:
    if "output_text" in body:
        return body["output_text"]
    for item in body.get("output", []):
        for content in item.get("content", []):
            if content.get("type") in {"output_text", "text"} and "text" in content:
                return content["text"]
    raise ValueError("No text found in OpenAI response")


def reaction_spec_schema() -> dict[str, Any]:
    structure = {
        "type": "object",
        "additionalProperties": False,
        "required": ["id", "role", "name", "smiles", "source", "status"],
        "properties": {
            "id": {"type": "string"},
            "role": {"type": "string"},
            "name": {"type": "string"},
            "smiles": {"type": "string"},
            "source": {"type": "string"},
            "status": {"type": "string", "enum": ["verified", "inferred", "needs_confirmation"]},
        },
    }
    spec = {
        "type": "object",
        "additionalProperties": False,
        "required": ["title", "reactants", "products", "conditions", "style"],
        "properties": {
            "title": {"type": "string"},
            "reactants": {"type": "array", "items": structure, "minItems": 1, "maxItems": 3},
            "products": {"type": "array", "items": structure, "minItems": 1, "maxItems": 2},
            "conditions": {
                "type": "object",
                "additionalProperties": False,
                "required": ["above", "below", "yield"],
                "properties": {
                    "above": {"type": "array", "items": {"type": "string"}},
                    "below": {"type": "array", "items": {"type": "string"}},
                    "yield": {"type": "string"},
                },
            },
            "style": {"type": "string", "enum": ["chemdraw_compact"]},
        },
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["ok", "spec", "questions", "warnings"],
        "properties": {
            "ok": {"type": "boolean"},
            "spec": {"anyOf": [spec, {"type": "null"}]},
            "questions": {"type": "array", "items": {"type": "string"}},
            "warnings": {"type": "array", "items": {"type": "string"}},
        },
    }
