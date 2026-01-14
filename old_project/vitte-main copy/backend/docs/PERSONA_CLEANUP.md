# Persona Cleanup (2025-01-07)

Удалённые персонажи:
- Эва (`witty_bold_female`)
- Фэй (`chaotic_fun_female`)
- Арина (`therapeutic_female`)
- Хана (`anime_waifu_soft_female`)
- Аки (`anime_tsundere_female`)

Оставшиеся: Лина, Марианна, Мей, Стейси, Тая.

Миграция:
- Применить Alembic:
  ```bash
  cd backend
  alembic upgrade head
  ```
- Или SQL вручную (идемпотентно):
  ```sql
  WITH ids AS (SELECT id FROM personas WHERE key = ANY(ARRAY[
      'witty_bold_female','chaotic_fun_female','therapeutic_female','anime_waifu_soft_female','anime_tsundere_female'
  ]))
  DELETE FROM user_personas WHERE persona_id IN (SELECT id FROM ids);
  WITH ids AS (SELECT id FROM personas WHERE key = ANY(ARRAY[
      'witty_bold_female','chaotic_fun_female','therapeutic_female','anime_waifu_soft_female','anime_tsundere_female'
  ]))
  DELETE FROM relationship_states WHERE persona_id IN (SELECT id FROM ids);
  WITH ids AS (SELECT id FROM personas WHERE key = ANY(ARRAY[
      'witty_bold_female','chaotic_fun_female','therapeutic_female','anime_waifu_soft_female','anime_tsundere_female'
  ]))
  DELETE FROM dialogs WHERE character_id IN (SELECT id FROM ids);
  WITH ids AS (SELECT id FROM personas WHERE key = ANY(ARRAY[
      'witty_bold_female','chaotic_fun_female','therapeutic_female','anime_waifu_soft_female','anime_tsundere_female'
  ]))
  DELETE FROM events_personas WHERE persona_id IN (SELECT id FROM ids);
  WITH ids AS (SELECT id FROM personas WHERE key = ANY(ARRAY[
      'witty_bold_female','chaotic_fun_female','therapeutic_female','anime_waifu_soft_female','anime_tsundere_female'
  ]))
  DELETE FROM personas WHERE id IN (SELECT id FROM ids);
  ```

Проверки (должно быть 0 строк):
```sql
SELECT key,name FROM personas ORDER BY id;
SELECT COUNT(*) FROM dialogs WHERE character_id IN (
  SELECT id FROM personas WHERE key IN (
    'witty_bold_female','chaotic_fun_female','therapeutic_female','anime_waifu_soft_female','anime_tsundere_female'
  )
);
SELECT COUNT(*) FROM relationship_states WHERE persona_id IN (
  SELECT id FROM personas WHERE key IN (
    'witty_bold_female','chaotic_fun_female','therapeutic_female','anime_waifu_soft_female','anime_tsundere_female'
  )
);
SELECT COUNT(*) FROM user_personas WHERE persona_id IN (
  SELECT id FROM personas WHERE key IN (
    'witty_bold_female','chaotic_fun_female','therapeutic_female','anime_waifu_soft_female','anime_tsundere_female'
  )
);
```
