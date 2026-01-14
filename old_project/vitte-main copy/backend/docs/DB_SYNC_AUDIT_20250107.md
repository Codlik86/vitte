# DB Sync Audit (Relationships & Image/Text Pipelines) — 2025-01-07

## 1) Current DB schema (fact)
- `relationship_states` (created lazily in `services/relationship_state.py:_ensure_table`):
  - Columns: `id SERIAL PK`, `user_id INTEGER FK users(id)`, `persona_id INTEGER FK personas(id)`, `trust_level INTEGER NOT NULL DEFAULT 10`, `respect_score INTEGER NOT NULL DEFAULT 0`, `closeness_level INTEGER NOT NULL DEFAULT 5`, `updated_at TIMESTAMP`.
  - Unique constraint on `(user_id, persona_id)` via `ON CONFLICT` UPSERT.
  - No dedicated `relationship_level` column.
- `users`: fields used for counts/transitions: `bot_reply_counter` (increments per assistant reply in `chat_flow.generate_chat_reply`), `free_messages_used`, `last_image_sent_at`.
- `dialogs`: link user/persona, stores `entry_story_id` (for story_cards).
- `messages`: stores dialog history (role/content) used for message_count, recent_dialogue, history for image prompt/user intent.
- `events_analytics`: used for image events, not affecting relationship levels.
- `image_balance`: quotas, unrelated to relationship levels.

## 2) Current write paths & overwrite risks
- Relationship load: `chat_flow.generate_chat_reply` creates task `get_relationship_state`.
- Update path: `generate_chat_reply` computes `target_level` (derived from trust/closeness via `derive_level_from_state`) and transitions via `transition_level` (message_count + analysis). Then `level_to_state` maps level back to trust/closeness values. Persisted via `save_relationship_state` (UPSERT) unless test mode or preview_story.
- Test mode (`vitte_rel_test_mode`): forces level ROMANTIC for prompt, skips persistence (no DB overwrite).
- Old trust ladder text removed from prompt; deltas via `update_relationship_state` no longer used for level (only `level_to_state` values are written).
- Overwrite risk: any admin SQL override of trust/closeness will be remapped on next message by transition rules (no manual override flag). Also, `_get_relationship_state` default values may overwrite missing rows on first save.

## 3) Current level logic (fact)
- Level derivation: `derive_level_from_state` (relationship_state.py): ROMANTIC if trust>=70 or closeness>=70; FRIENDLY if trust>=30 or closeness>=30; else INIT.
- Transitions: `transition_level`:
  - INIT→FRIENDLY if `message_count >= 20` (dialog messages counted in `chat_flow`).
  - FRIENDLY→ROMANTIC if analysis.is_flirty or is_romantic or asks_for_intimacy and not (is_rude or is_pushy).
  - If rude/pushy → cap at FRIENDLY (cannot go ROMANTIC).
- Stored state: `save_relationship_state` writes trust/respect/closeness derived from target level via `level_to_state` (INIT: 10/5/0, FRIENDLY: 50/50/0, ROMANTIC: 85/80/0).
- Admin override risk: manual trust/closeness edits will be re-derived to a level on next message and overwritten to canonical level values (no protection).

## 4) Recommendation: A (relationship_level column) vs B (mapping)
- Current state = B (mapping trust/closeness → level). Drawback: admin overrides on trust/closeness get normalized by auto-logic, hard to maintain “manual level”.
- Recommended path: **A** — add explicit `relationship_level SMALLINT` with default INIT, keep trust/closeness as legacy/derived. Pros: observable and manually settable; easier to bypass auto-transition when manually fixed. Cons: migration needed.

## 5) Migration + Backfill plan (if A) / Hardening plan (if B)
### If A (preferred):
1. Migration:
   ```sql
   ALTER TABLE relationship_states ADD COLUMN IF NOT EXISTS relationship_level SMALLINT DEFAULT 0;
   CREATE INDEX IF NOT EXISTS idx_relationship_states_level ON relationship_states(relationship_level);
   ```
