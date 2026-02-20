"""
Mapping between personas and their ComfyUI workflows
"""
from pathlib import Path
from typing import Dict, Optional

from app.config import config


# Persona key → Workflow filename mapping
PERSONA_WORKFLOW_MAP: Dict[str, str] = {
    "lina": "LINA_PROD_MVP_v2.json",
    "marianna": "MARIANNA_PROD_MVP_v2.json",
    "mei": "MEI_PROD_MVP_v2.json",
    "stacey": "STACY_PROD_MVP_v2.json",
    "taya": "TAYA_PROD_MVP_v2.json",
    "julie": "JULIE_PROD_MVP_v2.json",
    "ash": "ASH_PROD_MVP_v2.json",
    "anastasia": "ANASTASIA_PROD_MVP_v2.json",
    "sasha": "SASHA_PROD_MVP_v2.json",
    "roxy": "ROXY_PROD_MVP_v2.json",
    "pai": "PAI_PROD_MVP_v2.json",
    "hani": "HANI_PROD_MVP_v2.json",
    "yuna": "UNA_PROD_MVP_v2.json",
}


# Persona key → Trigger word mapping (from LoRA training)
PERSONA_TRIGGER_MAP: Dict[str, str] = {
    "lina": "ameg2",
    "marianna": "Amanda_Z, a beautiful woman with ginger hair, braided hair, green eyes and full lips",
    "yuna": "e1st_asn",
    "taya": "Elise_XWMB, she has blonde hair",
    "stacey": "woman037",
    "mei": "asig2",
    "ash": "brit-woman",
    "julie": "elvaross",
    "anastasia": "",
    "sasha": "eurameg1",
    "roxy": "Chase Infinity, African American, young woman",
    "pai": "DENISE",
    "hani": "l34n0r, chubby woman",
}


def get_workflow_path(persona_key: str) -> Optional[Path]:
    """
    Get full path to workflow JSON file for a persona.

    Args:
        persona_key: Persona identifier (lina, julie, ash, etc.)

    Returns:
        Path to workflow JSON file or None if not found
    """
    workflow_filename = PERSONA_WORKFLOW_MAP.get(persona_key)
    if not workflow_filename:
        return None

    workflow_path = config.WORKFLOWS_DIR / workflow_filename
    if not workflow_path.exists():
        return None

    return workflow_path


def get_trigger_word(persona_key: str) -> str:
    """
    Get trigger word for persona's LoRA.

    Args:
        persona_key: Persona identifier

    Returns:
        Trigger word or empty string if not configured
    """
    return PERSONA_TRIGGER_MAP.get(persona_key, "")


def is_persona_supported(persona_key: str) -> bool:
    """
    Check if persona has a workflow configured.

    Args:
        persona_key: Persona identifier

    Returns:
        True if workflow exists
    """
    return persona_key in PERSONA_WORKFLOW_MAP


__all__ = [
    "PERSONA_WORKFLOW_MAP",
    "PERSONA_TRIGGER_MAP",
    "get_workflow_path",
    "get_trigger_word",
    "is_persona_supported",
]
