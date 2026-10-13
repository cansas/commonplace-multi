---
name: Commonplace
description: A self-hosted reading room for the highlights you keep.
colors:
  ink-indigo: "#4f46e5"
  ink-indigo-deep: "#4338ca"
  ink-indigo-wash: "#eef2ff"
  ink-indigo-wash-2: "#e0e7ff"
  indigo-highlight: "#6366f1"
  amber-annotation: "#f59e0b"
  review-green: "#16a34a"
  slate-paper: "#f8fafc"
  surface: "#ffffff"
  surface-alt: "#f1f5f9"
  surface-active: "#e2e8f0"
  ink: "#1e293b"
  ink-secondary: "#475569"
  margin-gray: "#607087"
  margin-gray-light: "#94a3b8"
  sidebar-active: "#0f172a"
  sidebar-muted: "#68768a"
  rule: "#e2e8f0"
  charcoal-deep: "#07070e"
  charcoal-card: "#11111e"
  koreader-surface: "#d1fae5"
  koreader-ink: "#065f46"
  koreader-rule: "#a7f3d0"
  readwise-surface: "#dbeafe"
  readwise-ink: "#1e40af"
  readwise-rule: "#bfdbfe"
  manual-surface: "#fef3c7"
  manual-ink: "#92400e"
  manual-rule: "#fde68a"
  action-favorite: "#b45309"
  action-delete: "#b91c1c"
  action-share: "#4f46e5"
  danger-surface: "#fef2f2"
  danger-border: "#fecaca"
  danger-ink: "#b91c1c"
  danger-solid: "#dc2626"
  heat-light-1: "#bbf7d0"
  heat-light-2: "#4ade80"
  heat-light-3: "#16a34a"
  heat-light-4: "#15803d"
  heat-dark-1: "#14532d"
  heat-dark-2: "#166534"
  heat-dark-3: "#15803d"
  heat-dark-4: "#22c55e"
typography:
  headline:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: "1.875rem"
    fontWeight: 700
    lineHeight: 1.2
  title:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: "1.5rem"
    fontWeight: 600
    lineHeight: 1.33
  body:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 400
    lineHeight: 1.5
  reading:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: "0.9375rem"
    fontWeight: 400
    lineHeight: 1.625
  quote:
    fontFamily: 'Georgia, "Times New Roman", Times, serif'
    fontSize: "1.125rem"
    fontWeight: 400
    lineHeight: 1.75
  label:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: "0.75rem"
    fontWeight: 600
    lineHeight: 1.33
    letterSpacing: "0.05em"
  micro:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: "0.625rem"
    fontWeight: 500
    lineHeight: 1.3
  badge:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: "0.7rem"
    fontWeight: 600
    lineHeight: 1.5
    letterSpacing: "0.04em"
  control:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: "0.8125rem"
    fontWeight: 500
    lineHeight: 1.4
  headline-compact:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: "1.75rem"
    fontWeight: 700
    lineHeight: 1.2
  quote-compact:
    fontFamily: 'Georgia, "Times New Roman", Times, serif'
    fontSize: "1.05rem"
    fontWeight: 400
    lineHeight: 1.75
  mono:
    fontFamily: "JetBrains Mono, ui-monospace, SFMono-Regular, monospace"
    fontSize: "0.65rem"
    fontWeight: 600
  body-reader:
    fontFamily: 'Source Serif 4, Georgia, "Times New Roman", serif'
    fontSize: "0.875rem"
    fontWeight: 400
    lineHeight: 1.5
  body-contemporary:
    fontFamily: "Jost, system-ui, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 400
    lineHeight: 1.5
  mono-contemporary:
    fontFamily: "Overpass Mono, ui-monospace, monospace"
    fontSize: "0.65rem"
    fontWeight: 600
rounded:
  xs: "3px"
  sm: "4px"
  md: "8px"
  lg: "12px"
  xl: "16px"
  pill: "9999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "12px"
  lg: "16px"
  xl: "20px"
  xxl: "24px"
  page: "32px"
