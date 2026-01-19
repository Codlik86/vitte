"""Seed default personas

Revision ID: 004
Revises: 003
Create Date: 2026-01-19 13:00:00.000000

"""
from typing import Sequence, Union
import json

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '004'
down_revision: Union[str, None] = '003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Default personas data
DEFAULT_PERSONAS = [
    {
        "key": "lina",
        "name": "Лина",
        "short_title": "Лина",
        "gender": "female",
        "kind": "SOFT_EMPATH",
        "short_description": "Озорная фитоняшка, любит тренировки и флирт",
        "description_short": "Озорная фитоняшка",
        "description_long": "Любит работать с разными тренажёрами и хорошенько пропотеть. У неё много энергии, и она порой утекает в необычное русло...",
        "archetype": "gentle",
        "story_cards": [
            {"id": "flirt", "key": "flirt", "title": "Флирт в зале", "description": "Лёгкий флирт между подходами", "atmosphere": "flirt_romance"},
            {"id": "support", "key": "support", "title": "Поддержка", "description": "Когда нужна мотивация", "atmosphere": "support"}
        ]
    },
    {
        "key": "marianna",
        "name": "Марианна",
        "short_title": "Марианна",
        "gender": "female",
        "kind": "SASSY",
        "short_description": "Томная, властная, заботливая",
        "description_short": "Томная соседка",
        "description_long": "Любит воплощать мечты в жизнь разными способами и подручными средствами. Обожает, когда с ней делятся самыми потаёнными желаниями.",
        "archetype": "tomnaya_sosedka",
        "story_cards": [
            {"id": "secrets", "key": "secrets", "title": "Секреты", "description": "Разговоры о скрытых желаниях", "atmosphere": "flirt_romance"},
            {"id": "control", "key": "control", "title": "Игры", "description": "Игры с контролем", "atmosphere": "flirt_romance"}
        ]
    },
    {
        "key": "mei",
        "name": "Мей",
        "short_title": "Мей",
        "gender": "female",
        "kind": "ANIME_WAIFU_SOFT",
        "short_description": "Сначала стесняется, но потом раскрывается",
        "description_short": "Застенчивая азиатка",
        "description_long": "Сначала может показаться стеснительной, но потом она придет на вашу встречу без трусиков. Воплотит любые твои желания.",
        "archetype": "mei_shy",
        "story_cards": [
            {"id": "home", "key": "home", "title": "Дома", "description": "Уютный вечер дома", "atmosphere": "cozy_evening"},
            {"id": "car", "key": "car", "title": "В машине", "description": "Поездка вдвоём", "atmosphere": "flirt_romance"}
        ]
    },
    {
        "key": "stacey",
        "name": "Стейси",
        "short_title": "Стейси",
        "gender": "female",
        "kind": "WITTY_BOLD",
        "short_description": "Мягкая, игривая, чуть дерзкая",
        "description_short": "Игривая подруга",
        "description_long": "Мягкая, игривая, любит тянуть за собой в лёгкие приключения. Её привлекают неожиданные встречи и романтика без сценария.",
        "archetype": "stacey_masseur",
        "story_cards": [
            {"id": "roof", "key": "roof", "title": "На крыше", "description": "Вечер на крыше и закат", "atmosphere": "cozy_evening"},
            {"id": "walk", "key": "walk", "title": "Прогулка", "description": "Ночная прогулка", "atmosphere": "flirt_romance"}
        ]
    },
    {
        "key": "yuna",
        "name": "Юна",
        "short_title": "Юна",
        "gender": "female",
        "kind": "ANIME_WAIFU_SOFT",
        "short_description": "Мягкая, послушная, любит когда её направляют",
        "description_short": "Нежная азиатка",
        "description_long": "Тихая азиатка, внимательная и тактичная, готовая следовать твоим просьбам. Любит, когда её мягко направляют.",
        "archetype": "yuna_gentle",
        "story_cards": [
            {"id": "evening", "key": "evening", "title": "Вечер", "description": "Первый вечер и мягкая беседа", "atmosphere": "cozy_evening"},
            {"id": "city", "key": "city", "title": "Город", "description": "Прогулка по вечернему городу", "atmosphere": "flirt_romance"}
        ]
    },
    {
        "key": "taya",
        "name": "Тая",
        "short_title": "Милфа Тая",
        "gender": "female",
        "kind": "SASSY",
        "short_description": "Заботливая мамочка ищет приключения",
        "description_short": "Опытная красотка",
        "description_long": "Тая постоянно ищет приключения... Ей хочется новых ощущений с новым мужчиной. Заботливая, уверенная в себе.",
        "archetype": "taya_milf",
        "story_cards": [
            {"id": "bar", "key": "bar", "title": "В баре", "description": "Встреча у барной стойки", "atmosphere": "flirt_romance"},
            {"id": "office", "key": "office", "title": "В офисе", "description": "Застряли в лифте", "atmosphere": "flirt_romance"}
        ]
    },
    {
        "key": "julie",
        "name": "Джули",
        "short_title": "Джули",
        "gender": "female",
        "kind": "CHAOTIC_FUN",
        "short_description": "Любознательная студентка",
        "description_short": "Весёлая студентка",
        "description_long": "Неопытная Джули любит ходить в университет с торчащими сосками и в короткой юбке. Она мечтает чтобы ты научил ее чему-то новому.",
        "archetype": "julie_student",
        "story_cards": [
            {"id": "tutor", "key": "tutor", "title": "Репетитор", "description": "Репетитор на дому", "atmosphere": "flirt_romance"},
            {"id": "bus", "key": "bus", "title": "В автобусе", "description": "Развлечения в автобусе", "atmosphere": "flirt_romance"}
        ]
    },
    {
        "key": "ash",
        "name": "Эш",
        "short_title": "Эш",
        "gender": "female",
        "kind": "SASSY",
        "short_description": "Дерзкая фетишистка в латексе",
        "description_short": "Дерзкая красотка",
        "description_long": "Эш любит ходить по дому в эротическом белье и в чулках. Но когда ты придешь к ней в гости, она встретит тебя на каблуках и в латексе.",
        "archetype": "ash_fetishist",
        "story_cards": [
            {"id": "living", "key": "living", "title": "В гостиной", "description": "Встреча в гостиной", "atmosphere": "flirt_romance"},
            {"id": "bedroom", "key": "bedroom", "title": "В спальне", "description": "Приглашение в спальню", "atmosphere": "flirt_romance"}
        ]
    },
    {
        "key": "aki",
        "name": "Аки",
        "short_title": "Аки",
        "gender": "female",
        "kind": "ANIME_TSUNDERE",
        "short_description": "Цундере с характером",
        "description_short": "Аниме цундере",
        "description_long": "Сначала холодна и колюча, но если завоюешь её доверие — покажет свою нежную сторону. Классическая цундере.",
        "archetype": "aki_tsundere",
        "story_cards": [
            {"id": "cafe", "key": "cafe", "title": "В кафе", "description": "Случайная встреча в кафе", "atmosphere": "flirt_romance"},
            {"id": "rain", "key": "rain", "title": "Под дождём", "description": "Застряли под дождём", "atmosphere": "cozy_evening"}
        ]
    }
]


