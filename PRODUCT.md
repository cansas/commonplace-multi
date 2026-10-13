# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Household readers: family or small-team members who each keep their own highlight library on one self-hosted instance. Each person captures highlights while reading and comes back later to re-read them. One of them (user_id 1) also operates the server and invites the others.

## Product Purpose

A self-hosted home for reading highlights: capture them from whatever reader or reading app you already use, keep them in one searchable place, and return to them on a daily review rhythm. Success means a library that stays yours, stays readable years later, and actually gets re-read instead of merely accumulated.

## Positioning

Data ownership as the product, not a feature flag: everything lives on the operator's own box, one container and one SQLite file, no external service in the path, and no public signup (an admin invites each account). Readwise-class capture and review without the hosted dependency.

## Operating Context

- Runs as a single Docker container on the operator's own server (Unraid in this household), SQLite, with `data/` holding the database and covers.
- Highlights arrive from KOReader (sync plugin), Kindle clippings, Obsidian, the Readwise-compatible import API, BookOrbit, Readeck, and Readest.
- Daily use is a review ritual: a queue of highlights, current and best streaks, a heatmap, achievements, and Web Push reminders when a streak is at risk.
- Accounts are provisioned by invitation from `/admin/users`. The first account (user_id 1) is the operator and is treated as admin.
- Reading happens on phones and e-readers as much as on desktop, so the app is also a PWA.

## Capabilities and Constraints

- Confirmed: invite-only multi-user with per-user isolation of highlights, reviews, tags, streaks, achievements, and push subscriptions; highlight CRUD and full-text search; books view with covers from HardCover.app and Open Library; tag management; import and export; ZIP backup and restore; PNG/SVG share cards; BookOrbit/Readeck/Readest sync with SHA256 dedupe; Web Push via VAPID; web first-run wizard.
- Browser-first stack with no build step: Jinja templates in `app/templates/`, hand-written CSS in `app/static/style.css` and `app/static/themes.css`, Tailwind served as a checked-in `app/static/tailwind.min.js`, vanilla JS in `app/static/commonplace.js`. Keep it that way; adding an npm toolchain is out of scope unless explicitly requested.
- Theming runs on CSS custom properties in `app/static/themes.css`. A theme is a token block, not a component rewrite (`THEMES.md`).
- Three built-in themes are first-class and must be checked together in any UI change: Modern (`.theme-modern`), Reader (`.theme-reader`), Dark (`.theme-dark`). None may drift.
- UI changes stay portable to upstream `cansas/commonplace`: minimal divergence, and fixes are expected to land in both repos.
- Platform is web only. There is no native app; the PWA is mobile web.
- Assumed, not confirmed by the operator: token names in `themes.css` are a public contract, because a user can drop a custom theme into `data/themes/` or upload one from Settings, so renaming or removing a variable can break a theme nobody here wrote.
- Open decision: no product-specific accessibility standard has been set. See below.

## Brand Commitments

- Name: "commonplace", lowercase in the interface. Shell tagline: "Self-hosted highlights" (`app/templates/base.html:46`).
- Logo assets are checked in as `app/static/logo.png`, `logo-32.png`, `logo-64.png`, `logo-128.png`, `logo-white-bg.png`, used in the sidebar, the mobile header, and the favicons.
- The name carries the commonplace-book idea: a personal collection of passages worth keeping. Copy stays in that register, not in SaaS-marketing register.
- License is MIT No Attribution. The project is a fork of `cansas/commonplace` and documents itself as such in the README.
- The incumbent visual system is the design authority. `DESIGN.md` was never written; that is a documentation gap, not permission to replace the look.

## Evidence on Hand

- Reference captures of the running app in `screenshots/`: homescreen, daily review, settings in modern and dark, import.
- Product and API documentation: `README.md`, `API.md`, `ENV.md`, `INSTALL.md`, `THEMES.md`, `CONTRIBUTING.md`.
- Real data on the operator's live instance: a personal highlight library spread across several accounts. There are no testimonials, press mentions, or benchmarks, and none may be invented.

## Product Principles

1. The library is the user's; the app is only a caretaker. Data paths (backup, export, restore) are protected by default and nothing phones home.
2. Capture from where reading already happens. No feature may require a reader to change tools or re-type a highlight.
3. Re-reading beats accumulating. Review, streaks, and achievements exist to bring people back to what they saved.
4. One box, one file, few moving parts. Prefer the boring, self-contained option over the clever dependency.
5. A household server, not a SaaS. Invite-only, isolated accounts, no growth mechanics, no public surface.

## Accessibility & Inclusion

No product-specific accessibility standard is recorded yet; this is an open decision. What the app shell now guarantees: three text steps that clear 4.5:1 on their own surface in all six themes, an authored 2px accent focus ring on every interactive control, themed caret, placeholder and selection, and drawn SVG chrome icons marked `aria-hidden` next to real text labels. Still open and to be treated as audit findings elsewhere: one `aria-label` across all templates, no `prefers-reduced-motion` handling anywhere, unlabelled icon-only controls outside the shell, and 9px functional text in the highlights actions.
