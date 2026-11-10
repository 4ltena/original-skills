# Component techniques

Load only when the work includes the component. Values are starting points to tune by eye.

## Raised button
Neutral grey, light from directly above.
- Background: 180-degree gradient, top 6-8% lighter.
- `box-shadow` layers: `inset 0 1px 0` white highlight, `inset 0 -1px 0` black shade, then two outer shadows (`0 1px 2px`, `0 4px 10px -3px`). Put the insets in `box-shadow`, not a pseudo-element.
- Pressed: `translateY(1px)` and a smaller shadow.
- Transitions: transform 120ms, shadow 140ms, color 160ms.
- 14px label: height 40, horizontal padding 18, radius 10, weight 600.

## Cascading menu
- Safe triangle: ignore row changes while the cursor travels inside the triangle between its last position and the submenu's top and bottom edges.
- Open after 220ms, close after 360ms.
- Roles `menu`/`menuitem`, `aria-expanded`, full keyboard support.

## Drag-to-reorder
- Items around the insertion line shift: displacement 10px x 0.7^n, delay 24ms x n, spring of about 0.25s.

## Generated icons
- No piled-on highlights or shadows. Background is a linear gradient of one hue at different lightness. Shadow is a dark tone of a nearby hue, not black.
- Match stroke weight and visual mass across the set.

## Dark mode
- Fit the content's context rather than a plain toggle (a night itinerary darkens the whole screen and its map).

## Parts and materials
Prefer ready-made parts to hand-built ones: Radix Colors, Radix/shadcn-style components, Remix Icon, React Bits (motion), The Shape of AI (AI UX patterns). Materials: Coolors (palette), Fontshare (type), The Noun Project (icons), Blush (illustration), Unsplash (photos), CTA Gallery (CTA copy).

External design skills (suggest only when useful, never install unasked): UI UX Pro Max when style is undecided; Taste Skill for originality; Impeccable and Emil Kowalski Skills for polishing existing work; Hallmark to restyle without breaking features; kill-ai-slop to strip slop.
