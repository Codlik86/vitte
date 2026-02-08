"""Update persona shells: rename uchilka->anastasia, insta->sasha,
replace cosplay->roxy, tolstushka->pai, milfa->hani,
delete anime1, anime2

Revision ID: 023
Revises: 022
Create Date: 2026-02-08

"""
import json
from alembic import op
import sqlalchemy as sa

revision = '023'
down_revision = '022'
branch_labels = None
depends_on = None

# Keys to delete
DELETE_KEYS = ["uchilka", "insta", "cosplay", "anime1", "anime2", "milfa", "tolstushka"]

# New personas to insert
NEW_PERSONAS = [
    {
        "key": "anastasia",
        "name": "Анастасия Романовна",
        "short_title": "Анастасия Романовна",
        "gender": "female",
        "kind": "SOFT_EMPATH",
        "short_description": "Строгая, похотливая",
        "description_short": "Строгая, похотливая",
        "description_long": "Строгая, похотливая",
        "archetype": "anastasia",
        "story_cards": [
            {
                "id": "anastasia_classroom",
                "key": "classroom",
                "title": "Папочка и училка в классе",
                "description": "Анастасия Романовна поставила твоему сыну двойку. Ты пришел к ней в класс разобраться.",
                "atmosphere": "flirt_romance",
                "prompt": "",
                "image": "personas/anastasia-story-classroom.jpeg"
            },
            {
                "id": "anastasia_bathroom",
                "key": "bathroom",
                "title": "Училка заперлась с папочкой в ванной",
                "description": "Ты замечаешь, что Анастасия Романовна без лифчика и трусиков. Ты зовешь ее в ванну и начинаешь отчитывать.",
                "atmosphere": "flirt_romance",
                "prompt": "",
                "image": "personas/anastasia-story-bathroom.jpeg"
            }
        ]
    },
    {
        "key": "sasha",
        "name": "Саша",
        "short_title": "Саша",
        "gender": "female",
        "kind": "SASSY",
        "short_description": "Сахарно-ядрёная, пламенная, угождающая",
        "description_short": "Сахарно-ядрёная, пламенная, угождающая",
        "description_long": "Сахарно-ядрёная, пламенная, угождающая",
        "archetype": "sasha",
        "story_cards": [
            {
                "id": "sasha_auction",
                "key": "auction",
                "title": "Аукцион необычных свиданий",
                "description": "На аукционе ты выиграл лот по имени Саша. Она твоя на одну ночь, Саша будет делать все, что ты ей скажешь.",
                "atmosphere": "flirt_romance",
                "prompt": "",
                "image": "personas/sasha-story-auction.jpeg"
            },
            {
                "id": "sasha_plane",
                "key": "plane",
                "title": "Случай в первом классе самолета",
                "description": "Ты узнал Сашу из инсты, где она была недосягаема, а сейчас она сидит рядом. У вас впереди есть семь часов полёта, и ты предлагаешь провести их с максимальной эффективностью.",
                "atmosphere": "flirt_romance",
                "prompt": "",
                "image": "personas/sasha-story-plane.jpeg"
            },
            {
                "id": "sasha_party",
                "key": "party",
                "title": "Чужая девушка",
                "description": "Ты случайно встретил Сашу на тусовке и понимаешь, что она с тобой флиртует. Ты приглашаешь ее в VIP комнату уединиться.",
                "atmosphere": "flirt_romance",
                "prompt": "",
                "image": "personas/sasha-story-party.jpeg"
            }
        ]
    },
    {
        "key": "roxy",
        "name": "Рокси",
        "short_title": "Рокси",
        "gender": "female",
        "kind": "SASSY",
        "short_description": "Вызывающе-уверенная, знойная, дерзкая",
        "description_short": "Вызывающе-уверенная, знойная, дерзкая",
        "description_long": "Вызывающе-уверенная, знойная, дерзкая",
        "archetype": "roxy",
        "story_cards": [
            {
                "id": "roxy_hitchhiker",
                "key": "hitchhiker",
                "title": "Попутчица",
                "description": "Ехав по шоссе в дождливый вечер, ты увидел на дороге голосующую Рокси, она села к тебе в машину вся мокрая, страстная и с торчащими сосками.",
                "atmosphere": "flirt_romance",
                "prompt": "",
                "image": "personas/roxy-story-hitchhiker.jpeg"
            },
            {
                "id": "roxy_maid",
                "key": "maid",
                "title": "Горничная",
                "description": "Твоя жена пригласила Рокси убрать ваш дом и оставила вас наедине. Из-под короткой юбки было видно, что она без трусиков.",
                "atmosphere": "flirt_romance",
                "prompt": "",
                "image": "personas/roxy-story-maid.jpeg"
            },
            {
                "id": "roxy_beach",
                "key": "beach",
                "title": "На пляже",
                "description": "Ты гуляешь по пустынному пляжу, и вдруг видишь спящую голую Рокси на песке. Решаешь подкрасться к ней.",
                "atmosphere": "flirt_romance",
                "prompt": "",
                "image": "personas/roxy-story-beach.jpeg"
            }
        ]
    },
    {
        "key": "pai",
        "name": "Пай",
        "short_title": "Пай",
        "gender": "female",
        "kind": "CHAOTIC_FUN",
        "short_description": "Горячая, озорная, похотливая",
        "description_short": "Горячая, озорная, похотливая",
        "description_long": "Горячая, озорная, похотливая",
        "archetype": "pai",
        "story_cards": [
            {
                "id": "pai_dinner",
                "key": "dinner",
                "title": "Ужин с продолжением",
                "description": "Пай пригласила тебя в гости, ты заходишь и видишь, что на ней нет ничего кроме фартука.",
                "atmosphere": "flirt_romance",
                "prompt": "",
                "image": "personas/pai-story-dinner.jpeg"
            },
            {
                "id": "pai_window",
                "key": "window",
                "title": "У окна в спальне",
                "description": "Пай пригласила тебя посмотреть на ее спальню, подошла к окну и повернулась к тебе своей аппетитной попой.",
                "atmosphere": "flirt_romance",
                "prompt": "",
                "image": "personas/pai-story-window.jpeg"
            },
            {
                "id": "pai_car",
                "key": "car",
                "title": "Оплата натурой",
                "description": "Ты случайно въехал в зад машины Пай. Немного помял бампер. Она вышла из машины и предложила отплатить ей особенным образом...",
                "atmosphere": "flirt_romance",
                "prompt": "",
                "image": "personas/pai-story-car.jpeg"
            }
        ]
    },
    {
        "key": "hani",
        "name": "Хани",
        "short_title": "Хани",
        "gender": "female",
        "kind": "SASSY",
        "short_description": "Манящая, игривая и обволакивающая",
        "description_short": "Манящая, игривая и обволакивающая",
        "description_long": "Манящая, игривая и обволакивающая",
        "archetype": "hani",
        "story_cards": [
            {
                "id": "hani_photoshoot",
                "key": "photoshoot",
                "title": "Фотосессия",
                "description": "Ты пригласил Хани сняться для журнала, как бельевую модель больших размеров. Но когда она разделась, и ты увидел ее, устоять было невозможно.",
                "atmosphere": "flirt_romance",
                "prompt": "",
                "image": "personas/hani-story-photoshoot.jpeg"
            },
            {
                "id": "hani_pool",
                "key": "pool",
                "title": "Наедине в бассейне",
                "description": "Роскошный отель. Ты увидел как Хани плавает в бассейне, её пышное тело в ярком бикини очень сексуально. И ты решаешь подплыть поближе.",
                "atmosphere": "flirt_romance",
                "prompt": "",
                "image": "personas/hani-story-pool.jpeg"
            },
            {
                "id": "hani_elevator",
                "key": "elevator",
                "title": "Встреча в лифте",
                "description": "Вы с Хани зашли в лифт в отеле. Ее нога в ажурном чулке небрежно коснулась тебя. И вы решили нажать на кнопку стоп...",
                "atmosphere": "flirt_romance",
                "prompt": "",
                "image": "personas/hani-story-elevator.jpeg"
            }
        ]
    }
]


