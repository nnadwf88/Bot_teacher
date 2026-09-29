# Дизайн-скиллы для claude.ai

Готовые ZIP-архивы для загрузки в claude.ai (Settings → Capabilities → Skills).

| Архив | Что делает |
|-------|------------|
| `slides.zip` | Презентации в HTML: структуры слайдов, раскладки, тексты, графики Chart.js |
| `ui-ux-pro-max.zip` | База стилей, палитр и шрифтов — подбирает оформление под тему |
| `bencium-impact-designer.zip` | Смелый, «не шаблонный» дизайн страниц и слайдов |
| `ui-typography.zip` | Правильные кавычки, тире, отступы и заголовки |

## Как загрузить

1. Скачайте нужные `.zip` (на GitHub: открыть файл → кнопка **Download raw file**). Распаковывать не нужно.
2. Откройте claude.ai → **Settings** → **Capabilities**.
3. Включите **Code execution and file creation** (без этого скиллы не работают).
4. В разделе **Skills** нажмите **Upload skill** и выберите архив. Повторите для каждого.
5. Проверьте, что у загруженных скиллов включён переключатель.

## Как пользоваться

Пишите в обычном чате, Claude сам подключит нужный скилл:

> Сделай презентацию на 10 слайдов про мой Telegram-бот-учитель. Используй скиллы slides и ui-ux-pro-max.

## Claude Design

Claude Design (claude.ai/design) работает не со скиллами, а с дизайн-системой из ваших материалов бренда.
Чтобы перенести туда стиль: попросите Claude в чате со скиллом `ui-ux-pro-max` составить документ с палитрой
и шрифтами, сохраните его и загрузите в Claude Design при настройке дизайн-системы.

## Источники

- `slides`, `ui-ux-pro-max` — [nextlevelbuilder/ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) (MIT).
  В `slides.zip` добавлены скрипт поиска и данные из скилла `design-system`, чтобы архив работал сам по себе.
- `bencium-impact-designer`, `ui-typography` — [bencium/bencium-marketplace](https://github.com/bencium/bencium-marketplace) (MIT).
