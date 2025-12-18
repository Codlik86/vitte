# backend/app/services/image_generation.py
from __future__ import annotations

import asyncio
import json
import random
import time
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List

import httpx
from aiogram import Bot
from aiogram.types import BufferedInputFile

from ..config import settings
from ..db import get_session
from ..logging_config import logger
from sqlalchemy import select, text
from ..models import AccessStatus, Dialog, Message, Persona, User
from ..services.access import get_active_subscription
from ..services.analytics import log_event
from ..services.image_quota import consume_image, get_image_quota
from ..story_cards import StoryCard, get_story_cards_for_persona, resolve_story_id
from .persona_images import PersonaImageConfig, get_persona_image_config

WORKFLOW_DIR = Path(__file__).resolve().parent.parent / "assets" / "comfyui" / "workflows"
WORKFLOW_FILES = {
    "sdxl_lora": WORKFLOW_DIR / "sdxl_lora.json",
    "zimage_turbo_lora": WORKFLOW_DIR / "zimage_turbo_lora.json",
}
DEFAULT_WORKFLOW_NAME = "zimage_turbo_lora"
DEFAULT_CHECKPOINT_NAME = "models/checkpoints/huslyorealismxl_v2.safetensors"
DEFAULT_DIFFUSION_MODEL = "models/diffusion_models/z_image_turbo_bf16.safetensors"
DEFAULT_TEXT_ENCODER = "models/text_encoders/qwen_3_4b.safetensors"
DEFAULT_VAE = "models/vae/ae.safetensors"

# Без NSFW-тегов — только техничка.
DEFAULT_NEGATIVE = (
    "lowres, blurry, bad anatomy, bad proportions, deformed face, deformed hands, "
    "extra fingers, extra limbs, mutated, worst quality, jpeg artifacts, watermark, text, logo"
)

MAX_PROMPT_LEN = 240
MAX_HINT_LEN = 160
POLL_INTERVAL = 1.0
RETRIES = 2
USER_INTENT_KEYWORDS = {
    "покажи",
    "пришли",
    "хочу увидеть",
    "сделай фото",
    "вид",
    "ракурс",
    "поза",
    "спину",
    "лицо",
    "анфас",
    "профиль",
    "руки",
    "ноги",
    "спина",
    "грудь",
    "живот",
    "бедра",
    "одежд",
    "нижнее белье",
    "белье",
    "трус",
    "селфи",
    "зеркал",
    "камера",
    "делай снимок",
    "голову",
    "плечи",
    "покажи руку",
}
CUT_PHRASES = ("ENVIRONMENT:", "USER INTENT", "SEMANTIC CONTEXT", "CAMERA/STYLE")

_workflow_cache: Dict[str, Dict[str, Any]] = {}
_semaphore = asyncio.Semaphore(max(int(getattr(settings, "comfyui_concurrency", 1) or 1), 1))


def _deepcopy_workflow(template: Dict[str, Any]) -> Dict[str, Any]:
    return json.loads(json.dumps(template))


def _resolve_workflow_name() -> str:
    name = (getattr(settings, "comfyui_workflow_name", None) or "").strip().lower()
    if name in WORKFLOW_FILES:
        return name
    if name:
        logger.warning("Unknown ComfyUI workflow '%s', falling back to %s", name, DEFAULT_WORKFLOW_NAME)
    return DEFAULT_WORKFLOW_NAME


def _load_workflow_template(workflow_name: str) -> Dict[str, Any]:
    """
    Loads and caches workflow JSON template by name.
    Returns a deep copy every time (safe to mutate).
    """
    path = WORKFLOW_FILES.get(workflow_name) or WORKFLOW_FILES.get(DEFAULT_WORKFLOW_NAME)
    if not path:
        logger.error("ComfyUI workflow path not configured for %s", workflow_name)
        return {}

    cache_key = f"{workflow_name}:{path}"
    if cache_key not in _workflow_cache:
        try:
            _workflow_cache[cache_key] = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            logger.error("ComfyUI workflow template not found at %s", path)
            _workflow_cache[cache_key] = {}
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to read workflow template %s: %s", path, exc)
            _workflow_cache[cache_key] = {}

    return _deepcopy_workflow(_workflow_cache.get(cache_key) or {})


def _advisory_key(user_id: int, persona_id: int) -> int:
    return (int(user_id) << 20) + int(persona_id)


async def _try_acquire_advisory_lock(session, key: int) -> bool:
    try:
        result = await session.execute(text("SELECT pg_try_advisory_lock(:key) AS locked"), {"key": key})
        row = result.fetchone()
        return bool(row and row[0])
    except Exception as exc:  # noqa: BLE001
        logger.warning("Advisory lock unavailable, continuing without lock: %s", exc)
        return True


async def _release_advisory_lock(session, key: int) -> None:
    try:
        await session.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": key})
    except Exception as exc:  # noqa: BLE001
        logger.warning("Advisory unlock failed (ignored): %s", exc)