2. Backfill:
   ```sql
   UPDATE relationship_states
   SET relationship_level = CASE
       WHEN trust_level >= 70 OR closeness_level >= 70 THEN 2
       WHEN trust_level >= 30 OR closeness_level >= 30 THEN 1
       ELSE 0
   END
   WHERE relationship_level IS NULL OR relationship_level NOT IN (0,1,2);
   ```
   - For missing rows: no backfill needed; runtime creates defaults (INIT) on first write.
3. Code changes (later, not now): read/write relationship_level as source of truth; only derive trust/closeness from level; allow manual override by respecting stored level and skipping auto-transition if a manual flag set (could be another column or policy).

### If staying on B (current):
- Hardening options:
  - Introduce a manual_override flag (new column) to skip auto-transition when set.
  - Alternatively, policy “do not downshift” and “respect admin level if trust/closeness above canonical thresholds”.
  - Document canonical trust/closeness per level and instruct admins to use those exact values to avoid drift.

## 6) Validation checklist
- SQL checks:
  - Distribution of levels (mapping) per persona/user:
    ```sql
    SELECT
      SUM(CASE WHEN trust_level>=70 OR closeness_level>=70 THEN 1 ELSE 0 END) AS romantic,
      SUM(CASE WHEN trust_level>=30 OR closeness_level>=30 AND NOT (trust_level>=70 OR closeness_level>=70) THEN 1 ELSE 0 END) AS friendly,
      SUM(CASE WHEN trust_level<30 AND closeness_level<30 THEN 1 ELSE 0 END) AS init
    FROM relationship_states;
    ```
  - Missing rows:
    ```sql
    SELECT user_id, persona_id FROM dialogs d
    WHERE NOT EXISTS (
      SELECT 1 FROM relationship_states r WHERE r.user_id=d.user_id AND r.persona_id=d.persona_id
    );
    ```
  - Stuck INIT with high message count:
    ```sql
    SELECT u.id, d.id AS dialog_id, COUNT(m.id) AS msg_cnt, r.trust_level, r.closeness_level
    FROM dialogs d
    JOIN users u ON u.id=d.user_id
    LEFT JOIN messages m ON m.dialog_id=d.id
    LEFT JOIN relationship_states r ON r.user_id=d.user_id AND r.persona_id=d.character_id
    GROUP BY u.id, d.id, r.trust_level, r.closeness_level
    HAVING COUNT(m.id) > 40 AND (r.trust_level < 30 AND r.closeness_level < 30);
    ```
  - ROMANTIC with 0 messages:
    ```sql
    SELECT u.id, d.id AS dialog_id, COUNT(m.id) AS msg_cnt, r.trust_level, r.closeness_level
    FROM dialogs d
    JOIN users u ON u.id=d.user_id
    LEFT JOIN messages m ON m.dialog_id=d.id
    LEFT JOIN relationship_states r ON r.user_id=d.user_id AND r.persona_id=d.character_id
    GROUP BY u.id, d.id, r.trust_level, r.closeness_level
    HAVING COUNT(m.id) = 0 AND (r.trust_level >= 70 OR r.closeness_level >= 70);
    ```
- Runtime checks:
  - Logs: ensure no “REL_TEST_MODE enabled” unless intentionally set; observe `relationship level` log in prompt (system prompt via prompt_builder).
  - Scenarios in Telegram:
    1) INIT→FRIENDLY: 25 обычных сообщений, уровень должен стать FRIENDLY (mapped to trust≈50).
    2) FRIENDLY→ROMANTIC: флирт/романтика, без грубости → ROMANTIC.
    3) Admin override: вручную ставим ROMANTIC (trust=85/closeness=80); отправляем 1 сообщение — не должно откатиться (if A with level column) / при B — рискует быть нормализовано.
    4) Test mode on: уровень форс ROMANTIC в промпте, БД не трогается.
    5) Токсичный кейс: грубость/давление — уровень не поднимается выше FRIENDLY.

## 7) Change touchpoints (for future code changes, не делать сейчас)
- `services/relationship_state.py`: switch to relationship_level column if adopting A; add manual_override flag/logic if staying B.
- `services/chat_flow.py`: read/write level as source of truth; skip auto-transition when manual_override.
- `services/prompt_builder.py` and `llm_adapter.py`: continue using relationship_level text block; keep safety block intact.
- Admin tools/SQL snippets: for manual overrides and inspection.
