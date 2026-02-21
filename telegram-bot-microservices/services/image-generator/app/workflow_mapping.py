"""
Mapping between personas and their ComfyUI workflows
"""
from pathlib import Path
from typing import Dict, Optional

from app.config import config


# Universal workflow filename (single JSON for all personas)
UNIVERSAL_WORKFLOW = "universal_flow.json"

# Persona key → Workflow filename mapping (legacy, kept for reference)
PERSONA_WORKFLOW_MAP: Dict[str, str] = {
    "lina": UNIVERSAL_WORKFLOW,
    "marianna": UNIVERSAL_WORKFLOW,
    "mei": UNIVERSAL_WORKFLOW,
    "stacey": UNIVERSAL_WORKFLOW,
    "taya": UNIVERSAL_WORKFLOW,
    "julie": UNIVERSAL_WORKFLOW,
    "ash": UNIVERSAL_WORKFLOW,
    "anastasia": UNIVERSAL_WORKFLOW,
    "sasha": UNIVERSAL_WORKFLOW,
    "roxy": UNIVERSAL_WORKFLOW,
    "pai": UNIVERSAL_WORKFLOW,
    "hani": UNIVERSAL_WORKFLOW,
    "yuna": UNIVERSAL_WORKFLOW,
}

# Persona key → LoRA and sampler params for universal workflow injection
PERSONA_LORA_MAP: Dict[str, Dict] = {
    "lina": {
        "lora_name": "ameg2_con_char.safetensors",
        "strength_model": 0.88,
        "strength_clip": 0.93,
        "sampler_name": "res_multistep",
    },
    "marianna": {
        "lora_name": "QGVJNVQBYVJ0S2TRKZ005EF980.safetensors",
        "strength_model": 0.79,
        "strength_clip": 0.95,
        "sampler_name": "euler",
    },
    "mei": {
        "lora_name": "zimg_asig2_conchar.safetensors",
        "strength_model": 0.81,
        "strength_clip": 0.95,
        "sampler_name": "res_multistep",
    },
    "stacey": {
        "lora_name": "woman037-zimage.safetensors",
        "strength_model": 0.85,
        "strength_clip": 0.98,
        "sampler_name": "res_multistep",
    },
    "taya": {
        "lora_name": "Elise_XWMB_zimage.safetensors",
        "strength_model": 0.95,
        "strength_clip": 0.98,
        "sampler_name": "res_multistep",
    },
    "julie": {
        "lora_name": "elaravoss.safetensors",
        "strength_model": 0.93,
        "strength_clip": 0.99,
        "sampler_name": "res_multistep",
    },
    "ash": {
        "lora_name": "GF7184J7K4SJJSTY8VJ0VRBTQ0.safetensors",
        "strength_model": 0.95,
        "strength_clip": 0.99,
        "sampler_name": "res_multistep",
    },
    "anastasia": {
        "lora_name": "ULRIKANB_SYNTH_zimg_v1.safetensors",
        "strength_model": 0.78,
        "strength_clip": 0.92,
        "sampler_name": "res_multistep",
    },
    "sasha": {
        "lora_name": "zimg-eurameg1-refine-con-char.safetensors",
        "strength_model": 0.85,
        "strength_clip": 0.92,
        "sampler_name": "res_multistep",
    },
    "roxy": {
        "lora_name": "ChaseInfinity_ZimageTurbo.safetensors",
        "strength_model": 0.85,
        "strength_clip": 0.92,
        "sampler_name": "res_multistep",
    },
    "pai": {
        "lora_name": "DENISE_SYNTH_zimg_v1.safetensors",
        "strength_model": 0.75,
        "strength_clip": 0.87,
        "sampler_name": "res_multistep",
    },
    "hani": {
        "lora_name": "z-3l34n0r.safetensors",
        "strength_model": 0.80,
        "strength_clip": 0.85,
        "sampler_name": "res_multistep",
    },
    "yuna": {
        "lora_name": "nano_Korean.safetensors",
        "strength_model": 0.95,
        "strength_clip": 0.99,
        "sampler_name": "res_multistep",
    },
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


def get_lora_params(persona_key: str) -> Optional[Dict]:
    """
    Get LoRA and sampler parameters for a persona.

    Args:
        persona_key: Persona identifier

    Returns:
        Dict with lora_name, strength_model, strength_clip, sampler_name or None
    """
    return PERSONA_LORA_MAP.get(persona_key)


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
    "UNIVERSAL_WORKFLOW",
    "PERSONA_WORKFLOW_MAP",
    "PERSONA_LORA_MAP",
    "PERSONA_TRIGGER_MAP",
    "get_workflow_path",
    "get_lora_params",
    "get_trigger_word",
    "is_persona_supported",
]