@dataclass
class GenerationPlan:
    user_id: int
    chat_id: int
    persona_id: int
    persona_key: str | None
    persona_name: str | None
    prompt: str
    negative_prompt: str
    config: PersonaImageConfig
    has_subscription: bool


@dataclass
class ImageRequestInputs:
    user_id: int
    persona_id: int
    dialog: Dialog | None
    entry_story_id: str | None
    last_user_messages: List[str]
    history_user_messages: List[str]
    story_scene: str | None
    story_text: str | None
    persona_fallback: str
    config: PersonaImageConfig


@dataclass
class ImageContext:
    user_intent_text: str
    scene_text: str
    semantic_context_text: str
    persona_fallback: str
    prompt_core: str
    negative_text: str
    camera_style_text: str


async def _get_latest_dialog(session, user_id: int, persona_id: int) -> Dialog | None:
    res = await session.execute(
        select(Dialog).where(Dialog.user_id == user_id, Dialog.character_id == persona_id).order_by(Dialog.id.desc()).limit(1)
    )
    return res.scalar_one_or_none()


def find_first_node_id(
    workflow: Dict[str, Any],
    class_type: str,
    *,
    title_hints: str | Iterable[str] | None = None,
    exclude: Iterable[str] | None = None,
) -> str | None:
    """
    Returns the first node id matching class_type.
    If title_hints provided, prefers nodes whose _meta.title contains the hint(s).
    """
    exclude_set = {str(item) for item in (exclude or [])}
    matches: list[tuple[str, dict]] = []

    for node_id, node in workflow.items():
        if str(node_id) in exclude_set:
            continue
        if not isinstance(node, dict):
            continue
        if str(node.get("class_type")) != class_type:
            continue
        matches.append((str(node_id), node))

    if not matches:
        return None

    hints: list[str] = []
    if isinstance(title_hints, str):
        hints = [title_hints]
    elif title_hints:
        hints = list(title_hints)

    for hint in hints:
        lowered_hint = hint.lower()
        for node_id, node in matches:
            title = str(node.get("_meta", {}).get("title", "")).lower()
            if lowered_hint in title:
                return node_id

    return matches[0][0]


def _extract_connected_node_id(
    workflow: Dict[str, Any], inputs: Dict[str, Any], key: str, expected_class: str
) -> str | None:
    ref = inputs.get(key)
    if isinstance(ref, list) and ref:
        candidate = str(ref[0])
        node = workflow.get(candidate)
        if isinstance(node, dict) and node.get("class_type") == expected_class:
            return candidate
    return None


def _find_clip_text_nodes(workflow: Dict[str, Any], sampler_node_id: str | None) -> tuple[str | None, str | None]:
    sampler_inputs = workflow.get(sampler_node_id, {}).get("inputs", {}) if sampler_node_id else {}

    positive_node_id = _extract_connected_node_id(workflow, sampler_inputs, "positive", "CLIPTextEncode")
    negative_node_id = _extract_connected_node_id(workflow, sampler_inputs, "negative", "CLIPTextEncode")

    if not positive_node_id:
        positive_node_id = find_first_node_id(
            workflow,
            "CLIPTextEncode",
            title_hints=["positive", "prompt", "clip text encode"],
        )

    if not negative_node_id:
        negative_node_id = find_first_node_id(
            workflow,
            "CLIPTextEncode",
            title_hints=["negative", "prompt", "clip text encode"],
            exclude=[positive_node_id] if positive_node_id else None,
        )

    return positive_node_id, negative_node_id


def _collect_node_ids(workflow: Dict[str, Any], class_types: Iterable[str]) -> list[str]:
    target = {str(cls) for cls in class_types}
    found: list[str] = []
    for node_id, node in workflow.items():
        if not isinstance(node, dict):
            continue
        if str(node.get("class_type")) in target:
            found.append(str(node_id))
    return found


