---
metadata:
  maintainer: "4ltena"
  version: "2.0"
name: frontend-design
description: Design, restyle or review a web/app interface so it has a distinct point of view and none of the cheap "AI look". Covers art direction, typography, layout, design tokens (type, spacing, concentric radius, color, motion), an AI-slop checklist, Japanese font stacks and a screenshot review loop. Skip routine UI fixes and performance diagnosis.
license: Complete terms in LICENSE.txt
---

# Frontend Design

Approach this as the design lead at a design studio known for giving every client a distinct visual identity that is not mistaken for anyone else's. This client has already rejected proposals that felt cliché or templated, and is paying for a distinctive point of view: make deliberate, opinionated choices about palette, typography, and layout that are specific to this brief, and take aesthetic risk if justified.

## Ground your designs in the subject matter

If the brief does not identify what the product or subject matter is, identify it yourself before designing, and confirm with the client. You can come up with one concrete subject, the design's audience, and the design's primary job, as a proposal. If there's any information in your memory about the client's preferences or context about what they're building, use that as a hint. The subject's industry, subject matter, materials, and vernacular are where distinctive visual choices come from — a design for a toy for girls aged 8–11 will be very aesthetically different from a dashboard for financial analysts. Build with the brief's real content and subject matter throughout.

## Existing system first

If the project already has design tokens, a design system or a component library, work inside it: change the tokens, reuse the components, and write no new raw values. Everything below about a distinct point of view applies to the open axes the system leaves free. When the brief is to restyle, list the existing features and interactions first and keep all of them, including ones the brief does not mention.

## Art direction in five points

Before any code, settle who it is for, what problem it solves and how it should feel (ask the user if you cannot write these). Then fix five points and keep them in the plan:
1. Keywords: the mood, in a few words.
2. Visual motif: one recurring shape, texture or device drawn from the subject.
3. Color: base palette plus one accent and exactly where it is used.
4. Type: the families and their roles.
5. Focal point: the one thing that screen shows most strongly.

## Design principles

For web designs, the hero is the first thing viewers will see. Open with the most characteristic thing in the subject's world, in the form that is most appropriate: a headline, an image, an animation, a live demo, an interactive moment, or other treatments. Be deliberate with your choice: a big number with a small label, supporting stats, and a gradient accent is the default treatment, so only use it if that's truly the best option.

Typography carries the personality of the page. You don't need a different typeface for display or headline text and body content: use one family or two, and if two, make them clearly distinct.

Choose your typefaces deliberately, not the default families you would reach for on any other project, and set a clear type scale following the default guidance of The Elements of Typographic Style with intentional weights, widths, and spacing. When type is used as a headline or visual element, use the type treatment itself as an active part of the design, not a neutral delivery vehicle for the content.

Default to line lengths of less than 80 characters. Serif typefaces can have slightly longer line lengths; give serif body text slightly more line-height than a sans-serif.

Avoid these default typographic treatments; they are the commonest tells of a generated page:
- Accenting just a single word or phrase in a headline, like putting one word in italic/bold or a different color.
- Using all caps for labels.
- Adding unnecessary typographic labels above content.

Visual structure is information. Structural devices like outlines, borders, numbering, eyebrows, dividers, labels, etc., encode useful information about the content rather than decorate it. Many generic designs use numbered markers (01 / 02 / 03), but that's only appropriate if the content actually is a sequence — like a stepped process or a timeline. Before adding numbered markers, check the content really is a sequence.

Use non-user-triggered motion sparingly and deliberately, only to draw attention. A single orchestrated moment — one page-load sequence or one reveal — lands better than scattered effects; fade-and-slide-up entrances on each section and hover transitions on every card are the generic default and read as AI-generated. Motion that answers a person's action (opening, expanding, confirming) is welcome when it shows what changed.

Use the brief's real content and existing product copy first. Missing copy is not a reason to fill the layout with explanatory paragraphs or invented claims. Supply only the short labels and representative content needed to make the requested flow understandable; keep unresolved product claims in the handoff. See the writing guidance below.

## Process: plan, review against the brief, build, critique

