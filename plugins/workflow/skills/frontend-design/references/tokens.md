# Design token floor

Numeric defaults for the quality floor. They are what separates a considered interface from a generated one; they do not decide the look. Palette, typeface and layout stay the brief's choice. If the project already has tokens or a design system, change the tokens there and do not write new raw values.

## Type size
- 3-4 sizes in total, minimum 12px, no fractional values such as 15.5px.
- Build hierarchy with weight, color and spacing before adding another size.
- Line length under 80 characters (see SKILL.md).

## Spacing
- Padding, gap and radius sit on a 4px grid, mostly multiples of 8.

## Radius
- 2-3 steps. Same level, same value. Minimum 4; pills and circles are fully round.
- Nested radius is concentric: `inner = outer - padding` (r = R - p).
- Order from outside in: dialog/card, then panel/input/button, then chip.
- Example: dialog radius 32 with padding 16 gives inner panels and buttons radius 16.
- Continuous (superellipse) corners, progressive enhancement only:
  ```css
  @supports (corner-shape: superellipse(1.25)) {
    :where(*) { corner-shape: superellipse(1.25); }
  }
  /* pills and circles: corner-shape: round */
  ```
  Renders in Chrome/Edge 139+ and falls back to plain border-radius elsewhere. Applying it to the key elements only is enough.

## Lines and borders
- One hairline weight everywhere: 0.5px on high-DPI, a pale 1px on 1x. Never mix thicknesses.

## Color
- UI chrome is white, black and grey; color belongs to photos and content.
- One accent, with its use written down (for example "primary action and selected state only").
- Use a stepped scale with defined roles (Radix Colors' 12 steps: background, subtle background, component states, borders, solid, text). 3-5 distinct hues in total.

## Shadow
- Only for floating layers: menus, dialogs, toasts. Separate cards with a border, not a shadow.

## Buttons
- One primary button per screen.

## Motion
- Little. Default ease-out, 250ms. Never ease-in on entrance.
- Dropdowns and popovers start at scale 0.96; pressed state scales to 0.97.
- Animate transform and opacity. Honor `prefers-reduced-motion`.

## Copy
- Short words that suit the audience. No filler, over-casual phrasing, or coined terms (see the writing section in SKILL.md).
