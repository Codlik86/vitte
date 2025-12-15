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
from typing import Any, Dict, Iterable

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

WORKFLOW_PATH = Path(__file__).resolve().parent.parent / "assets" / "comfyui" / "workflows" / "sdxl_lora.json"

# Без NSFW-тегов — только техничка.
DEFAULT_NEGATIVE = (
    "lowres, blurry, bad anatomy, bad proportions, deformed face, deformed hands, "
    "extra fingers, extra limbs, mutated, worst quality, jpeg artifacts, watermark, text, logo"
)

MAX_PROMPT_LEN = 240
MAX_HINT_LEN = 160
POLL_INTERVAL = 1.0
RETRIES = 2

_workflow_cache: Dict[str, Any] | None = None
_semaphore = asyncio.Semaphore(max(int(getattr(settings, "comfyui_concurrency", 1) or 1), 1))


def _deepcopy_workflow(template: Dict[str, Any]) -> Dict[str, Any]:
    return json.loads(json.dumps(template))


async def _get_latest_dialog(session, user_id: int, persona_id: int) -> Dialog | None:
    res = await session.execute(
        select(Dialog).where(Dialog.user_id == user_id, Dialog.character_id == persona_id).order_by(Dialog.id.desc()).limit(1)
    )
    return res.scalar_one_or_none()


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


def _load_workflow_template() -> Dict[str, Any]:
    """
    Loads and caches workflow JSON template from WORKFLOW_PATH.
    Returns a deep copy every time (safe to mutate).
    """
    global _workflow_cache
    if _workflow_cache is None:
        try:
            _workflow_cache = json.loads(WORKFLOW_PATH.read_text(encoding="utf-8"))
        except FileNotFoundError:
            logger.error("ComfyUI workflow template not found at %s", WORKFLOW_PATH)
            _workflow_cache = {}
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to read workflow template %s: %s", WORKFLOW_PATH, exc)
            _workflow_cache = {}
    return _deepcopy_workflow(_workflow_cache or {})


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


