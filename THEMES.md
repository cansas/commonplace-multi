# Commonplace Themes

Commonplace uses **CSS custom properties** for theming. Every visual token — backgrounds, text, accents, borders, buttons — is controlled by a set of CSS variables. Themes are literally just CSS class blocks that override these variables.

## Built-in Themes

Three themes ship with Commonplace in `app/static/themes.css`:

| Theme | Class | Description |
|---|---|---|
| Modern | `.theme-modern` | Default. Zinc grays, Indigo accent, Inter font. |
| Reader | `.theme-reader` | Warm cream tones, Source Serif, muted browns. |
| Dark | `.theme-dark` | Deep charcoal, Amber accent, low-light friendly. |

Select one from **Settings → Appearance**.

## Custom Themes

You can add your own themes by dropping a `.css` file into `data/themes/`. No rebuild, no deploy — just create the file. The new theme appears in Settings → Appearance on the next page load.

### File Format

```
data/themes/{theme-name}.css
```

- The filename (minus `.css`) becomes the theme's identifier — e.g. `data/themes/forest.css` → `forest`
- Use lowercase, hyphens for spaces: `solarized-dark.css`
- A CSS comment on the **first line** is used as the theme description in the UI

### Minimal Example

```css
/* Ocean — Cool blues, calm reading */
.theme-ocean {
  --bg-page: #f0f4f8;
  --bg-sidebar: #e4eef5;
  --bg-card: #ffffff;
  --color-accent: #2563eb;
  --color-accent-hover: #1d4ed8;
  --color-accent-light: #eff6ff;
  --text-primary: #1e293b;
  --border-card: #d4e0ed;
  --btn-primary-bg: #2563eb;
  --btn-primary-text: #ffffff;
  --btn-primary-hover: #1d4ed8;
}
```

**Every variable is optional** — inherit from the default modern theme for anything you don't override. Only set what you want to change.

## All CSS Variable Tokens

Below is the complete list of CSS custom properties used by Commonplace. Override any subset.

### Page & Card Backgrounds

| Variable | Default | Purpose |
|---|---|---|
| `--bg-page` | `#f8fafc` | Main page background |
| `--bg-page-alt` | `#f1f5f9` | Alternate section background (cards, forms) |
| `--bg-sidebar` | `#ffffff` | Sidebar panel |
| `--bg-card` | `#ffffff` | Card / section backgrounds |
| `--bg-sidebar-hover` | `#f1f5f9` | Sidebar item hover |
| `--bg-sidebar-active` | `#e2e8f0` | Sidebar item active/selected |

### Text Colors

| Variable | Default | Purpose |
|---|---|---|
| `--text-primary` | `#1e293b` | Main body text |
| `--text-secondary` | `#475569` | Secondary / less important text |
| `--text-muted` | `#64748b` | Muted / metadata text |
| `--text-muted-lighter` | `#94a3b8` | Very muted / placeholder text |
| `--text-sidebar` | `#475569` | Sidebar navigation text |
| `--text-sidebar-muted` | `#94a3b8` | Sidebar secondary text |
| `--text-sidebar-active` | `#0f172a` | Sidebar active item text |

### Borders

| Variable | Default | Purpose |
|---|---|---|
| `--border-subtle` | `#e2e8f0` | Subtle dividers |
| `--border-card` | `#e2e8f0` | Card / section borders |
| `--border-sidebar` | `#e2e8f0` | Sidebar borders |

### Accent Colors

| Variable | Default | Purpose |
|---|---|---|
| `--color-accent` | `#4f46e5` | Primary accent (buttons, links, active states) |
| `--color-accent-hover` | `#4338ca` | Accent hover state |
| `--color-accent-light` | `#eef2ff` | Light accent (selected state backgrounds) |
| `--color-accent-lighter` | `#e0e7ff` | Lighter accent (hover on light accent) |
| `--color-accent-text` | `#4338ca` | Text on accent-colored elements |

### Links

| Variable | Default | Purpose |
|---|---|---|
| `--color-link` | `#4f46e5` | Link color |
| `--color-link-hover` | `#4338ca` | Link hover color |

### Buttons

| Variable | Default | Purpose |
|---|---|---|
| `--btn-primary-bg` | `#4f46e5` | Primary button background |
| `--btn-primary-text` | `#ffffff` | Primary button text |
| `--btn-primary-hover` | `#4338ca` | Primary button hover |

### Typography

| Variable | Default | Purpose |
|---|---|---|
| `--font-body` | `"Inter", system-ui, sans-serif` | Body and UI font |
| `--font-mono` | `"JetBrains Mono", ui-monospace, monospace` | Monospace / code font |

### Scrollbar

| Variable | Default | Purpose |
|---|---|---|
| `--scrollbar-track` | `#f1f5f9` | Scrollbar track |
| `--scrollbar-thumb` | `#cbd5e1` | Scrollbar thumb |
| `--scrollbar-thumb-hover` | `#94a3b8` | Scrollbar thumb hover |

### Selection

| Variable | Default | Purpose |
|---|---|---|
| `--selection-bg` | `#6366f1` | Text selection / highlight background |

## How It Works

1. Commonplace loads `app/static/themes.css` (built-in themes) plus any `.css` files from `data/themes/` as `<link>` stylesheets.
2. The selected theme name is stored as a class on `<body>`: `class="theme-forest"`.
3. Each theme file defines a class block — only the one matching the current class is active. Unselected theme classes are dormant.
4. All template elements reference these CSS variables, so switching a single class repaints the entire UI.

### Theme Discovery

On every page render, Commonplace scans `data/themes/` for `.css` files. The file's first CSS comment is used as the theme's description in the settings UI. Themes appear in **Settings → Appearance** in alphabetical order after the built-in options.

### Sidebar Toggle

The sidebar theme toggle button cycles through all available themes (built-in + custom) in the order they appear on the settings page. Each click advances to the next theme.
