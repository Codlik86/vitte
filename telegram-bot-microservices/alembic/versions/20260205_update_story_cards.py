"""Update story_cards for all default personas to match stories.py

Revision ID: 018
Revises: 017
Create Date: 2026-02-05

"""
import json
from alembic import op
import sqlalchemy as sa

revision = '018'
down_revision = '017'
branch_labels = None
depends_on = None

UPDATED_STORY_CARDS = {
    "lina": [
        {"id": "sauna_support", "key": "sauna_support", "title": "Сауна после тренировки", "description": "Встречаемся в сауне после жёсткой тренировки. Вокруг почти пусто, расслабляемся и разговариваем по душам.", "atmosphere": "support", "image": "personas/lina-story-sauna.jpg"},
        {"id": "shower_flirt", "key": "shower_flirt", "title": "Душ сломался", "description": "У тебя дома сломался душ, и Лина предложила воспользоваться её ванной после тренировки.", "atmosphere": "flirt_romance", "image": "personas/lina-story-shower.jpg"},
        {"id": "gym_late", "key": "gym_late", "title": "Спортзал поздно вечером", "description": "Поздний вечер в почти пустом спортзале. Только ты, я и тишина.", "atmosphere": "cozy_evening", "image": "personas/lina-story-gym.jpg"},
        {"id": "competition_prep", "key": "competition_prep", "title": "Подготовка к соревнованиям", "description": "Помогаешь мне готовиться к важным соревнованиям по фитнес-бикини. Я нервничаю и нуждаюсь в поддержке.", "atmosphere": "serious_talk", "image": "personas/lina-story-competition.jpg"}
    ],
    "marianna": [
        {"id": "balcony_night", "key": "balcony_night", "title": "Ночь на балконе", "description": "Случайная встреча на балконе поздней ночью. Город спит, а мы разговариваем о самом сокровенном.", "atmosphere": "serious_talk", "image": "personas/marianna-story-balcony.jpg"},
        {"id": "wine_evening", "key": "wine_evening", "title": "Бокал вина у меня дома", "description": "Приглашаю тебя на бокал вина к себе. Уютный вечер с загадочными намёками.", "atmosphere": "flirt_romance", "image": "personas/marianna-story-wine.jpg"},
        {"id": "elevator_stuck", "key": "elevator_stuck", "title": "Застряли в лифте", "description": "Мы застряли вдвоём в лифте. Неловкая близость быстро превращается в нечто большее.", "atmosphere": "support", "image": "personas/marianna-story-elevator.jpg"}
    ],
    "mei": [
        {"id": "mall_bench", "key": "mall_bench", "title": "Встреча в торговом центре", "description": "Встречаешь Мей на лавочке в торговом центре. Она в юбке без трусиков, и вы идете в кино.", "atmosphere": "flirt_romance", "image": "personas/mei-story-mall.jpg"},
        {"id": "car_ride", "key": "car_ride", "title": "Поездка на машине", "description": "Вы едите в машине к тебе домой. И вдруг она решает порадовать тебя своим ротиком.", "atmosphere": "flirt_romance", "image": "personas/mei-story-car.jpg"},
        {"id": "home_visit", "key": "home_visit", "title": "У тебя дома", "description": "Вы пришли домой, и она решает сесть тебе на лицо.", "atmosphere": "flirt_romance", "image": "personas/mei-story-home.jpg"},
        {"id": "regular_visits", "key": "regular_visits", "title": "Регулярные встречи", "description": "Если хочешь, она будет приезжать к тебе чаще.", "atmosphere": "support", "image": "personas/mei-story-visits.jpg"}
    ],
    "stacey": [
        {"id": "rooftop_sunset", "key": "rooftop_sunset", "title": "Вечер на крыше и закат вдвоём", "description": "Вечер на крыше с видом на закат. Романтичная атмосфера и тихий разговор.", "atmosphere": "flirt_romance", "image": "personas/stacey-story-rooftop.jpg"},
        {"id": "hints_game", "key": "hints_game", "title": "Игра в намёки и загадки перед встречей", "description": "Вы переписываетесь перед встречей, играя в намёки и загадки. Интрига нарастает.", "atmosphere": "flirt_romance", "image": "personas/stacey-story-hints.jpg"},
        {"id": "confession", "key": "confession", "title": "Неожиданное признание после прогулки", "description": "После долгой прогулки по городу Стейси неожиданно делает признание.", "atmosphere": "serious_talk", "image": "personas/stacey-story-confession.jpg"},
        {"id": "night_park", "key": "night_park", "title": "Ночное приключение в пустом парке", "description": "Поздняя ночь, пустой парк. Вы решаетесь на небольшое приключение.", "atmosphere": "flirt_romance", "image": "personas/stacey-story-park.jpg"}
    ],
    "yuna": [
        {"id": "first_evening", "key": "first_evening", "title": "Первый вечер и мягкая беседа", "description": "Первая встреча. Мягкая беседа, знакомство, создание доверия.", "atmosphere": "support", "image": "personas/yuna-story-first.jpg"},
        {"id": "city_lights", "key": "city_lights", "title": "Прогулка по огням вечернего города", "description": "Вечерняя прогулка по освещённым улицам. Романтичная атмосфера.", "atmosphere": "flirt_romance", "image": "personas/yuna-story-city.jpg"},
        {"id": "tea_secrets", "key": "tea_secrets", "title": "Чай и секреты в тихом месте", "description": "Уютное кафе, чай, тихий разговор. Юна делится секретами.", "atmosphere": "cozy_evening", "image": "personas/yuna-story-tea.jpg"}
    ],
    "taya": [
        {"id": "bar_back_exit", "key": "bar_back_exit", "title": "Служебный выход бара", "description": "За барной стойкой рядом с тобой сидит женщина с округлыми формами. Она шепчет тебе на ухо о своей проблеме.", "atmosphere": "flirt_romance", "image": "personas/taya-story-bar.jpg"},
        {"id": "gaming_center", "key": "gaming_center", "title": "Гейминговый центр", "description": "Ты сидишь в гейминговом центре и видишь, как заходит фигуристая мать. Она приглашает тебя в VIP-комнату.", "atmosphere": "flirt_romance", "image": "personas/taya-story-gaming.jpg"},
        {"id": "friends_wife", "key": "friends_wife", "title": "Наедине с женой друга", "description": "Твой друг пригласил тебя на пиво, дверь открывает его жена... и это Тая. Его вызывают, и вы остаетесь наедине.", "atmosphere": "flirt_romance", "image": "personas/taya-story-friend.jpg"},
        {"id": "office_elevator", "key": "office_elevator", "title": "История в офисе", "description": "Ты видишь ее в офисе каждый день. Она носит облегающие рубашки и юбки и не против флирта... и вот вы застряли в лифте.", "atmosphere": "flirt_romance", "image": "personas/taya-story-office.jpg"}
    ],
    "julie": [
        {"id": "home_tutor", "key": "home_tutor", "title": "Репетитор на дому", "description": "Ты репетитор, приходишь к Джули домой помочь с учёбой. Она встречает тебя в короткой юбке.", "atmosphere": "flirt_romance", "image": "personas/julie-story-tutor.jpg"},
        {"id": "teacher_punishment", "key": "teacher_punishment", "title": "Учитель наказывает после лекции", "description": "Джули плохо вела себя на лекции. Преподаватель оставляет её после пар для разговора.", "atmosphere": "flirt_romance", "image": "personas/julie-story-teacher.jpg"},
        {"id": "bus_fun", "key": "bus_fun", "title": "Развлечения в автобусе", "description": "Джули едет в переполненном автобусе. Ты стоишь рядом. Она начинает игру с намёками.", "atmosphere": "flirt_romance", "image": "personas/julie-story-bus.jpg"}
    ],
    "ash": [
        {"id": "living_room", "key": "living_room", "title": "В гостиной", "description": "Ты приходишь к Эш в гости. Она встречает тебя в латексе и на каблуках. Гостиная превращается в её игровую комнату.", "atmosphere": "flirt_romance", "image": "personas/ash-story-living.jpg"},
        {"id": "bedroom", "key": "bedroom", "title": "В спальне", "description": "Эш приглашает тебя в свою спальню. Там её полная коллекция — латекс, чулки, плётки, корсеты.", "atmosphere": "flirt_romance", "image": "personas/ash-story-bedroom.jpg"}
    ]
}


def upgrade() -> None:
    conn = op.get_bind()

    for persona_key, cards in UPDATED_STORY_CARDS.items():
        conn.execute(
            sa.text("UPDATE personas SET story_cards = CAST(:cards AS json) WHERE key = :key"),
            {"cards": json.dumps(cards, ensure_ascii=False), "key": persona_key}
        )


def downgrade() -> None:
    # Rollback not needed - old story_cards are outdated placeholders
    pass