def _apply_template_values(
    template: Dict[str, Any],
    *,
    prompt: str,
    negative_prompt: str,
    config: PersonaImageConfig,
    workflow_name: str,
) -> Dict[str, Any]:
    workflow = template

    checkpoint_node_id = find_first_node_id(
        workflow,
        "CheckpointLoaderSimple",
        title_hints=["load checkpoint", "checkpoint"],
    )
    unet_node_id = find_first_node_id(workflow, "UNETLoader", title_hints=["unet", "diffusion", "load model"])
    clip_loader_id = find_first_node_id(workflow, "CLIPLoader", title_hints=["clip", "text encoder", "load clip"])
    vae_loader_id = find_first_node_id(workflow, "VAELoader", title_hints=["vae"])
    sampler_node_id = find_first_node_id(workflow, "KSampler", title_hints=["ksampler", "sampler"])
    lora_node_ids = _collect_node_ids(workflow, ["LoraLoader", "LoraLoaderModelOnly"])
    positive_clip_id, negative_clip_id = _find_clip_text_nodes(workflow, sampler_node_id)

    missing = []
    if not checkpoint_node_id and not unet_node_id:
        missing.append("diffusion_model")
    if not lora_node_ids:
        missing.append("lora")
    if not sampler_node_id:
        missing.append("sampler")
    if not positive_clip_id:
        missing.append("positive_text")
    if not clip_loader_id:
        missing.append("clip_loader")
    if not vae_loader_id:
        missing.append("vae_loader")

    if missing:
        logger.error(
            "Workflow %s missing nodes (expected CheckpointLoaderSimple/UNETLoader, LoraLoader/LoraLoaderModelOnly, "
            "CLIPTextEncode, CLIPLoader, VAELoader, KSampler): %s",
            workflow_name,
            ", ".join(sorted(missing)),
        )
        raise ImageRequestError("bad_workflow_template")

    primary_lora_id = lora_node_ids[0] if lora_node_ids else None
    secondary_lora_id = lora_node_ids[1] if len(lora_node_ids) > 1 else None

    checkpoint_inputs = workflow.get(checkpoint_node_id or "", {}).setdefault("inputs", {})
    unet_inputs = workflow.get(unet_node_id or "", {}).setdefault("inputs", {})
    clip_inputs = workflow.get(clip_loader_id or "", {}).setdefault("inputs", {})
    vae_inputs = workflow.get(vae_loader_id or "", {}).setdefault("inputs", {})
    sampler_inputs = workflow.get(sampler_node_id or "", {}).setdefault("inputs", {})
    positive_inputs = workflow.get(positive_clip_id or "", {}).setdefault("inputs", {})

    checkpoint_name = settings.comfyui_default_checkpoint or checkpoint_inputs.get("ckpt_name") or DEFAULT_CHECKPOINT_NAME
    diffusion_model_name = (
        getattr(settings, "comfyui_default_diffusion_model", None)
        or unet_inputs.get("unet_name")
        or DEFAULT_DIFFUSION_MODEL
    )
    clip_name = (
        getattr(settings, "comfyui_default_text_encoder", None) or clip_inputs.get("clip_name") or DEFAULT_TEXT_ENCODER
    )
    vae_name = getattr(settings, "comfyui_default_vae", None) or vae_inputs.get("vae_name") or DEFAULT_VAE

    if checkpoint_node_id:
        checkpoint_inputs["ckpt_name"] = checkpoint_name
    if unet_node_id:
        unet_inputs["unet_name"] = diffusion_model_name
    if clip_loader_id:
        clip_inputs["clip_name"] = clip_name
    if vae_loader_id:
        vae_inputs["vae_name"] = vae_name

    lora_filename = Path(config.lora_filename).name
    if primary_lora_id:
        primary_inputs = workflow.get(primary_lora_id, {}).setdefault("inputs", {})
        primary_inputs["lora_name"] = lora_filename
        if "strength_model" in primary_inputs:
            primary_inputs["strength_model"] = float(config.lora_strength_model)
        if "strength_clip" in primary_inputs:
            primary_inputs["strength_clip"] = float(config.lora_strength_clip)

    if secondary_lora_id:
        secondary_inputs = workflow.get(secondary_lora_id, {}).setdefault("inputs", {})
        if config.quality_lora_filename:
            secondary_inputs["lora_name"] = Path(config.quality_lora_filename).name
            if "strength_model" in secondary_inputs:
                secondary_inputs["strength_model"] = float(config.quality_lora_strength)
            if "strength_clip" in secondary_inputs:
                secondary_inputs["strength_clip"] = float(config.quality_lora_strength)
        elif "strength_model" in secondary_inputs:
            secondary_inputs["strength_model"] = 0.0
            if "strength_clip" in secondary_inputs:
                secondary_inputs["strength_clip"] = 0.0

    positive_inputs["text"] = prompt

    if negative_clip_id:
        negative_inputs = workflow.get(negative_clip_id, {}).setdefault("inputs", {})
        if workflow.get(negative_clip_id, {}).get("class_type") == "CLIPTextEncode":
            negative_inputs["text"] = negative_prompt or DEFAULT_NEGATIVE
    else:
        logger.info("Workflow %s has no negative CLIP node; keeping template negative prompt", workflow_name)

    sampler_inputs["seed"] = random.randint(1, 2_000_000_000)

    logger.info(
        "Workflow nodes workflow=%s ckpt=%s unet=%s clip=%s vae=%s loras=%s sampler=%s",
        workflow_name,
        checkpoint_node_id,
        unet_node_id,
        clip_loader_id,
        vae_loader_id,
        ",".join(lora_node_ids),
        sampler_node_id,
    )

    return workflow


def _trim_hint_text(text: str) -> str:
    cleaned = text.replace("\n", " ").replace("\r", " ").strip()
    if len(cleaned) > MAX_HINT_LEN:
        cleaned = cleaned[:MAX_HINT_LEN].rsplit(" ", 1)[0]
    return cleaned


