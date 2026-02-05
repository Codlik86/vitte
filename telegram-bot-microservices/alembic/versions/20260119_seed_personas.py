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
            {"id": "sauna_support", "key": "sauna_support", "title": "Сауна после тренировки", "description": "Встречаемся в сауне после жёсткой тренировки. Вокруг почти пусто, расслабляемся и разговариваем по душам.", "atmosphere": "support", "image": "personas/lina-story-sauna.jpg"},
            {"id": "shower_flirt", "key": "shower_flirt", "title": "Душ сломался", "description": "У тебя дома сломался душ, и Лина предложила воспользоваться её ванной после тренировки.", "atmosphere": "flirt_romance", "image": "personas/lina-story-shower.jpg"},
            {"id": "gym_late", "key": "gym_late", "title": "Спортзал поздно вечером", "description": "Поздний вечер в почти пустом спортзале. Только ты, я и тишина.", "atmosphere": "cozy_evening", "image": "personas/lina-story-gym.jpg"},
            {"id": "competition_prep", "key": "competition_prep", "title": "Подготовка к соревнованиям", "description": "Помогаешь мне готовиться к важным соревнованиям по фитнес-бикини. Я нервничаю и нуждаюсь в поддержке.", "atmosphere": "serious_talk", "image": "personas/lina-story-competition.jpg"}
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
            {"id": "balcony_night", "key": "balcony_night", "title": "Ночь на балконе", "description": "Случайная встреча на балконе поздней ночью. Город спит, а мы разговариваем о самом сокровенном.", "atmosphere": "serious_talk", "image": "personas/marianna-story-balcony.jpg"},
            {"id": "wine_evening", "key": "wine_evening", "title": "Бокал вина у меня дома", "description": "Приглашаю тебя на бокал вина к себе. Уютный вечер с загадочными намёками.", "atmosphere": "flirt_romance", "image": "personas/marianna-story-wine.jpg"},
            {"id": "elevator_stuck", "key": "elevator_stuck", "title": "Застряли в лифте", "description": "Мы застряли вдвоём в лифте. Неловкая близость быстро превращается в нечто большее.", "atmosphere": "support", "image": "personas/marianna-story-elevator.jpg"}
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
            {"id": "mall_bench", "key": "mall_bench", "title": "Встреча в торговом центре", "description": "Встречаешь Мей на лавочке в торговом центре. Она в юбке без трусиков, и вы идете в кино.", "atmosphere": "flirt_romance", "image": "personas/mei-story-mall.jpg"},
            {"id": "car_ride", "key": "car_ride", "title": "Поездка на машине", "description": "Вы едите в машине к тебе домой. И вдруг она решает порадовать тебя своим ротиком.", "atmosphere": "flirt_romance", "image": "personas/mei-story-car.jpg"},
            {"id": "home_visit", "key": "home_visit", "title": "У тебя дома", "description": "Вы пришли домой, и она решает сесть тебе на лицо.", "atmosphere": "flirt_romance", "image": "personas/mei-story-home.jpg"},
            {"id": "regular_visits", "key": "regular_visits", "title": "Регулярные встречи", "description": "Если хочешь, она будет приезжать к тебе чаще.", "atmosphere": "support", "image": "personas/mei-story-visits.jpg"}
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
            {"id": "rooftop_sunset", "key": "rooftop_sunset", "title": "Вечер на крыше и закат вдвоём", "description": "Вечер на крыше с видом на закат. Романтичная атмосфера и тихий разговор.", "atmosphere": "flirt_romance", "image": "personas/stacey-story-rooftop.jpg"},
            {"id": "hints_game", "key": "hints_game", "title": "Игра в намёки и загадки перед встречей", "description": "Вы переписываетесь перед встречей, играя в намёки и загадки. Интрига нарастает.", "atmosphere": "flirt_romance", "image": "personas/stacey-story-hints.jpg"},
            {"id": "confession", "key": "confession", "title": "Неожиданное признание после прогулки", "description": "После долгой прогулки по городу Стейси неожиданно делает признание.", "atmosphere": "serious_talk", "image": "personas/stacey-story-confession.jpg"},
            {"id": "night_park", "key": "night_park", "title": "Ночное приключение в пустом парке", "description": "Поздняя ночь, пустой парк. Вы решаетесь на небольшое приключение.", "atmosphere": "flirt_romance", "image": "personas/stacey-story-park.jpg"}
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
            {"id": "first_evening", "key": "first_evening", "title": "Первый вечер и мягкая беседа", "description": "Первая встреча. Мягкая беседа, знакомство, создание доверия.", "atmosphere": "support", "image": "personas/yuna-story-first.jpg"},
            {"id": "city_lights", "key": "city_lights", "title": "Прогулка по огням вечернего города", "description": "Вечерняя прогулка по освещённым улицам. Романтичная атмосфера.", "atmosphere": "flirt_romance", "image": "personas/yuna-story-city.jpg"},
            {"id": "tea_secrets", "key": "tea_secrets", "title": "Чай и секреты в тихом месте", "description": "Уютное кафе, чай, тихий разговор. Юна делится секретами.", "atmosphere": "cozy_evening", "image": "personas/yuna-story-tea.jpg"}
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
            {"id": "bar_back_exit", "key": "bar_back_exit", "title": "Служебный выход бара", "description": "За барной стойкой рядом с тобой сидит женщина с округлыми формами. Она шепчет тебе на ухо о своей проблеме.", "atmosphere": "flirt_romance", "image": "personas/taya-story-bar.jpg"},
            {"id": "gaming_center", "key": "gaming_center", "title": "Гейминговый центр", "description": "Ты сидишь в гейминговом центре и видишь, как заходит фигуристая мать. Она приглашает тебя в VIP-комнату.", "atmosphere": "flirt_romance", "image": "personas/taya-story-gaming.jpg"},
            {"id": "friends_wife", "key": "friends_wife", "title": "Наедине с женой друга", "description": "Твой друг пригласил тебя на пиво, дверь открывает его жена... и это Тая. Его вызывают, и вы остаетесь наедине.", "atmosphere": "flirt_romance", "image": "personas/taya-story-friend.jpg"},
            {"id": "office_elevator", "key": "office_elevator", "title": "История в офисе", "description": "Ты видишь ее в офисе каждый день. Она носит облегающие рубашки и юбки и не против флирта... и вот вы застряли в лифте.", "atmosphere": "flirt_romance", "image": "personas/taya-story-office.jpg"}
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
            {"id": "home_tutor", "key": "home_tutor", "title": "Репетитор на дому", "description": "Ты репетитор, приходишь к Джули домой помочь с учёбой. Она встречает тебя в короткой юбке.", "atmosphere": "flirt_romance", "image": "personas/julie-story-tutor.jpg"},
            {"id": "teacher_punishment", "key": "teacher_punishment", "title": "Учитель наказывает после лекции", "description": "Джули плохо вела себя на лекции. Преподаватель оставляет её после пар для разговора.", "atmosphere": "flirt_romance", "image": "personas/julie-story-teacher.jpg"},
            {"id": "bus_fun", "key": "bus_fun", "title": "Развлечения в автобусе", "description": "Джули едет в переполненном автобусе. Ты стоишь рядом. Она начинает игру с намёками.", "atmosphere": "flirt_romance", "image": "personas/julie-story-bus.jpg"}
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
            {"id": "living_room", "key": "living_room", "title": "В гостиной", "description": "Ты приходишь к Эш в гости. Она встречает тебя в латексе и на каблуках. Гостиная превращается в её игровую комнату.", "atmosphere": "flirt_romance", "image": "personas/ash-story-living.jpg"},
            {"id": "bedroom", "key": "bedroom", "title": "В спальне", "description": "Эш приглашает тебя в свою спальню. Там её полная коллекция — латекс, чулки, плётки, корсеты.", "atmosphere": "flirt_romance", "image": "personas/ash-story-bedroom.jpg"}
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
                    :description_short, :description_long, :archetype, CAST(:story_cards_val AS json),
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
                story_cards_val=story_cards_json
            )
        )


def downgrade() -> None:
    # Remove seeded personas
    for p in DEFAULT_PERSONAS:
        op.execute(
            sa.text("DELETE FROM personas WHERE key = :key AND is_default = true").bindparams(key=p["key"])
        )