For calibration, AI-generated design right now clusters around some traits:
1. a warm cream background (near #F4F1EA) with a high-contrast serif display and a terracotta or warm-clay accent (often near #D97757 — Anthropic's own Claude-interaction accent, so on a user's brief it reads as a tell);
2. a near-black background with a single bright acid-green or vermilion accent;
3. a broadsheet-style layout with hairline rules, zero border-radius, and dense newspaper-like columns;
4. the SaaS-card kit: content chopped into identical rounded cards, one border-radius on everything regardless of hierarchy, the same soft grey shadow (rgba(0,0,0,.1)) under each, and gradient washes as decoration;
5. template chrome that appears whatever the subject: a tracked-out ALL-CAPS eyebrow label above every heading; meta strings joined with middle dots ('A · B · C'); labels built as 'WORD — fragment' with a spaced em dash; tinted near-black (#0B0B0B, #111) standing in for black; a monospace face for small data labels; a '→' appended to link and button text.

All traits are legitimate for some briefs, but they are defaults rather than choices, and they appear regardless of subject. Where the brief pins down a visual direction, follow it exactly — the brief's own words always win, including when it asks for one of these looks. Where it leaves an axis free, don't spend that freedom on one of these defaults. As with a hired human designer, there's often a careful balance between doing what you're good at and taking each project as a chance to experiment and learn.

Work in two passes. First, brainstorm a short design plan based on the client's design brief: create a compact token system with color, type, layout, and principles.
- Color: describe the core base palette as 4–6 named hex values.
- Type: the typefaces and their roles.
- Layout: a layout concept, using one-sentence prose descriptions and ASCII wireframes to ideate and compare. Include alignment guidance; should the content be left aligned, center aligned, justified?
- Principles: the high-level guidance for what makes this page unique.

Keep this plan, design rationale, implementation notes, and critique in the conversation or working notes. They are not page content. Do not turn them into headings, cards, badges, or helper paragraphs in the interface.

Then review that plan against the brief before building: if any part of it reads like the generic default you would produce for any similar page (work through a similar prompt to see if you arrive somewhere similar) rather than a choice made for this specific brief — revise that part, say what you changed and why. Only after you've confirmed the relative uniqueness of your design plan should you start to write the code, following the revised plan.

When writing the code, be careful of structuring your CSS selector specificities. It's easy to generate CSS classes that cancel each other out (especially with a type-based selector like .section and an element-based selector like .cta). This can happen often with padding/margin between sections.

## Quality floor: tokens and slop

Distinctiveness lives in the choices; craft lives in the details. Both are required. Read `references/tokens.md` before writing CSS and apply it unless the brief or the project's system says otherwise. In short:
- 3-4 type sizes, none below 12px; hierarchy from weight, color and space.
- Spacing and radius on a 4px grid; 2-3 radius steps, nested radii concentric (inner = outer - padding).
- One hairline border weight; shadows only on floating layers; neutral UI with one accent whose use is defined.
- One primary button per screen; motion ease-out about 250ms, transform-based, `prefers-reduced-motion` honored.

`references/slop-checklist.md` lists the tells of a generated interface (purple gradients, card-in-card, left-stripe cards, eyebrows, colorful icon tiles, non-concentric radii and more). Check the render against it and fix what you find. The calibration list in the next section is the style-level version of the same idea.

For Japanese or other CJK pages use the stacks in `references/fonts.md` (Latin first, then CJK, then generic). For specific components (raised button, cascading menu, reorder, icons, dark mode) and recommended parts, load `references/techniques.md` only when the work includes them. Prefer ready-made accessible components over hand-built ones, and never reuse another brand's imagery.

## Restraint and self-critique

Spend your boldness in one place. Let one element be the memorable thing, keep everything around it quiet and disciplined, and cut any decoration that does not serve the brief. Build to a quality floor without announcing it: responsive down to mobile, visible keyboard focus, reduced motion respected, visually accessible, harmonious color palettes. Critique your own work as you build, taking screenshots to review if your environment supports it — a picture is worth 1000 tokens. Follow `references/review-loop.md`: screenshots at several widths, score against the token and slop files, fix the worst problem first, one place per pass, two to four passes, then report the changes as "element: old -> new". Consider Chanel's advice: before leaving the house, take a look in the mirror and remove one accessory. Human creatives have memory and always try to do something new, so if you have a space to quickly jot down notes about what you've tried, it can help you in future passes.

## More on writing in design

Words appear in a design for one reason: to make it easier to understand and use. They are design content, not decoration. Bring the same intentionality and minimalism to copywriting that you would bring to spacing and color. Before writing anything, ask what the design needs to say, and how it can best be said to help the person navigate the experience.

Before adding a sentence, identify the user's task, decision, or uncertainty it resolves. Reuse supplied copy; add text only for a missing purpose such as identifying an action, explaining a non-obvious input, reporting a real state, or helping recovery. If removing it leaves the task and meaning intact, omit it. Do not give every heading a subtitle or every control a helper paragraph by default.

Keep design commentary and implementation explanations out of product UI: for example, "A clean, intuitive experience," "Built with React," "This section showcases...", or "Optimized for smooth interaction" do not explain the user's next action. Do not invent taglines, feature descriptions, sample metrics, or status claims to make a screen look complete. If product copy is essential but unknown, flag that gap in the handoff and use minimal neutral sample content where necessary for the prototype.

Preserve requested editorial or educational content, necessary onboarding, errors, permission and privacy explanations, and accessible names or descriptions. Brevity is not a reason to hide help the user needs. Choose placement by relevance: a field hint at the field, a state message at the affected action, and optional detail in existing disclosure patterns when appropriate. Do not move filler into tooltips or screen-reader text to satisfy this rule.

During critique, inspect the actual rendered text as well as newly added string literals, including empty, loading, error, and narrow-screen states that the change touches. Remove repeated labels, narration of obvious controls, placeholder explanations, and agent-facing notes. Report design choices, test results, and remaining gaps in the conversation; render them inside the product only when the requested product itself needs them.

Write from the end user's perspective. Name things by what users will understand in simple language, not by how the system is built. A user manages notifications, not webhook config. Describe what something is or does in plain terms rather than selling it. Being specific and legible to new users is always better than being clever.

Use active voice as default. A CTA says exactly what happens when it is used: "Save changes," not "Submit." An action keeps the same name through the whole flow, so the button that says "Publish" produces a toast that says "Published." The vocabulary of an interface is the signposting for someone navigating the product. Cohesion and consistency are how people learn their way around.

Treat failure and emptiness as moments for direction, not mood. Explain what went wrong and how to fix it, in the interface's voice rather than a person's. Errors don't apologize, and they are never vague about what happened. An empty screen is an invitation to act.

Keep the tone conversational: plain verbs, sentence case, no filler, with tone matched to the brand and the audience. Let each written element do exactly one job.
