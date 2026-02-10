"""
Image Prompt Builder for ComfyUI (Z-Image Turbo)

Generates English image prompts from dialog context via LLM.
Structure: trigger_word, LLM-generated scene description

The LLM receives:
- Story scene description (locked from selected story)
- Last few dialog messages for context/mood
- User's current message
And outputs a natural-language English prompt for Z-Image Turbo.
"""

import logging
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)


# Trigger words per persona — exactly as provided, no modifications
PERSONA_TRIGGER_WORDS: Dict[str, str] = {
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


# Scene descriptions extracted from stories for image context
# These map story_key -> English scene description for the image prompt
STORY_SCENE_MAP: Dict[str, Dict[str, str]] = {
    "lina": {
        "sauna_support": "in a sauna after workout, steam and warm lighting, towels, relaxed atmosphere",
        "shower_flirt": "near shower area after swimming pool, wet hair, towel wrapped, water drops",
        "gym_late": "in a gym late at night, dim lighting, workout equipment, empty gym, energetic mood",
        "competition_prep": "personal training session in gym, sporty outfit, exercise equipment, motivational atmosphere",
    },
    "marianna": {
        "support": "in apartment hallway, late evening, dim corridor lighting, mysterious neighbor encounter",
        "cozy": "cozy apartment evening, soft lighting, intimate setting, trust game atmosphere",
        "flirt": "secluded spot outside the city, nature, evening, private outdoor setting, no other people",
        "serious": "adult hotel room, dimly lit, elegant interior, evening atmosphere, private setting",
    },
    "mei": {
        "mall_bench": "sitting on a bench in shopping mall, casual daytime, bright mall lighting",
        "car_ride": "inside a car, passenger seat, night drive, dashboard lights, intimate car atmosphere",
        "home_visit": "at home on a couch, cozy living room, evening, warm home lighting",
        "regular_visits": "comfortable home setting, familiar and warm, casual and relaxed atmosphere",
    },
    "stacey": {
        "rooftop_sunset": "on a rooftop at sunset, golden hour light, city skyline, warm evening glow",
        "hints_game": "playful texting atmosphere, casual indoor setting, teasing mood",
        "confession": "walking together after a stroll, evening city, streetlights, emotional moment",
        "night_park": "in an empty park at night, moonlight, park benches, mysterious and adventurous",
    },
    "yuna": {},
    "taya": {},
    "julie": {
        "home_tutor": "home study session, desk with books, cozy room, student atmosphere",
        "teacher_punishment": "classroom or study room, after lecture, academic setting, tension",
        "bus_fun": "sitting together on a bus, window view, close seats, subtle touches",
    },
    "ash": {
        "living_room": "in a stylish living room, dim lighting, latex outfit, high heels, prepared for special evening",
        "bedroom": "in a bedroom, intimate setting, fetish collection displayed, leather and latex, low lighting",
    },
    "anastasia": {
        "classroom": "in an empty classroom after school, teacher's desk, strict suit, tight skirt, glasses, pointer on desk, confrontational atmosphere",
        "bathroom": "in a bathroom, locked door, steamy mirror, strict teacher without underwear, challenging look over glasses",
    },
    "sasha": {
        "auction": "at a luxury auction event, elegant dress, confident smile, VIP setting, glamorous atmosphere, stage lighting",
        "plane": "in first class airplane seat, luxury cabin, close seating, long flight, intimate enclosed space",
        "party": "in a VIP room at a party, dim lights, loud music behind the door, forbidden flirt, glamorous outfit",
    },
    "roxy": {
        "hitchhiker": "on a rainy highway at night, wet clothes clinging to body, inside a car, foggy windows, provocative atmosphere",
        "maid": "in a house wearing short maid outfit, bending over, no underwear, domestic setting, forbidden flirt",
        "beach": "on a deserted beach, sunny day, dark skin glistening, lying on sand, bold and confident",
    },
    "pai": {
        "dinner": "in a kitchen wearing only an apron, cooking, curvy body visible from behind, cozy home, warm lighting",
        "window": "in a bedroom near a window, curvy figure silhouetted, soft light, provocative pose from behind",
        "car": "at a parking lot near a car, tight dress, curvy figure, playful negotiation atmosphere",
    },
    "hani": {
        "photoshoot": "in a photo studio, soft professional lighting, lingerie model, curvy plus-size body, changing outfits",
        "pool": "in a luxury hotel pool, evening, bright bikini, curvy wet body, water drops, warm pool lighting",
        "elevator": "in a hotel elevator, lace stockings, dress, close space, stopped between floors, intimate tension",
    },
}


# Seeds extracted from original story cover images (ComfyUI KSampler)
# Using story seed keeps generated images visually close to the cover
STORY_SEED_MAP: Dict[str, Dict[str, int]] = {
    "lina": {
        "sauna_support": 656755850281819,
        "shower_flirt": 112315912076405,
        "gym_late": 85003959885866,
        "competition_prep": 192108570398182,
    },
    "marianna": {
        "support": 105221863419341,
        "cozy": 1106517916080220,
        "flirt": 994846394465755,
        "serious": 998993951784854,
    },
    "mei": {
        "mall_bench": 861005257413862,
        "car_ride": 40464755444875,
        "home_visit": 34558265822501,
        "regular_visits": 217474263031081,
    },
    "taya": {
        "bar": 314029085449603,
        "gaming": 355937291397089,
        "friend": 1104607118420134,
        "office": 452099311126967,
    },
    "julie": {
        "home_tutor": 644758794086270,
        "teacher_punishment": 945644158643537,
        "bus_fun": 540285820336111,
    },
    "ash": {
        "living_room": 841674637352483,
        "bedroom": 1102831278917405,
    },
    "anastasia": {
        "classroom": 109031112687797,
        "bathroom": 275706753580744,
    },
    "sasha": {
        "auction": 595699482374484,
        "plane": 884921992830667,
        "party": 410756799592044,
    },
    "roxy": {
        "hitchhiker": 656570736418155,
        "maid": 214062548803426,
        "beach": 1060190116269833,
    },
    "pai": {
        "dinner": 205179185577168,
        "window": 705722453588220,
        "car": 965140167639980,
    },
    "hani": {
        "photoshoot": 113666949531807,
        "pool": 741201838605907,
        "elevator": 442941847325952,
    },
}


def get_story_seed(persona_key: str, story_key: Optional[str]) -> Optional[int]:
    """Get the original cover seed for a story. Returns None if not found."""
    if not story_key:
        return None
    return STORY_SEED_MAP.get(persona_key, {}).get(story_key)


SYSTEM_PROMPT = """You are an image prompt generator for Z-Image Turbo AI model.

Your task: generate a short English image description (40-60 words) based on the dialog context.

RULES:
1. Output ONLY the image description, nothing else. No explanations, no quotes, no prefixes.
2. Write in natural descriptive English, like describing a real photograph.
3. Describe: the woman's pose, expression, clothing/state, setting details, lighting, mood.
4. Capture the emotional atmosphere from the conversation.
5. NSFW/nudity: ONLY describe nudity or explicit body parts if the dialog has clear sexual context (undressing, sex, explicit flirt). If the conversation is casual or just flirty — keep her clothed or in lingerie.
6. Always describe as a single scene with one woman.
7. Use photography terms: shallow depth of field, soft lighting, close-up, etc.
8. NEVER include the trigger word — it will be added separately.
9. NEVER output anything except the image description itself.
10. Prefer STATIC, calm poses — standing, sitting, leaning, lying. Avoid dynamic actions like running, dancing, reaching, grabbing.
11. NEVER describe fingers, hands or feet in detail. Do NOT mention hand interactions with objects (holding glass, touching hair, etc). Hands can be visible but should not be the focus.
12. Focus on: face, eyes, expression, body posture, clothing, atmosphere, lighting."""


def build_image_prompt_messages(
    persona_key: str,
    story_key: Optional[str],
    user_message: str,
    recent_messages: Optional[List[Dict[str, str]]] = None,
) -> List[Dict[str, str]]:
    """
    Build messages array for LLM to generate an image prompt.

    Args:
        persona_key: Persona identifier (lina, ash, etc.)
        story_key: Current story key (sauna_support, bedroom, etc.)
        user_message: Current user message
        recent_messages: Last few dialog messages [{"role": "user/assistant", "content": "..."}]

    Returns:
        Messages array in OpenAI format for LLM call
    """
    # Get scene from story
    scene_description = ""
    if story_key:
        persona_scenes = STORY_SCENE_MAP.get(persona_key, {})
        scene_description = persona_scenes.get(story_key, "")

    # Build context for LLM
    context_parts = []

    if scene_description:
        context_parts.append(f"SCENE SETTING: {scene_description}")

    # Add last 4 messages for mood context
    if recent_messages:
        last_messages = recent_messages[-4:]
        dialog_lines = []
        for msg in last_messages:
            role = "User" if msg.get("role") == "user" else "Her"
            content = msg.get("content", "")[:150]
            dialog_lines.append(f"{role}: {content}")
        context_parts.append("RECENT DIALOG:\n" + "\n".join(dialog_lines))

    context_parts.append(f"CURRENT USER MESSAGE: {user_message}")

    user_content = "\n\n".join(context_parts)

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]


def assemble_final_prompt(persona_key: str, llm_output: str) -> str:
    """
    Assemble the final ComfyUI prompt: trigger_word, llm_description

    Args:
        persona_key: Persona identifier
        llm_output: Raw LLM output (scene description)

    Returns:
        Final prompt string for ComfyUI
    """
    trigger_word = PERSONA_TRIGGER_WORDS.get(persona_key, "")

    # Clean LLM output
    description = llm_output.strip()
    # Remove quotes if LLM wrapped output in them
    if description.startswith('"') and description.endswith('"'):
        description = description[1:-1].strip()
    if description.startswith("'") and description.endswith("'"):
        description = description[1:-1].strip()

    # Append anatomy/quality tags to reduce artifacts
    quality_suffix = "perfect anatomy, correct hands, five fingers, photorealistic"

    if trigger_word:
        return f"{trigger_word}, {description}, {quality_suffix}"
    else:
        return f"{description}, {quality_suffix}"


__all__ = [
    "PERSONA_TRIGGER_WORDS",
    "STORY_SCENE_MAP",
    "STORY_SEED_MAP",
    "get_story_seed",
    "build_image_prompt_messages",
    "assemble_final_prompt",
]
