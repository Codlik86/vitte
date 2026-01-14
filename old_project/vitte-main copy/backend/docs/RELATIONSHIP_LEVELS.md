# Relationship Levels (Vitte)

Три уровня:
- **INIT (0)** — мягкий прогрев и лёгкий флирт, без откровенности.
- **FRIENDLY (1)** — открытый тёплый диалог, без лишних отказов, уважение и комфорт.
- **ROMANTIC (2)** — романтика и флирт разрешены, действуй смело, но бережно (safety 18+ всегда активна).

DB source of truth:
- Колонки: `relationship_level SMALLINT`, `manual_override BOOLEAN`, плюс legacy `trust_level/closeness_level/respect_score`.
- Маппинг по умолчанию (когда level нужно пересчитать): INIT → trust=10/closeness=5/respect=0; FRIENDLY → 50/50/0; ROMANTIC → 85/80/0.
- derive_level_from_state читает `relationship_level` если задан, иначе вычисляет по trust/closeness: `>=70 → ROMANTIC`, `>=30 → FRIENDLY`, иначе INIT.
- manual_override=true: авто-переходы и сохранение не выполняются, уровень остаётся тем, что выставил админ.

Переходы (авто):
- INIT → FRIENDLY: после ~20 сообщений в диалоге.
- FRIENDLY → ROMANTIC: если пользователь флиртует/романтичен/просит интим и нет грубости/давления.
- Рудость/давление: уровень не поднимается выше FRIENDLY.

Test mode (`vitte_rel_test_mode=True`):
- Уровень форсируется в ROMANTIC только для промпта, в БД не сохраняется.

Как вручную поставить уровень (пример SQL, при наличии migration):
```sql
UPDATE relationship_states
SET relationship_level=2, manual_override=TRUE, trust_level=85, respect_score=0, closeness_level=80, updated_at=NOW()
WHERE user_id=<uid> AND persona_id=<pid>;

-- Снять override и вернуть авто-поведение:
UPDATE relationship_states
SET manual_override=FALSE
WHERE user_id=<uid> AND persona_id=<pid>;
```

Распределение уровней:
```sql
SELECT relationship_level, COUNT(*) FROM relationship_states GROUP BY relationship_level;
```
