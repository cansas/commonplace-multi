# Clipboard & Contextual Shares — Implementation Plan

> **For Hermes:** Use this plan to implement the clipboard and contextual shares features for Commonplace v0.9.

**Goal:** Add one-click copy buttons on all highlight views and make the context modal actionable (copy/share individual context highlights).

**Architecture:** Pure frontend — no API changes needed. The `share_token` is already on every highlight model, the context API at `GET /api/highlights/{id}/context` already returns full highlight objects, and `showToast()` exists in `commonplace.js`. Work is in templates (adding buttons) and JS (clipboard API + wiring).

**Tech Stack:** Jinja2 templates, vanilla JS (CSP-safe, no inline handlers), `navigator.clipboard.writeText()`, existing `showToast()` and `confirmModal()` utilities.

---

## Current Context

- **`highlights.html`** — Desktop table has an expanded detail row (`.highlight-detail`) with action buttons: Edit, Context, Delete, Share (latter only if `h.share_token`). Mobile cards have a card-detail section with same actions plus swipe-to-reveal.
- **`review.html`** — Has secondary actions: Context, Delete, Favorite, Later. No copy button.
- **`share.html`** — Standalone share page showing the card image. No copy button.
- **`commonplace.js`** — `showToast()` already exists. `loadContext()` renders context for highlights page. `showReviewContext()` renders context modal for review page. `contextItemHtml()` and `contextModalItem()` render individual context items with text, date, chapter/page — but no copy/share buttons.
- **`base.html`** — `#toast-container` and confirm modal already rendered.
- **Data actions** — Already wired via delegated click handler on `[data-action]`. New actions just need a function + `else if` branch.

---

## Step-by-Step Plan

### Task 1: Add `copyText()` utility to commonplace.js

**Objective:** A shared `copyText(text, label)` function used by all copy buttons. Writes to clipboard via `navigator.clipboard.writeText()`, shows toast on success/error, accessible globally as `window.copyText`.

**Files:**
- Modify: `app/static/commonplace.js` — add function after utility section (~line 87)

**Steps:**

1. Add `window.copyText` function after the `updateFileName` function:

```js
window.copyText = function(text, label) {
    label = label || 'Text';
    if (!navigator.clipboard || !navigator.clipboard.writeText) {
        window.showToast('Clipboard not available', 'error');
        return;
    }
    navigator.clipboard.writeText(text).then(function() {
        window.showToast(label + ' copied!', 'success');
    }).catch(function(e) {
        window.showToast('Copy failed: ' + e.message, 'error');
    });
};
```

2. Add the data-action handler in the click delegation section (~line 1131):

```js
else if (action === 'copy-text') {
    e.preventDefault();
    var text = btn.getAttribute('data-text');
    var label = btn.getAttribute('data-label') || 'Highlight';
    if (window.copyText) window.copyText(text, label);
}
```

**Verification:** After adding the function, calling `copyText('test', 'Test')` in the browser console shows a toast "Test copied!".

---

### Task 2: Copy button on highlights page (desktop + mobile)

**Objective:** Add a clipboard/copy button to each highlight's expanded detail row (desktop table) and mobile card detail section. Copies the full highlight text.

**Files:**
- Modify: `app/templates/highlights.html` (two locations)

**Desktop (line ~128-133, the action button group in `.highlight-detail`):**
Add a copy button alongside existing Edit/Context/Delete/Share buttons:

```html
<button data-action="copy-text" data-text="{{ h.text }}" data-label="Highlight"
        class="px-3 py-1 bg-white border border-slate-200 text-slate-600 rounded text-xs font-medium hover:bg-slate-50 transition-colors">
    📋 Copy
</button>
```

Place it at the start of the action button group (before Edit).

**Mobile card (line ~217-224, the action button group in `.hl-card-detail`):**
Add the same button in the mobile card action flex row:

```html
<button data-action="copy-text" data-text="{{ h.text }}" data-label="Highlight"
        class="flex-1 px-3 py-2 bg-white border border-slate-200 text-slate-600 rounded-lg text-xs font-medium hover:bg-slate-50">
    📋 Copy
</button>
```

Place it at the start of the mobile action row (before Edit).

**Swipe-to-reveal area (line ~267-273):**
Optionally add a copy button to the swipe reveal area too. This is lower priority but fits the pattern of quick actions.

**Verification:** Open highlights page, expand a row, click 📋 Copy — toast shows "Highlight copied!" and the text is on the clipboard.

---

### Task 3: Copy button on review page

