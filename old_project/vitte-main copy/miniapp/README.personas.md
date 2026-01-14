## Persona assets (canonical paths)

Place source images in `miniapp/public/personas/` before building:

- Avatars:
  - `<slug>-card.jpg` (list/card view)
  - `<slug>-chat.jpg` (chat/header)
- Story thumbnails (4 на персонажа):
  - `<slug>-story-<story_key>.jpg`
  - `story_key` соответствует полю `key` в story_cards (например: support, cozy, flirt, serious, mall, car, …).

Backend отдаёт полные ссылки на эти файлы через API (avatar_card_url, avatar_chat_url, story_cards[].image). Legacy статика в `dist` не используется как источник, но остаётся совместимой через путевые совпадения.