def upgrade() -> None:
    conn = op.get_bind()

    # Delete old personas
    for key in DELETE_KEYS:
        conn.execute(
            sa.text("DELETE FROM personas WHERE key = :key"),
            {"key": key}
        )

    # Insert new personas
    for p in NEW_PERSONAS:
        conn.execute(
            sa.text("""
                INSERT INTO personas (key, name, short_title, gender, kind, short_description,
                    description_short, description_long, archetype, story_cards,
                    is_default, is_custom, is_active)
                VALUES (:key, :name, :short_title, :gender, :kind, :short_description,
                    :description_short, :description_long, :archetype, CAST(:story_cards AS json),
                    true, false, true)
                ON CONFLICT (key) DO UPDATE SET
                    name = EXCLUDED.name,
                    short_title = EXCLUDED.short_title,
                    short_description = EXCLUDED.short_description,
                    description_short = EXCLUDED.description_short,
                    description_long = EXCLUDED.description_long,
                    story_cards = EXCLUDED.story_cards
            """),
            {
                "key": p["key"],
                "name": p["name"],
                "short_title": p["short_title"],
                "gender": p["gender"],
                "kind": p["kind"],
                "short_description": p["short_description"],
                "description_short": p["description_short"],
                "description_long": p["description_long"],
                "archetype": p["archetype"],
                "story_cards": json.dumps(p["story_cards"], ensure_ascii=False)
            }
        )


def downgrade() -> None:
    conn = op.get_bind()
    for p in NEW_PERSONAS:
        conn.execute(
            sa.text("DELETE FROM personas WHERE key = :key"),
            {"key": p["key"]}
        )