**Objective:** Add a copy button to the review flash card layout. User can copy the highlight text they're reviewing.

**Files:**
- Modify: `app/templates/review.html`

**Steps:**

Add a copy button in the secondary actions section (line ~93-117, the `review-secondary-actions` div):

```html
<button type="button" data-action="copy-text" data-text="{{ highlight.text }}" data-label="Highlight"
        class="px-3 py-1.5 text-xs text-muted hover:text-indigo-500 hover:bg-page-alt rounded-md transition-colors">
    📋 Copy
</button>
```

Place it as the first secondary action (before Context).

**Verification:** Open `/review`, click 📋 Copy — toast shows "Highlight copied!" and text is on clipboard.

---

### Task 4: Copy button on share page

**Objective:** Add a copy button to the public share page so visitors can copy the highlighted text.

**Files:**
- Modify: `app/templates/share.html`

**Steps:**

Add a copy button in the attribution section (after the note block, around line ~50):

```html
{% if not error %}
<div class="mt-4 text-center">
    <button onclick="navigator.clipboard.writeText('{{ highlight.text|e('js') }}').then(function(){ var e=document.getElementById('copy-msg'); e.textContent='Copied!'; setTimeout(function(){e.textContent=''},2000); })"
            class="px-5 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 transition-colors shadow-sm">
        📋 Copy Text
    </button>
    <p id="copy-msg" class="text-xs text-slate-400 mt-2"></p>
</div>
{% endif %}
```

Note: The share page doesn't use `base.html` (standalone page with Tailwind only), so it can't use the toast system. Use an inline confirmation instead.

**Verification:** Open a share link (`/share/{token}`), click 📋 Copy Text — "Copied!" appears below the button, text is on clipboard.

---

### Task 5: Add copy/share buttons to context modal items (highlights page)

**Objective:** Each context highlight item rendered by `contextItemHtml()` gets a Copy button and a Share button (if `share_token` exists). The current item also needs these actions.

**Files:**
- Modify: `app/static/commonplace.js` — update `contextItemHtml()` function

**Steps:**

1. Update `contextItemHtml()` (~line 355) to add an action bar below each context item:

```js
function contextItemHtml(hl, isCurrent, highlightId) {
    var cls = isCurrent ? 'bg-indigo-50 border-indigo-200 ring-1 ring-indigo-200' : 'bg-white border-slate-200';
    var favStar = hl.favorite ? '\u2B50' : '\u2606';
    var text = hl.text.length > 120 ? hl.text.substring(0, 120) + '\u2026' : hl.text;
    var pageInfo = '';
    if (hl.chapter) pageInfo += ' <span class="text-slate-400">\xb7</span> ' + hl.chapter;
    if (hl.page) pageInfo += ' <span class="text-slate-400">\xb7</span> p.' + hl.page;

    // Action bar: Copy + Share (if token exists)
    var actions = '<div class="flex gap-2 mt-1.5 pt-1.5 border-t border-slate-100">' +
        '<button class="text-xs text-indigo-500 hover:text-indigo-700" onclick="event.stopPropagation(); window.copyText(\'' +
        window.escapeHtml(hl.text) + '\', \'Highlight\')">\uD83D\uDCCB Copy</button>';
    if (hl.share_token) {
        actions += ' <a href="/share/' + hl.share_token + '" target="_blank" class="text-xs text-indigo-500 hover:text-indigo-700">\uD83D\uDCE4 Share</a>';
    }
    actions += '</div>';

    return '<div class="flex items-start gap-2 px-3 py-2.5 rounded-lg text-sm border ' + cls + '">' +
        '<button class="context-fav-btn shrink-0 mt-0.5 text-sm leading-none ' + (hl.favorite ? 'text-amber-400' : 'text-slate-300 hover:text-amber-300') + '" data-id="' + hl.id + '">' + favStar + '</button>' +
        '<div class="min-w-0 flex-1">' +
        '<p class="text-slate-700 leading-relaxed ' + (isCurrent ? 'font-medium' : '') + '">' + window.escapeHtml(text) + '</p>' +
        '<div class="text-xs text-slate-400 mt-0.5">' +
        (hl.highlighted_at || '') + pageInfo +
        '</div>' + actions +
        '</div></div>';
}
```

Key changes:
- Added `actions` div with Copy (calls `copyText`) and Share (link to share page)
- Escape the text properly when embedding in inline onclick — use `window.escapeHtml()` and be careful with quotes
- The Share link opens in a new tab pointing to `/share/{share_token}`