components:
  button-primary:
    backgroundColor: "{colors.ink-indigo}"
    textColor: "{colors.surface}"
    typography: "{typography.body}"
    rounded: "{rounded.md}"
    padding: "8px 16px"
  button-primary-hover:
    backgroundColor: "{colors.ink-indigo-deep}"
  button-secondary:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink-secondary}"
    typography: "{typography.body}"
    rounded: "{rounded.md}"
    padding: "6px 16px"
  button-ghost:
    textColor: "{colors.margin-gray}"
    typography: "{typography.body}"
    rounded: "{rounded.md}"
    padding: "6px 16px"
  input-text:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    typography: "{typography.body}"
    rounded: "{rounded.md}"
    padding: "8px 12px"
    height: "38px"
  card:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.lg}"
    padding: "24px"
  card-note:
    backgroundColor: "{colors.surface-alt}"
    textColor: "{colors.ink-secondary}"
    rounded: "{rounded.md}"
    padding: "8px 16px"
  stat-card:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.lg}"
    padding: "24px"
  tag-pill:
    backgroundColor: "{colors.surface-alt}"
    textColor: "{colors.margin-gray}"
    typography: "{typography.label}"
    rounded: "{rounded.pill}"
    padding: "1px 8px"
  source-badge:
    typography: "{typography.label}"
    rounded: "{rounded.pill}"
    padding: "2px 10px"
  nav-item:
    textColor: "{colors.ink-secondary}"
    typography: "{typography.body}"
    rounded: "{rounded.md}"
    padding: "10px 12px"
  nav-item-active:
    backgroundColor: "{colors.surface-active}"
    textColor: "{colors.ink}"
  shortcut-key:
    backgroundColor: "{colors.surface-alt}"
    textColor: "{colors.ink-secondary}"
    typography: "{typography.mono}"
    rounded: "{rounded.sm}"
    padding: "1px 6px"
  heatmap-cell:
    rounded: "{rounded.xs}"
    size: "14px"
  bottom-nav-item:
    textColor: "{colors.margin-gray-light}"
    rounded: "{rounded.md}"
    padding: "6px 10px"
---

# Design System: Commonplace

## Overview

**Creative North Star: "The Reading Room"**

Commonplace is a reading room, not a workspace. Every surface exists to hold text and then get out of the way: a page is a stack of pale cards on slate paper, one accent color for the thing you should do next, and text carrying everything else. Density is low on purpose. A class census across `app/templates/*.html` counts 233 uses of `text-sm` and 195 of `text-muted` against zero uses of any display or hero type - the interface speaks in one quiet mid-size voice.

The room is themeable by design, and that is the load-bearing property of the whole system. Six built-in themes (Modern, Reader, Dark, Glass, Contemporary, Contemporary Dark) are nothing but CSS custom-property overwrites of the same ~40 token names in `app/static/themes.css`, and a user can drop a seventh into `data/themes/`. No template names a color; the theme swap is one class on `<body>` (`base.html:22`). The frontmatter above therefore records the Modern values as the normative source, and the other five themes re-key the same variables.

Components are quietly tactile. Cards lift 2px on hover and take a soft shadow, buttons respond on press, the heatmap cell scales under the cursor - small answers that stay small, so a wall of thirty highlight cards still reads as a page rather than a dashboard. Motion runs 150ms for state, 250-350ms for entrances, and always eases out. The Glass theme is the single place the system permits literal light: translucent cards over deep navy, blurred at 16px, with a shadowed accent. That glow is a deliberate theme identity, not a house style.

**Key Characteristics:**
- One accent per theme, spent sparingly and only on the next action
- Six theme sheets sharing a single token vocabulary, plus user-droppable themes
- Quiet type scale: 14px body, no display face, uppercase reserved for 12px labels
- Flat surfaces at rest; elevation appears only as a response to state
- Mobile is a real second layout - fixed bottom nav, bottom sheets, swipe rows
- Text-first proportions: highlight text is the largest recurring type on any page