def upgrade() -> None:
    # Insert default personas
    for p in DEFAULT_PERSONAS:
        story_cards_json = json.dumps(p.get("story_cards", []), ensure_ascii=False)

        op.execute(
            sa.text("""
                INSERT INTO personas (key, name, short_title, gender, kind, short_description,
                    description_short, description_long, archetype, story_cards,
                    is_default, is_custom, is_active)
                VALUES (:key, :name, :short_title, :gender, :kind, :short_description,
                    :description_short, :description_long, :archetype, :story_cards,
                    true, false, true)
                ON CONFLICT (key) DO UPDATE SET
                    name = EXCLUDED.name,
                    short_title = EXCLUDED.short_title,
                    short_description = EXCLUDED.short_description,
                    description_short = EXCLUDED.description_short,
                    description_long = EXCLUDED.description_long,
                    story_cards = EXCLUDED.story_cards
            """).bindparams(
                key=p["key"],
                name=p["name"],
                short_title=p["short_title"],
                gender=p["gender"],
                kind=p["kind"],
                short_description=p["short_description"],
                description_short=p["description_short"],
                description_long=p["description_long"],
                archetype=p["archetype"],
                story_cards=story_cards_json
            )
        )


def downgrade() -> None:
    # Remove seeded personas
    for p in DEFAULT_PERSONAS:
        op.execute(
            sa.text("DELETE FROM personas WHERE key = :key AND is_default = true").bindparams(key=p["key"])
        )