async def _build_context_hint_from_history(
    session,
    user_id: int,
    persona_id: int,
    limit: int = 5,
    dialog: Dialog | None = None,
) -> str:
    try:
        target_dialog = dialog
        if target_dialog is None:
            target_dialog = await _get_latest_dialog(session, user_id, persona_id)
        if not target_dialog:
            return ""

        msg_res = await session.execute(
            select(Message.content)
            .where(Message.dialog_id == target_dialog.id, Message.role == "user")
            .order_by(Message.id.desc())
            .limit(limit)
        )
        messages = [row[0] for row in msg_res.fetchall() if row[0]]
        if not messages:
            return ""

        messages = list(reversed(messages))
        combined = ". ".join(m.replace("\n", " ").replace("\r", " ").strip() for m in messages if m)
        return _trim_hint_text(combined)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to build history hint user=%s persona=%s err=%s", user_id, persona_id, exc)
        return ""


async def _load_user_request_text(session, dialog: Dialog | None, limit: int = 2) -> str:
    if not dialog:
        return ""
    try:
        msg_res = await session.execute(
            select(Message.content)
            .where(Message.dialog_id == dialog.id, Message.role == "user")
            .order_by(Message.id.desc())
            .limit(limit)
        )
        messages = [row[0] for row in msg_res.fetchall() if row[0]]
        if not messages:
            return ""
        messages = list(reversed(messages))
        normalized = [m.replace("\n", " ").replace("\r", " ").strip() for m in messages if m]
        for text in reversed(normalized):
            lowered = text.lower()
            if any(marker in lowered for marker in USER_INTENT_KEYWORDS):
                return _trim_hint_text(text)
        combined = " ".join(normalized)
        return _trim_hint_text(combined)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to load user request text dialog=%s err=%s", dialog.id if dialog else None, exc)
        return ""


async def _fetch_last_user_messages(session, dialog: Dialog | None, limit: int) -> list[str]:
    if not dialog:
        return []
    try:
        msg_res = await session.execute(
            select(Message.content)
            .where(Message.dialog_id == dialog.id, Message.role == "user")
            .order_by(Message.id.desc())
            .limit(limit)
        )
        messages = [row[0] for row in msg_res.fetchall() if row[0]]
        messages.reverse()
        return messages
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to fetch last user messages dialog=%s err=%s", dialog.id if dialog else None, exc)
        return []


def _build_story_hint_from_ctx(context: dict[str, Any]) -> str:
    story_scene = str(context.get("story_scene") or "").strip()
    story_text = str(context.get("story_text") or "").strip()
    story_title = str(context.get("story_title") or "").strip()

    if story_scene:
        return _trim_hint_text(story_scene)

    combined = " ".join(part for part in [story_title, story_text] if part)
    if combined.strip():
        return _trim_hint_text(combined.strip())
    return ""


def _story_from_card(card: StoryCard | None) -> dict[str, str]:
    if not card:
        return {}
    return {
        "story_id": card.id,
        "story_title": card.title,
        "story_scene": card.prompt,
        "story_text": card.description,
    }


async def _load_story_context(
    persona: Persona,
    dialog: Dialog | None,
) -> dict[str, str]:
    if dialog is None or not dialog.entry_story_id:
        return {}
    resolved_id = resolve_story_id(dialog.entry_story_id)
    if not resolved_id:
        return {}
    cards = get_story_cards_for_persona(persona.archetype, persona.name)
    card = next((c for c in cards if c.id == resolved_id), None)
    return _story_from_card(card)


def _build_image_context(inputs: ImageRequestInputs, context: dict[str, Any]) -> ImageContext:
    story_hint = _build_story_hint_from_ctx(context)
    env_text = _trim_hint_text(story_hint)

    history_text = context.get("history_text") or ""
    if isinstance(history_text, list):
        history_text = " ".join([str(item) for item in history_text])

    semantic_context = ""
    if not context.get("user_request_text"):
        semantic_context = _trim_hint_text(str(history_text or ""))

    user_request = _trim_hint_text(str(context.get("user_request_text") or ""))
    persona_fallback = _trim_hint_text(inputs.persona_fallback or "")

    camera_style = "85mm lens, shallow depth of field, high detail, cinematic lighting"

    return ImageContext(
        user_intent_text=user_request,
        scene_text=env_text,
        semantic_context_text=semantic_context,
        persona_fallback=persona_fallback,
        prompt_core=inputs.config.prompt_core,
        negative_text=inputs.config.negative_prompt or DEFAULT_NEGATIVE,
        camera_style_text=camera_style,
    )