No visual anti-reference has been confirmed by the operator yet. Every guardrail below is grounded in the incumbent implementation rather than a rejected style.

## Colors

A slate-and-paper neutral field, one saturated accent per theme, and warm signals reserved for bookkeeping: favorites, provenance, and review history.

### Primary
- **Ink Indigo** (#4f46e5): the Modern theme's accent. Primary buttons, the active nav row, links, and the 2px gradient that fades in across the top of a stat card on hover.
- **Ink Indigo Deep** (#4338ca): the accent's hover and pressed voice, and the accent-as-text color on light surfaces.
- **Indigo Wash** (#eef2ff) and **Indigo Wash Deep** (#e0e7ff): the accent's soft fills, for selected and secondary accent states.

### Secondary
- **Indigo Highlight** (#6366f1): text selection and the share action in the mobile swipe row. Slightly brighter than the accent so a selection reads as marked rather than clickable.
- **Amber Annotation** (#f59e0b): the accent for Dark and Glass, and in every theme the favorite star. In Modern it is the annotate signal, not a system accent.

### Tertiary
- **Review Green** (#16a34a): the review heatmap's filled steps. The heatmap is the only place a saturated data ramp is allowed.
- **Provenance tints**: koreader (`--badge-koreader-*`), readwise (`--badge-readwise-*`), manual (`--badge-manual-*`), each a surface/ink/rule triplet. Provenance keeps one meaning in every theme, so these live in the theme-invariant token block rather than in a palette.
- **Swipe actions**: `--action-favorite`, `--action-delete`, `--action-share`, with `--action-label` for the glyph. Dark enough for that label (5.02:1, 6.47:1, 6.29:1; before extraction they were 2.15:1, 3.76:1 and 4.47:1).
- **Danger**: `--danger-surface`, `--danger-border`, `--danger-ink`, `--danger-solid`. One semantic set behind `.alert-danger`, `.btn-danger`, `.btn-danger-quiet`, `.badge-danger`, `.text-danger`, and `.hover-danger`. Five shades of red (500, 600, 700, 800, plus a literal) collapsed into this.
- **Review heat ramp**: `--heat-1` through `--heat-4`, one designed step per intensity, declared per theme family. Light themes step `#bbf7d0` -> `#4ade80` -> `#16a34a` -> `#15803d`; dark themes step `#14532d` -> `#166534` -> `#15803d` -> `#22c55e`. This replaced the `[data-theme="dark"]` override block, which meant Glass and Contemporary Dark had no ramp of their own and borrowed the light greens.

### Neutral
- **Slate Paper** (#f8fafc): the page field in Modern.
- **Surface** (#ffffff), **Surface Alt** (#f1f5f9), **Surface Active** (#e2e8f0): cards and sidebar at rest, quiet fills and hover rows, and the active nav row.
- **Ink** (#1e293b), **Ink Secondary** (#475569), **Margin Gray** (#607087): the three steps that carry text. Margin Gray is tuned to clear 4.5:1 on the worst surface it lands on in each theme (4.6:1 in Modern, on the alt surface).
- **Margin Gray Light** (#94a3b8): not a text color. A step lighter than Margin Gray cannot reach 4.5:1 on any surface in this system, so it is reserved for separators, dividers, disabled controls, and glyphs. Its three remaining uses are exactly that: a `·` separator, an emoji, and a disabled button, which WCAG exempts.
- **Sidebar Active** (#0f172a) and **Sidebar Muted** (#68768a): the sidebar's own pair - the wordmark and active row use the first, the tagline and the highlights count the second, measured at 4.62:1 on the sidebar surface.
- **Rule** (#e2e8f0): every border and divider, always 1px. The system has no 2px borders.
- **Charcoal Deep** (#07070e) and **Charcoal Card** (#11111e): the dark field and its raised card.

### Theme Anchors
The five non-Modern themes re-key the same variable names; these are their identities.
- **Reader**: warm brown accent #655743 on cream #faf8f5, Source Serif 4 body, and quoted material forced to the serif (`themes.css:221`).
- **Dark**: amber #f59e0b on charcoal, with inverted button text (#07070e on amber).
- **Glass**: indigo #6366f1 on deep navy #0f172a, translucent cards rgba(30,27,50,0.55) at `backdrop-filter: blur(16px)`, accent glow shadows.
- **Contemporary**: magenta #c800df on #f8f7fc, Jost body, Overpass Mono.
- **Contemporary Dark**: #d946ef on #0d0b15, with the accent's light steps expressed as rgba(217,70,239,0.12) and rgba(217,70,239,0.06).

### Named Rules
**The One Accent Rule.** A theme declares exactly one accent. Anything that wants a second color argues for a state (hover, wash, border) instead of a hue, and no screen spends the accent on more than roughly a tenth of its pixels. Its scarcity is what makes the next action legible.

**The Six-Shelf Rule.** Every color decision has to resolve in all six themes. A literal hex inside a template is a bug, because the theme swap is a single class on the body and hard-coded color breaks it silently - in the theme nobody testing happens to be using.

**The Legible Ramp Rule.** Three steps carry text; the fourth does not. A caption that needs to be quieter than Margin Gray gets more space or a smaller role, never the decorative token - reaching past the last legible step is what put 2.6:1 text in the shell.

## Typography

**Display Font:** none. The system has no display face; hierarchy comes from size and weight inside the body face. A surface that seems to need one needs a larger body size, not a new font.
**Body Font:** Inter (with `system-ui, sans-serif`) in Modern, Dark, and Glass; Source Serif 4 with a Georgia fallback in Reader; Jost in both Contemporary themes. Each is a declared role (`body-reader`, `body-contemporary`) rather than a stray font-family, so the theme faces are visible to tooling.
**Label/Mono Font:** JetBrains Mono in four themes, Overpass Mono in Contemporary. All four families load once at `base.html:15`.

**Character:** a plain, legible interface voice with the serif held back for quoted material. Chrome speaks in the sans; the highlight itself gets the serif wherever a theme offers one. Inter is deliberate rather than provisional: the detector flags it as overused, and replacing it is an identity change, not a polish step.

### Hierarchy
- **Headline** (700, 1.875rem/30px, 1.2): stat numbers and the few real page titles.
- **Title** (600, 1.5rem/24px, 1.33): card and section headings.
- **Body** (400, 0.875rem/14px, 1.5): the default voice, 233 uses across the templates.
- **Reading** (400, 0.9375rem/15px, 1.625): highlight text on cards and in the review flow, the one place type is allowed to grow.
- **Quote** (400, 1.125rem/18px, 1.75, serif): review quotes. `style.css:78-81` sets Georgia; Reader overrides to Source Serif 4; mobile steps the review card down to 1.05rem (`style.css:522`).
- **Label** (600, 0.75rem/12px, 0.05em tracking, uppercase): form labels, section eyebrows, badges. The only uppercase in the system.
- **Micro** (500, 0.625rem/10px): mobile bottom-nav labels.
- **Badge** (600, 0.7rem/11.2px, 0.04em, uppercase): source badges and the mobile swipe labels - the smallest text the system ships in the app, at the 11px floor.
- **Control** (500, 0.8125rem/13px): the sidebar theme toggle.
- **Headline Compact** (700, 1.75rem/28px): stat numerals inside the mobile breakpoint, where `headline` is too wide.
- **Quote Compact** (400, 1.05rem, 1.75): the review quote inside the mobile card, a step down from `quote`.
- **Mono** (600, 0.65rem): keyboard shortcut keys.

### Named Rules
**The Reading Line Rule.** Quoted material is serif where the theme offers one, set at 1.75 line-height, never smaller than 15px, and never truncated mid-sentence to make a card fit.

**The Uppercase Reserve Rule.** Uppercase belongs to labels and badges at 12px with 0.05em tracking. Titles, buttons, and navigation are sentence case.

## Layout

A single centered column: `max-w-6xl` (1152px) inside `px-4 sm:px-6 lg:px-8` with `py-6 md:py-8` (`base.html:126-130`), beside a fixed 240-256px sidebar (`w-64 md:w-60 lg:w-64`, `base.html:40`) that is sticky from 768px up and an off-canvas drawer below it, behind a `bg-black/50` overlay. Vertical rhythm is one 24px step (`gap-6`, `space-y-6`) at the page level and a 4px step inside components.

Breakpoints are Tailwind's defaults (640 / 768 / 1024) plus two hand-written media queries in `style.css` - 767px and 639px - that carry the mobile work: the highlight table swaps to cards at 767px (`style.css:351-358`), full-screen bottom sheets replace centered dialogs, swipe reveals appear, and the review card re-tunes its own padding and type. Mobile is a second layout, not a squeezed desktop: a fixed bottom nav with `env(safe-area-inset-bottom)` padding, a "More" button standing in for the sidebar's overflow, and touch targets padded up for thumbs.

## Elevation & Depth

Flat at rest, elevated on contact. Depth is a state, not a hierarchy: cards sit flush on the page field until a pointer or a finger addresses them, and then they lift 2px and take a soft neutral shadow. There is no resting shadow vocabulary to rank surfaces by, so importance is expressed through type size, the accent, and position instead. Glass is the deliberate exception, carrying real blur and lit edges as its theme identity.

### Shadow Vocabulary
- **Ambient lift** (`0 8px 24px rgba(0,0,0,0.06)`): a stat card on hover, paired with `translateY(-2px)`.
- **Hairline** (`0 1px 2px rgba(0,0,0,0.05)` via Tailwind `shadow-sm`): resting buttons and cards, barely there.
- **Dialog** (Tailwind `shadow-xl`): the confirm dialog, the one genuinely raised surface in the system.
- **Glass card** (`0 8px 32px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.06)`): blurred glass cards at rest; hover deepens to `0 16px 48px rgba(0,0,0,0.4)` with a brighter inset edge.
- **Glass accent glow** (`0 4px 14px rgba(99,102,241,0.3)`, buttons `0 6px 20px rgba(99,102,241,0.4)`): the Glass theme's lit accent.
- **Key edge** (`0 1px 0 #cbd5e1`): the physical bottom edge on a keyboard shortcut key.

### Named Rules
**The Flat-Until-Touched Rule.** Surfaces are flat at rest. Shadows are a response to state - hover, focus, or an actual physical metaphor like a key cap - never a way to rank importance.

**The Glass Exception Rule.** Colored glow is fenced inside the Glass theme. No other theme gains a chromatic box-shadow or halo, because a glow that appears in one shelf has to be justified in all six.

## Shapes

Rectangles with softened corners, and the radius itself encodes size: 3px for heatmap cells, 4px for keyboard keys, 8px as the workhorse (buttons, inputs, nav rows, 150 uses of `rounded-lg`), 12px for cards (64 uses of `rounded-xl`, and the mobile highlight card matches at 12px), 16px for mobile sheets and the review card, and pills at `9999px` for tag pills, source badges, and the range thumb's `50%`.

Borders are always 1px and always tokenized, so a border inverts cleanly between a light and a dark theme. Tables use `border-collapse: separate` with zero spacing so rows can still take a corner. Mobile sheets round only their top corners (16px 16px 0 0) and grow a 36x4px drag handle, which is the system's only non-rectangular furniture. There are no diagonals, no texture, and no ornament: the geometry stays a stack of quiet rectangles.

## Components

### Buttons
- **Shape:** 8px radius, 1px transparent border so secondary and primary share a box model.
- **Primary:** accent fill with white text in light themes and dark text on amber in Dark; 8px 16px padding, 14px medium, `shadow-sm`. In Dark the text inverts to the page color (#07070e) because amber is a light fill.
- **Hover / Focus:** background steps to the deep accent, transition 150ms. Focus today relies on `focus:ring-2` and a `ring-accent/40` that resolves to nothing - see Don'ts.
- **Secondary:** surface background, 1px rule border, secondary text, hover settles onto the alt surface.
- **Ghost:** muted text, no border, accent on hover; used for tertiary row actions such as Share.

### Chips
- **Tag pill:** pill radius, 12px field fill, 1px rule border, 11px medium muted text, hover deepens fill and text. 1px 8px padding keeps them quiet inside dense rows.
- **Source badge:** pill radius, 11px semibold uppercase with 0.04em tracking, 2px 10px padding, one tint per capture source. Color here carries meaning, so the badge never appears without its source name.

### Cards / Containers
- **Corner Style:** 12px radius (mobile highlight cards included); 16px on mobile sheets.
- **Background:** surface, with alt-surface for inset notes.
- **Shadow Strategy:** hairline at rest, ambient lift on hover - see Elevation & Depth.
- **Border:** 1px rule on every card, which is what keeps cards legible in the Reader theme's low-contrast cream field.
- **Internal Padding:** 24px (`p-6`) on dashboard cards, 16-20px on dense rows, 14px 16px on mobile highlight cards.
- **Signature detail:** the dashboard's highlight card carries a 4px-wide accent bar with a soft rounded end down its left edge, tying the card to the accent without filling anything with color. Stat cards grow a 2px accent gradient across their top edge on hover only.

### Inputs / Fields
- **Style:** full width, surface background, 1px rule border, 8px radius, 8px 12px padding, 14px text.
- **Focus:** accent border plus a 2px accent-translucent ring intended at 40% opacity. The border half works; the ring half does not - see Don'ts.
- **Range:** 8px slat track at 4px radius with a 20px circular accent thumb wearing a 2px white border and a `0 1px 4px rgba(0,0,0,0.15)` shadow, deepening to an accent shadow on hover.

### Navigation
- **Sidebar:** 14px medium rows at 8px radius, 10px 12px padding, secondary text on the sidebar field; hover moves text to active and fills with the alt surface; the active row fills with the deepest surface step and goes semibold. Icons are drawn SVG at 18px in the same 1.8-stroke family as the mobile bottom nav (`nav-icon`), so the shell speaks one icon language at every width. The theme toggle carries a split-circle mark and names the theme it will switch to.
- **Mobile bottom nav:** five flex items, 22px inline SVG icons stroked at 1.8 with round caps, 10px labels, active state coloring both icon and label. `env(safe-area-inset-bottom)` is honored so it clears a home indicator.
- **Theme toggle:** a full-width sidebar row, 13px medium, muted until hover; it names the theme it will switch to ("Switch to Reader") rather than the current one.

### Signature: Review Heatmap
A 14px cell at 3px radius, stepped through five review-green levels above an idle cell drawn from the alt surface, with a dark-theme override set that re-pitches every level for charcoal. Cells scale 1.4 on hover to make a year of reading legible one day at a time. It is the only data visualization in the product and the only component allowed a saturated ramp.

### Signature: Keyboard Shortcut Key
A 4px-radius key cap at 11px semibold mono, alt-surface fill, a `1px solid #cbd5e1` border, and a `0 1px 0 #cbd5e1` bottom edge so it reads as a physical key. The review flow leans on it to teach the shortcuts that make daily review fast.

## Do's and Don'ts

### Do:
- **Do** define every color, border, and surface as a token in `app/static/themes.css` and consume it through `var()` or a semantic class. Six themes read the same variable names, so a token is what makes a change themeable at all.
- **Do** check any visual change in all six themes before calling it done - Modern, Reader, Dark, Glass, Contemporary, Contemporary Dark - since a low-contrast pair that passes on slate paper can fail on cream or on translucent glass.
- **Do** keep the accent rare. One action per view earns it; the rest belongs to type and surface.
- **Do** keep quoted material serif where the theme offers one, at 1.75 line-height and at least 15px.
- **Do** reuse the incumbent's tactile values - `translateY(-2px)` with `0 8px 24px rgba(0,0,0,0.06)`, press-scale 0.99 - so dozens of cards behave identically instead of each inventing its own lift.
- **Do** build mobile as its own layout (bottom nav, bottom sheets, swipe rows, safe-area padding) rather than shrinking the desktop column.
- **Do** keep UI edits portable to upstream `cansas/commonplace`; friction here is paid twice.
- **Do** theme the browser's own surfaces from the palette - caret, placeholder, selection, scrollbars, focus. They are the cheapest signal that a page was built rather than assembled: `caret-color: var(--color-accent)`, placeholders at `var(--text-muted)`, focus authored once as `outline: 2px solid var(--color-accent)`.
- **Do** draw icons as SVG in one stroke weight (1.8, round caps and joins) and mark them `aria-hidden`; the row label carries the meaning.
- **Do** give the accent's text-bearing pair to anything that puts text on the accent (`--btn-primary-bg` + `--btn-primary-text`), so a dark theme reads dark-on-amber instead of white-on-amber at 2.1:1.
- **Do** give a repeated literal a token before the third copy. Provenance, swipe actions, the heat ramp and the error surface were all extracted this pass; each had been a literal repeated across files, and the error surface had drifted into five different reds.
- **Do** confirm a token exists before referencing it. Seven `var()` references here pointed at names that were never defined (`--sidebar-muted`, `--sidebar-active`, `--sidebar-hover`, `--page-alt`, `--interactive-accent`), so the mobile bottom nav silently lost its colours and the review chart stayed indigo in all six themes. A missing token fails without a warning; check the name against `themes.css`.
- **Do** keep pre-auth and first-run surfaces on the same tokens as the app. `/setup` used to be a self-contained page with eleven hardcoded colours; it now links `themes.css` and reads every colour from tokens, so a new user's first screen follows the theme system instead of freezing the Modern palette.

### Don't:
- **Don't** ship a second shade of a colour that already has a meaning. One danger set, one accent per theme, one ramp per data surface; a new shade is a new intent or a bug.
- **Don't** introduce a color literal outside `themes.css`. The theme swap is one class on `<body>` (`base.html:22`), and a hard-coded hex silently breaks the theme nobody happens to be testing. The three source-badge tints in `style.css:97-113` are the existing debt of this kind.
- **Don't** write Tailwind classes that need a config file. `tailwind.min.js` is the 3.4.17 Play CDN bundle with no config, so palette utilities like `ring-accent/40` and `accent-accent` resolve to nothing - which is why 37 call sites paired `focus:outline-none` with a ring that painted Tailwind's default blue. The project's own semantic classes (`.bg-accent`, `.text-primary`, `.border-card`) are the supported path. `themes.css` now maps `--tw-ring-color` to the accent so those call sites are correct until they are rewritten; new work should not add more of them.
- **Don't** check in a build step. The frontend is Jinja, hand-written CSS, a bundled Tailwind, and vanilla JS; parity with upstream depends on there being no npm toolchain.
- **Don't** add motion without a reduced-motion guard. `prefers-reduced-motion` appears nowhere in the codebase today, so every animation added widens that gap.
- **Don't** extend the Glass theme's glow, blur, or translucent cards into the other five themes. Glass is an identity, not a technique to borrow.
- **Don't** put emoji in chrome. Page copy may use one as a content glyph, but navigation, toggles, and badges use drawn SVG; emoji carry a different weight, color, and baseline on every platform, which is why the shell stopped using them.
- **Don't** introduce a display face or hero type. Hierarchy is bought with size, weight, and position in the existing scale.