**Verification:** Open highlights page, expand a highlight, click Context. Each context item shows 📋 Copy and 📤 Share buttons. Click Copy — toast shows, text is on clipboard.

---

### Task 6: Add copy/share buttons to review context modal

**Objective:** Update `contextModalItem()` function in the review context modal to include Copy and Share buttons.

**Files:**
- Modify: `app/static/commonplace.js` — update `contextModalItem()` function (~line 1017)

**Steps:**

Update `contextModalItem()` with the same action bar pattern:

```js
function contextModalItem(hl, isCurrent) {
    var cls = isCurrent ? 'bg-indigo-50 dark:bg-indigo-900/20 border-indigo-200 dark:border-indigo-700 ring-1 ring-indigo-200' : 'bg-page-alt border-card';
    var text = hl.text.length > 150 ? hl.text.substring(0, 150) + '\u2026' : hl.text;
    var pageInfo = '';
    if (hl.chapter) pageInfo += ' <span class="text-muted">\xb7</span> ' + hl.chapter;
    if (hl.page) pageInfo += ' <span class="text-muted">\xb7</span> p.' + hl.page;

    var actions = '<div class="flex gap-2 mt-1.5 pt-1 border-t border-card">' +
        '<button class="text-xs text-indigo-500 hover:text-indigo-700" onclick="event.stopPropagation(); window.copyText(\'' +
        window.escapeHtml(hl.text) + '\', \'Highlight\')">\uD83D\uDCCB Copy</button>';
    if (hl.share_token) {
        actions += ' <a href="/share/' + hl.share_token + '" target="_blank" class="text-xs text-indigo-500 hover:text-indigo-700">\uD83D\uDCE4 Share</a>';
    }
    actions += '</div>';

    return '<div class="px-3 py-2.5 rounded-lg text-sm border ' + cls + '">' +
        '<p class="text-primary leading-relaxed ' + (isCurrent ? 'font-medium' : '') + '">' + window.escapeHtml(text) + '</p>' +
        '<div class="text-xs text-muted mt-0.5">' +
        (hl.highlighted_at || '') + pageInfo +
        '</div>' + actions +
        '</div>';
}
```

**Verification:** Open `/review`, click 📖 Context on a highlight that has other highlights from the same book. Each context item shows 📋 Copy and 📤 Share buttons.

---

### Task 7: Verify and test

**Objective:** Confirm all four views have working copy buttons and context modals show actionable items.

**Verification checklist:**
- [ ] Highlights page — expanded row has 📋 Copy, click copies text
- [ ] Highlights page — mobile card detail has 📋 Copy
- [ ] Review page — secondary actions include 📋 Copy
- [ ] Share page — standalone page shows 📋 Copy Text button, works with inline feedback
- [ ] Context modal (highlights) — each item shows 📋 Copy and 📤 Share (if token exists)
- [ ] Context modal (review) — each item shows 📋 Copy and 📤 Share
- [ ] Toast shows "Highlight copied!" on success
- [ ] Toast shows error message if clipboard unavailable
- [ ] CSP safety — no inline script tags, all through `data-action` delegation or `onclick` on the share page (standalone, not CSP-restricted)

---

## Files Changed Summary

| File | Change |
|------|--------|
| `app/static/commonplace.js` | Add `copyText()` function, update `contextItemHtml()`, update `contextModalItem()`, add data-action handler for `copy-text` |
| `app/templates/highlights.html` | Add 📋 Copy button to desktop expanded row and mobile card detail |
| `app/templates/review.html` | Add 📋 Copy button to secondary actions |
| `app/templates/share.html` | Add 📋 Copy Text button with inline confirmation |

## Risks & Tradeoffs

- **Text escaping in context items** — When embedding `hl.text` in an inline `onclick` handler, it must be properly escaped to prevent XSS. Using `window.escapeHtml()` handles HTML entities, but single quotes in the text could break the `onclick` attribute. Mitigation: use `replace(/'/g, "\\'")` on the text before embedding in the single-quoted onclick. This applies only to dynamically rendered context items (Tasks 5-6) — not to the Jinja2-rendered copy buttons (Tasks 2-4).
- **Share page is standalone** — No base.html, no toast system, no CSRF protection needed (public page). The inline `onclick` handler and a simple DOM text update are appropriate there.
- **Share token may not exist** — Older highlights may not have a `share_token`. The Share button only renders when `hl.share_token` is truthy. Copy always works.
- **Large highlight text** — `navigator.clipboard.writeText()` can handle strings up to ~1MB. Highlight text is typically <10KB. No issue.

## Open Questions

- None for the clipboard section. The spec is clear.