def _compose_structured_prompt(img_ctx: ImageContext) -> str:
    segments: list[str] = []
    core = img_ctx.prompt_core.strip().strip(",")
    if core:
        segments.append(f"CORE SUBJECT: {core}")

    if img_ctx.scene_text:
        segments.append(f"SCENE: {img_ctx.scene_text}")

    if img_ctx.user_intent_text:
        segments.append(f"USER INTENT (follow precisely): {img_ctx.user_intent_text}")
    elif img_ctx.semantic_context_text:
        segments.append(f"SEMANTIC CONTEXT: {img_ctx.semantic_context_text}")
    elif img_ctx.persona_fallback:
        segments.append(f"FALLBACK: {img_ctx.persona_fallback}")

    segments.append(f"CAMERA/STYLE: {img_ctx.camera_style_text}")

    prompt = ". ".join(segments)

    if len(prompt) > MAX_PROMPT_LEN:
        # remove semantic/fallback first
        segments = [s for s in segments if not s.startswith("SEMANTIC CONTEXT") and not s.startswith("FALLBACK")]
        prompt = ". ".join(segments)
    if len(prompt) > MAX_PROMPT_LEN and img_ctx.scene_text:
        trimmed_scene = _trim_hint_text(img_ctx.scene_text[: max(30, MAX_HINT_LEN // 2)])
        segments = [seg for seg in segments if not seg.startswith("SCENE")]
        if trimmed_scene:
            segments.insert(1, f"SCENE: {trimmed_scene}")
        prompt = ". ".join(segments)
    if len(prompt) > MAX_PROMPT_LEN:
        prompt = prompt[:MAX_PROMPT_LEN]

    logger.info(
        "Image prompt parts user_intent=%s scene=%s semantic=%s len=%s preview=%s",
        img_ctx.user_intent_text[:80],
        img_ctx.scene_text[:80],
        img_ctx.semantic_context_text[:80],
        len(prompt),
        prompt[:120],
    )
    return prompt


def _build_full_prompt(config: PersonaImageConfig, hint: str) -> str:
    """
    prompt_core + (optional hint) + (optional default_style)
    """
    style = f", {config.default_style}" if config.default_style else ""
    trimmed_hint = hint.strip(" .,")

    pieces = [config.prompt_core]
    if trimmed_hint:
        pieces.append(trimmed_hint)

    prompt = ", ".join(pieces) + style
    return prompt[:MAX_PROMPT_LEN]


async def ping_comfyui(base_url: str | None = None) -> bool:
    target = (base_url or settings.comfyui_base_url or "").rstrip("/")
    if not target:
        logger.info("ComfyUI ping skipped: base_url not configured")
        return False
    url = f"{target}/system_stats"
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(5.0, connect=3.0)) as client:
            resp = await client.get(url)
            logger.info("ComfyUI ping status=%s url=%s", resp.status_code, url)
            return resp.status_code == 200
    except Exception:  # noqa: BLE001
        logger.exception("COMFYUI_UNREACHABLE base_url=%s", target)
        return False


async def _log_failure(plan: GenerationPlan, reason: str, extra: Dict[str, Any] | None = None) -> None:
    payload: Dict[str, Any] = {"reason": reason, "persona_id": plan.persona_id, "persona_key": plan.persona_key}
    if extra:
        payload.update(extra)

    async for session in get_session():
        try:
            await log_event(session, plan.user_id, "image_failed", payload)
            await session.commit()
        except Exception:
            await session.rollback()
        break


async def request_comfyui(*, workflow_payload: Dict[str, Any], client_id: str | None = None) -> bytes:
    """
    Sends a workflow to ComfyUI and returns the generated image bytes.
    Includes client_id for easier debugging and more stable history tracking.
    """
    base_url = (settings.comfyui_base_url or "").rstrip("/")
    if not base_url:
        raise RuntimeError("COMFYUI_BASE_URL is not configured")

    timeout_seconds = float(getattr(settings, "comfyui_timeout_seconds", 90) or 90)
    timeout = httpx.Timeout(timeout_seconds, connect=10.0, read=timeout_seconds, write=timeout_seconds)

    logger.info("ComfyUI prompt request base_url=%s", base_url)

    async with httpx.AsyncClient(timeout=timeout) as client:
        last_error: Exception | None = None

        for attempt in range(1, RETRIES + 2):
            try:
                payload = _normalize_prompt_payload(workflow_payload, client_id)

                resp = await client.post(f"{base_url}/prompt", json=payload)
                logger.info(
                    "ComfyUI /prompt status=%s len=%s attempt=%s",
                    resp.status_code,
                    len(resp.content or b""),
                    attempt,
                )
                resp.raise_for_status()

                data = resp.json() or {}
                prompt_id = data.get("prompt_id") or data.get("promptId")
                if not prompt_id:
                    raise RuntimeError(f"No prompt_id in ComfyUI response: {data}")

                logger.info("ComfyUI prompt_id=%s received", prompt_id)
                image_info = await _wait_for_image(client, base_url, str(prompt_id))
                return await _download_image(client, base_url, image_info)

            except httpx.HTTPStatusError as exc:
                logger.exception(
                    "ComfyUI HTTP error base_url=%s status=%s body=%s",
                    base_url,
                    getattr(exc.response, "status_code", None),
                    (exc.response.text or "")[:3000] if exc.response else "",
                )
                last_error = exc
            except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
                logger.exception("COMFYUI_UNREACHABLE base_url=%s", base_url)
                last_error = exc
                break
            except (httpx.ReadTimeout, TimeoutError) as exc:
                logger.exception("ComfyUI timeout base_url=%s", base_url)
                last_error = exc
            except Exception as exc:  # noqa: BLE001
                logger.exception("ComfyUI unknown error base_url=%s", base_url)
                last_error = exc

            if attempt >= (RETRIES + 1):
                break
            await asyncio.sleep(1.5 * attempt)

        raise last_error or RuntimeError(f"COMFYUI_UNREACHABLE base_url={base_url}")


async def _wait_for_image(client: httpx.AsyncClient, base_url: str, prompt_id: str) -> dict:
    deadline = time.monotonic() + float(getattr(settings, "comfyui_timeout_seconds", 90) or 90)

    while time.monotonic() < deadline:
        resp = await client.get(f"{base_url}/history/{prompt_id}")
        logger.info("ComfyUI /history/%s status=%s", prompt_id, resp.status_code)
        resp.raise_for_status()

        try:
            data = resp.json() or {}
        except Exception as exc:  # noqa: BLE001
            # Occasionally (especially through tunnels) body can be non-JSON; retry.
            logger.warning("ComfyUI history json parse failed prompt_id=%s err=%s", prompt_id, exc)
            await asyncio.sleep(POLL_INTERVAL)
            continue

        record = data.get(prompt_id) or {}
        outputs = record.get("outputs") or {}

        for node_id, node in outputs.items():
            images = node.get("images") or []
            if images:
                logger.info("ComfyUI history got images from node=%s prompt_id=%s", node_id, prompt_id)
                return images[0]

        logger.info("ComfyUI waiting images prompt_id=%s outputs=%s", prompt_id, list(outputs.keys()))
        await asyncio.sleep(POLL_INTERVAL)

    raise TimeoutError("ComfyUI generation timed out")


async def _download_image(client: httpx.AsyncClient, base_url: str, image_info: dict) -> bytes:
    filename = image_info.get("filename")
    subfolder = image_info.get("subfolder", "")
    file_type = image_info.get("type", "output")

    if not filename:
        raise RuntimeError("ComfyUI returned empty filename")

    params = {"filename": filename}
    if subfolder:
        params["subfolder"] = subfolder
    if file_type:
        params["type"] = file_type

    resp = await client.get(f"{base_url}/view", params=params)
    logger.info("ComfyUI /view status=%s file=%s", resp.status_code, filename)
    resp.raise_for_status()
    return resp.content


def _normalize_prompt_payload(workflow_payload: Dict[str, Any] | None, client_id: str | None) -> Dict[str, Any]:
    """
    ComfyUI API expects {"prompt": <nodes_dict>, "client_id": "..."}.
    Accepts raw nodes dict or already-wrapped payload; normalizes and validates.
    """
    payload: Dict[str, Any]
    if not isinstance(workflow_payload, dict):
        raise ImageGenerationConfigError("bad_workflow_template")

    if "prompt" in workflow_payload and isinstance(workflow_payload.get("prompt"), dict):
        payload = dict(workflow_payload)
        if client_id:
            payload["client_id"] = client_id
    else:
        # Sometimes exported workflows use other top-level keys; try to locate node map.
        nodes = workflow_payload.get("nodes") if isinstance(workflow_payload.get("nodes"), dict) else None
        if nodes:
            payload = {"prompt": nodes}
        else:
            payload = {"prompt": workflow_payload}
        if client_id:
            payload["client_id"] = client_id

    if not isinstance(payload.get("prompt"), dict):
        raise ImageGenerationConfigError("bad_workflow_template")
    _validate_prompt(payload["prompt"])
    return payload


def _validate_prompt(nodes: Dict[str, Any]) -> None:
    if not isinstance(nodes, dict):
        raise ImageGenerationConfigError("bad_workflow_template")

    ids = {str(k) for k in nodes.keys()}
    for node_id, node in nodes.items():
        if not isinstance(node, dict):
            raise ImageGenerationConfigError("bad_workflow_template")
        inputs = node.get("inputs", {})
        class_type = node.get("class_type")
        if not class_type or not isinstance(inputs, dict):
            raise ImageGenerationConfigError("bad_workflow_template")
        for value in inputs.values():
            if isinstance(value, list) and value:
                ref_id = str(value[0])
                if ref_id not in ids:
                    raise ImageGenerationConfigError("bad_workflow_template")

async def _deliver_image(plan: GenerationPlan, image_bytes: bytes, bot_instance: Bot) -> None:
    input_file = BufferedInputFile(image_bytes, filename="vitte_image.png")
    await bot_instance.send_photo(plan.chat_id, input_file)


async def _persist_image_usage(session, plan: GenerationPlan) -> None:
    user = await session.get(User, plan.user_id)
    if not user:
        return
    await consume_image(session, user, count=1, has_subscription=plan.has_subscription)
    user.last_image_sent_at = datetime.utcnow()
    await log_event(
        session,
        user.id,
        "image_generated",
        {"persona_id": plan.persona_id, "persona_key": plan.persona_key},
    )

async def _generate_and_send(plan: GenerationPlan, context: dict[str, Any], bot_instance: Bot) -> bool:
    base_url = (settings.comfyui_base_url or "").rstrip("/")
    if not base_url:
        logger.info("ComfyUI base URL is not configured; skipping image generation")
        await _log_failure(plan, "not_configured")
        return False

    workflow_name = _resolve_workflow_name()
    template = _load_workflow_template(workflow_name)
    if not template:
        logger.error("Workflow template %s is empty or missing", workflow_name)
        await _log_failure(plan, "bad_workflow_template")
        return False
    try:
        workflow = _apply_template_values(
            template,
            prompt=plan.prompt,
            negative_prompt=plan.negative_prompt,
            config=plan.config,
            workflow_name=workflow_name,
        )
    except ImageRequestError as exc:
        logger.error(
            "Failed to apply workflow template user=%s persona=%s reason=%s",
            plan.user_id,
            plan.persona_id,
            exc.reason,
        )
        await _log_failure(plan, exc.reason or "bad_workflow_template")
        return False
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to apply workflow template user=%s persona=%s: %s", plan.user_id, plan.persona_id, exc)
        await _log_failure(plan, "bad_workflow_template")
        return False

    checkpoint_node_id = find_first_node_id(workflow, "CheckpointLoaderSimple", title_hints=["checkpoint"])
    ckpt_name = (
        workflow.get(checkpoint_node_id or "", {}).get("inputs", {}).get("ckpt_name")
        if checkpoint_node_id
        else None
    )
    quality_name = Path(plan.config.quality_lora_filename).name if plan.config.quality_lora_filename else None

    logger.info(
        "ComfyUI request user=%s persona=%s workflow=%s ckpt=%s lora=%s quality_lora=%s strengths=(%.2f/%.2f/%.2f)",
        plan.user_id,
        plan.persona_id,
        workflow_name,
        ckpt_name,
        Path(plan.config.lora_filename).name,
        quality_name,
        plan.config.lora_strength_model,
        plan.config.lora_strength_clip,
        plan.config.quality_lora_strength if quality_name else 0.0,
    )

    # Stable-ish client_id helps debugging and history tracking through tunnels.
    client_id = f"vitte-{plan.user_id}-{plan.persona_id}-{uuid.uuid4().hex[:8]}"

    try:
        async with _semaphore:
            image_bytes = await request_comfyui(workflow_payload=workflow, client_id=client_id)
        await _deliver_image(plan, image_bytes, bot_instance)
        return True

    except Exception:  # noqa: BLE001
        logger.exception("Image generation/delivery failed user=%s persona=%s", plan.user_id, plan.persona_id)
        await _log_failure(plan, "generation_error")
        return False


async def _generate_image_bytes(plan: GenerationPlan, context: dict[str, Any]) -> bytes:
    base_url = (settings.comfyui_base_url or "").rstrip("/")
    if not base_url:
        await _log_failure(plan, "not_configured")
        raise ImageRequestError("generation_failed")

    workflow_name = _resolve_workflow_name()
    template = _load_workflow_template(workflow_name)
    if not template:
        logger.error("Workflow template %s is empty or missing", workflow_name)
        await _log_failure(plan, "bad_workflow_template")
        raise ImageRequestError("generation_failed")

    try:
        workflow = _apply_template_values(
            template,
            prompt=plan.prompt,
            negative_prompt=plan.negative_prompt,
            config=plan.config,
            workflow_name=workflow_name,
        )
    except ImageRequestError as exc:
        logger.error(
            "Failed to apply workflow template user=%s persona=%s reason=%s",
            plan.user_id,
            plan.persona_id,
            exc.reason,
        )
        await _log_failure(plan, exc.reason or "bad_workflow_template")
        raise
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to apply workflow template user=%s persona=%s: %s", plan.user_id, plan.persona_id, exc)
        await _log_failure(plan, "bad_workflow_template")
        raise ImageRequestError("generation_failed")

    checkpoint_node_id = find_first_node_id(workflow, "CheckpointLoaderSimple", title_hints=["checkpoint"])
    ckpt_name = (
        workflow.get(checkpoint_node_id or "", {}).get("inputs", {}).get("ckpt_name")
        if checkpoint_node_id
        else None
    )
    quality_name = Path(plan.config.quality_lora_filename).name if plan.config.quality_lora_filename else None

    logger.info(
        "ComfyUI request user=%s persona=%s workflow=%s ckpt=%s lora=%s quality_lora=%s strengths=(%.2f/%.2f/%.2f)",
        plan.user_id,
        plan.persona_id,
        workflow_name,
        ckpt_name,
        Path(plan.config.lora_filename).name,
        quality_name,
        plan.config.lora_strength_model,
        plan.config.lora_strength_clip,
        plan.config.quality_lora_strength if quality_name else 0.0,
    )

    client_id = f"vitte-{plan.user_id}-{plan.persona_id}-{uuid.uuid4().hex[:8]}"

    async with _semaphore:
        try:
            return await request_comfyui(workflow_payload=workflow, client_id=client_id)
        except Exception:  # noqa: BLE001
            logger.exception("Image generation failed user=%s persona=%s", plan.user_id, plan.persona_id)
            await _log_failure(plan, "generation_error")
            raise ImageRequestError("generation_failed")


class ImageRequestError(RuntimeError):
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)


class ImageGenerationConfigError(ImageRequestError):
    pass

async def request_image_on_demand(
    user_id: int,
    chat_id: int,
    persona_id: int,
    bot_instance: Bot,
    context: dict[str, Any] | None = None,
) -> None:
    """
    Generate and send image on explicit user action.
    """
    if not getattr(settings, "image_enabled", False):
        raise ImageRequestError("disabled")

    ctx = context or {}
    success = False
    image_bytes: bytes | None = None
    plan: GenerationPlan | None = None
    success = False
    image_bytes: bytes | None = None

    async for session in get_session():
        user = await session.get(User, user_id)
        persona = await session.get(Persona, persona_id) if persona_id else None
        if not user or not persona:
            raise ImageRequestError("not_found")

        lock_key = _advisory_key(user.id, persona.id)
        lock_acquired = await _try_acquire_advisory_lock(session, lock_key)
        if not lock_acquired:
            raise ImageRequestError("busy")

        try:
            dialog = await _get_latest_dialog(session, user.id, persona.id)

            if "history_text" not in ctx and "recent_messages" not in ctx:
                history_hint = await _build_context_hint_from_history(session, user.id, persona.id, dialog=dialog)
                if history_hint:
                    ctx["history_text"] = history_hint

            if not any(ctx.get(key) for key in ("story_scene", "story_text", "story_title")):
                story_ctx = await _load_story_context(persona, dialog)
                for key, value in story_ctx.items():
                    ctx.setdefault(key, value)

            if "user_request_text" not in ctx:
                user_req = await _load_user_request_text(session, dialog)
                if user_req:
                    ctx["user_request_text"] = user_req

            has_subscription = bool(
                user.access_status == AccessStatus.SUBSCRIPTION_ACTIVE
                or await get_active_subscription(session, user.id)
            )

            quota = await get_image_quota(session, user, has_subscription=has_subscription)
            if quota.get("total_remaining", 0) <= 0:
                await log_event(session, user.id, "image_failed", {"reason": "no_quota", "persona_id": persona.id})
                await session.commit()
                raise ImageRequestError("no_quota")

            config = get_persona_image_config(persona.key, persona.name)
            last_user_messages = await _fetch_last_user_messages(session, dialog, limit=2)
            history_msgs = await _fetch_last_user_messages(session, dialog, limit=5)

            inputs = ImageRequestInputs(
                user_id=user.id,
                persona_id=persona.id,
                dialog=dialog,
                entry_story_id=dialog.entry_story_id if dialog else None,
                last_user_messages=last_user_messages,
                history_user_messages=history_msgs,
                story_scene=ctx.get("story_scene") or "",
                story_text=ctx.get("story_text") or ctx.get("story_title") or "",
                persona_fallback=persona.short_description or persona.name or "",
                config=config,
            )

            if not ctx.get("user_request_text"):
                ctx["user_request_text"] = inputs.last_user_messages[-1] if inputs.last_user_messages else ""
            img_ctx = _build_image_context(inputs, ctx)
            prompt = _compose_structured_prompt(img_ctx)
            negative_prompt = (img_ctx.negative_text or DEFAULT_NEGATIVE).strip()

            await log_event(
                session,
                user.id,
                "image_requested",
                {"persona_id": persona.id, "persona_key": persona.key, "trigger": "button"},
            )
            await session.commit()

            plan = GenerationPlan(
                user_id=user.id,
                chat_id=chat_id,
                persona_id=persona.id,
                persona_key=persona.key,
                persona_name=persona.name,
                prompt=prompt,
                negative_prompt=negative_prompt,
                config=config,
                has_subscription=has_subscription,
            )

            try:
                image_bytes = await _generate_image_bytes(plan, ctx)
                await _persist_image_usage(session, plan)
                await session.commit()
                success = True
            except Exception:  # noqa: BLE001
                logger.exception("Image generation failed for user=%s persona=%s", user.id, persona.id)
                await session.rollback()
                success = False
        finally:
            await _release_advisory_lock(session, lock_key)
        break
    else:
        raise ImageRequestError("not_found")

    if success:
        await _deliver_image(plan, image_bytes, bot_instance)
    else:
        try:
            await bot_instance.send_message(chat_id, "Не удалось сгенерировать изображение. Попробуй ещё раз через минуту.")
        except Exception:  # noqa: BLE001
            logger.exception(
                "Failed to send image fallback message user=%s persona=%s",
                plan.user_id if plan else user_id,
                plan.persona_id if plan else persona_id,
            )