def _apply_template_values(
    template: Dict[str, Any],
    *,
    prompt: str,
    negative_prompt: str,
    config: PersonaImageConfig,
) -> Dict[str, Any]:
    workflow = template

    checkpoint_node_id = find_first_node_id(
        workflow,
        "CheckpointLoaderSimple",
        title_hints=["load checkpoint", "checkpoint"],
    )
    lora_node_id = find_first_node_id(workflow, "LoraLoader", title_hints=["load lora", "lora"])
    sampler_node_id = find_first_node_id(workflow, "KSampler", title_hints=["ksampler", "sampler"])
    positive_clip_id, negative_clip_id = _find_clip_text_nodes(workflow, sampler_node_id)

    missing = [
        name
        for name, value in {
            "checkpoint": checkpoint_node_id,
            "lora": lora_node_id,
            "positive_text": positive_clip_id,
            "negative_text": negative_clip_id,
            "sampler": sampler_node_id,
        }.items()
        if not value
    ]
    if missing:
        raise RuntimeError(f"Workflow template missing nodes: {', '.join(sorted(missing))}")

    checkpoint_inputs = workflow[checkpoint_node_id]["inputs"]
    lora_inputs = workflow[lora_node_id]["inputs"]
    positive_inputs = workflow[positive_clip_id]["inputs"]
    negative_inputs = workflow[negative_clip_id]["inputs"]
    sampler_inputs = workflow[sampler_node_id]["inputs"]

    checkpoint_name = settings.comfyui_default_checkpoint or checkpoint_inputs.get("ckpt_name")
    seed = random.randint(1, 2_000_000_000)

    lora_filename = Path(config.lora_filename).name

    if checkpoint_name:
        checkpoint_inputs["ckpt_name"] = checkpoint_name

    lora_inputs["lora_name"] = lora_filename
    lora_inputs["strength_model"] = float(config.lora_strength_model)
    lora_inputs["strength_clip"] = float(config.lora_strength_clip)

    positive_inputs["text"] = prompt
    negative_inputs["text"] = negative_prompt or DEFAULT_NEGATIVE

    sampler_inputs["seed"] = seed

    logger.info(
        "Workflow nodes ckpt=%s lora=%s pos=%s neg=%s sampler=%s",
        checkpoint_node_id,
        lora_node_id,
        positive_clip_id,
        negative_clip_id,
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
        combined = " ".join(m.replace("\n", " ").replace("\r", " ").strip() for m in messages if m)
        return _trim_hint_text(combined)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to load user request text dialog=%s err=%s", dialog.id if dialog else None, exc)
        return ""


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


def _build_prompt_hint(context: dict[str, Any], persona: Persona | None) -> str:
    story_hint = _build_story_hint_from_ctx(context)
    history_text = context.get("history_text") or ""
    if isinstance(history_text, list):
        history_text = " ".join([str(item) for item in history_text])

    recent_messages = context.get("recent_messages") or ""
    if isinstance(recent_messages, list):
        recent_messages = " ".join([str(item) for item in recent_messages])

    user_request = _trim_hint_text(str(context.get("user_request_text") or ""))

    reply = (context.get("reply_text") or "").strip()
    user_message = (context.get("user_message") or "").strip()

    env_text = _trim_hint_text(story_hint)
    optional_context = _trim_hint_text(str(history_text or recent_messages or ""))

    if not user_request:
        user_request = _trim_hint_text(reply or user_message)

    if not user_request and persona:
        user_request = _trim_hint_text(persona.short_description or persona.name or "")

    segments: list[str] = []
    if env_text:
        segments.append(f"ENVIRONMENT: {env_text}")
    if user_request:
        segments.append(f"USER REQUEST (follow precisely): {user_request}")
    if optional_context:
        segments.append(f"OPTIONAL CONTEXT: {optional_context}")

    hint = ". ".join(part for part in segments if part)
    if len(hint) > MAX_HINT_LEN and optional_context:
        segments = segments[:-1]
        hint = ". ".join(segments)
    if len(hint) > MAX_HINT_LEN and env_text:
        trimmed_env = _trim_hint_text(env_text[: max(20, MAX_HINT_LEN // 2)])
        rebuilt = []
        if trimmed_env:
            rebuilt.append(f"ENVIRONMENT: {trimmed_env}")
        if user_request:
            rebuilt.append(f"USER REQUEST (follow precisely): {user_request}")
        hint = ". ".join(rebuilt)
    if len(hint) > MAX_HINT_LEN:
        hint = hint[:MAX_HINT_LEN]

    preview = hint[:80]
    logger.info(
        "Image hint parts user_req=%s env=%s final_len=%s",
        user_request[:80] if user_request else "",
        env_text[:80] if env_text else "",
        len(hint),
    )
    return hint


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
    timeout = httpx.Timeout(timeout_seconds, connect=10.0)

    logger.info("ComfyUI base_url=%s", base_url)

    async with httpx.AsyncClient(timeout=timeout) as client:
        last_error: Exception | None = None

        for attempt in range(1, RETRIES + 2):
            try:
                payload: Dict[str, Any] = {"prompt": workflow_payload}
                if client_id:
                    payload["client_id"] = client_id

                resp = await client.post(f"{base_url}/prompt", json=payload)
                resp.raise_for_status()

                data = resp.json() or {}
                prompt_id = data.get("prompt_id") or data.get("promptId")
                if not prompt_id:
                    raise RuntimeError(f"No prompt_id in ComfyUI response: {data}")

                image_info = await _wait_for_image(client, base_url, str(prompt_id))
                return await _download_image(client, base_url, image_info)

            except Exception as exc:  # noqa: BLE001
                last_error = exc
                if attempt >= (RETRIES + 1):
                    break
                await asyncio.sleep(1.5 * attempt)

        raise last_error or RuntimeError("Unknown ComfyUI error")


async def _wait_for_image(client: httpx.AsyncClient, base_url: str, prompt_id: str) -> dict:
    deadline = time.monotonic() + float(getattr(settings, "comfyui_timeout_seconds", 90) or 90)

    while time.monotonic() < deadline:
        resp = await client.get(f"{base_url}/history/{prompt_id}")
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

        for node in outputs.values():
            images = node.get("images") or []
            if images:
                return images[0]

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
    resp.raise_for_status()
    return resp.content


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

    template = _load_workflow_template()
    if not template:
        logger.error("Workflow template is empty or missing at %s", WORKFLOW_PATH)
        await _log_failure(plan, "bad_workflow_template")
        return False
    try:
        workflow = _apply_template_values(
            template,
            prompt=plan.prompt,
            negative_prompt=plan.negative_prompt,
            config=plan.config,
        )
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
    logger.info(
        "ComfyUI request user=%s persona=%s ckpt=%s lora=%s strengths=(%.2f/%.2f)",
        plan.user_id,
        plan.persona_id,
        ckpt_name,
        Path(plan.config.lora_filename).name,
        plan.config.lora_strength_model,
        plan.config.lora_strength_clip,
    )

    # Stable-ish client_id helps debugging and history tracking through tunnels.
    client_id = f"vitte-{plan.user_id}-{plan.persona_id}-{uuid.uuid4().hex[:8]}"

    try:
        async with _semaphore:
            image_bytes = await request_comfyui(workflow_payload=workflow, client_id=client_id)
        await _deliver_image(plan, image_bytes, bot_instance)
        return True

    except Exception as exc:  # noqa: BLE001
        logger.error("Image generation/delivery failed user=%s persona=%s: %s", plan.user_id, plan.persona_id, exc)
        await _log_failure(plan, "generation_error")
        return False


async def _generate_image_bytes(plan: GenerationPlan, context: dict[str, Any]) -> bytes:
    base_url = (settings.comfyui_base_url or "").rstrip("/")
    if not base_url:
        await _log_failure(plan, "not_configured")
        raise ImageRequestError("generation_failed")

    template = _load_workflow_template()
    if not template:
        logger.error("Workflow template is empty or missing at %s", WORKFLOW_PATH)
        await _log_failure(plan, "bad_workflow_template")
        raise ImageRequestError("generation_failed")

    try:
        workflow = _apply_template_values(
            template,
            prompt=plan.prompt,
            negative_prompt=plan.negative_prompt,
            config=plan.config,
        )
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
    logger.info(
        "ComfyUI request user=%s persona=%s ckpt=%s lora=%s strengths=(%.2f/%.2f)",
        plan.user_id,
        plan.persona_id,
        ckpt_name,
        Path(plan.config.lora_filename).name,
        plan.config.lora_strength_model,
        plan.config.lora_strength_clip,
    )

    client_id = f"vitte-{plan.user_id}-{plan.persona_id}-{uuid.uuid4().hex[:8]}"

    async with _semaphore:
        try:
            return await request_comfyui(workflow_payload=workflow, client_id=client_id)
        except Exception as exc:  # noqa: BLE001
            logger.error("Image generation failed user=%s persona=%s: %s", plan.user_id, plan.persona_id, exc)
            await _log_failure(plan, "generation_error")
            raise ImageRequestError("generation_failed")


class ImageRequestError(RuntimeError):
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)


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
            hint = _build_prompt_hint(ctx, persona)
            prompt = _build_full_prompt(config, hint)
            negative_prompt = (config.negative_prompt or DEFAULT_NEGATIVE).strip()

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

            image_bytes = await _generate_image_bytes(plan, ctx)
            await _persist_image_usage(session, plan)
            await session.commit()
        finally:
            await _release_advisory_lock(session, lock_key)
        break
    else:
        raise ImageRequestError("not_found")

    await _deliver_image(plan, image_bytes, bot_instance)
