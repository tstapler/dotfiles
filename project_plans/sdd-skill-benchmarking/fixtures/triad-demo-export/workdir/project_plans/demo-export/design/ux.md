# UX: scheduled export

## Flow

1. Admin opens Reports > Usage and clicks "Schedule export".
2. A form asks for frequency (daily, weekly, monthly) and the time of day, then "Create".
3. The new schedule appears in a "Schedules" list with Pause and Delete buttons.
4. Each run adds an entry to an "Exports" list showing date, size and a Download link.

## Screens

- **Schedule form:** frequency select, time-of-day input, Create button.
- **Schedules list:** one row per schedule: frequency, next run, Pause/Delete.
- **Exports list:** one row per export: date, size, Download.

## States

- Schedules list with items: as above.
- Exports list with items: as above.

## Copy

- Button: "Schedule export"
- Success toast: "Schedule created"
