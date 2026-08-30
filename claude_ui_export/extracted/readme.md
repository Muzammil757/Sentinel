# Sentinel — Operations · Design System

Sentinel is an **AI governance and decision-control console for high-stakes automated operations**. It sits between what AI agents recommend and what actually executes in the world. An administrator opening Sentinel should be able to answer four questions in seconds: *what needs my attention, why was this decided, did it execute, and does a human need to look at it.*

The system is built to feel like premium fintech **infrastructure** — precise, restrained, technical, operational — not a SaaS admin dashboard. Signal over volume: a small number of meaningful cases, dense-but-readable rows, hairline structure, one accent colour, and status semantics that never lie.

## Sources

No design sources were supplied for this build — no codebase, no Figma file, no deck, no logo, no font binaries. Everything here is derived from the written brief ("Sentinel — Operations", AI governance / decision-control console, premium fintech-infrastructure feel, Razorpay-ecosystem level of polish). **Substitutions made, all flagged:**

- **Typeface** — IBM Plex Sans + IBM Plex Mono, loaded from Google Fonts (`tokens/fonts.css`). Nearest available match to a precise technical grotesque with a strong tabular mono companion. Swap in the real brand font by replacing that one file.
- **Icons** — Lucide, loaded per-glyph from `unpkg.com/lucide-static` as CSS masks (`components/core/Icon.jsx`). No brand icon set existed to copy in.
- **Logo** — none supplied, and none invented. The brand appears as a wordmark set in type (see `guidelines/brand-wordmark.html`). `assets/` is intentionally empty of marks.

If you have the real fonts, logo, or icon set, drop them in and this system will absorb them with no structural change.

## Core concepts (the product vocabulary)

**Case** — one automated action under governance. **Agent disagreement / Conflict** — two or more agents proposing incompatible positions. **Candidate options** — the discrete choices produced during **WEIGH**. **GOVERN** — the decision authority that allows, blocks or escalates. **Execution** — the real-world call, which only happens if GOVERN allowed it. **Human review** — an *annotation* workflow. **Audit trail** — append-only record. **System reliability** — whether the control plane itself is healthy.

**Hard rule, encoded in the components:** human review annotates. It never approves, overrides, retries, or authorises execution. `DecisionSummary.decidedBy` must always be a system authority; every review surface carries an explicit authority notice (`InlineNotice tone="neutral" icon="lock"`).

---

## CONTENT FUNDAMENTALS

**Voice.** A flight recorder that can write. Declarative, past tense for what happened, present tense for what is true now. Never chatty, never reassuring, never apologetic.

**Structure of a message: what happened → why → effect.**
- "Execution blocked before any external call." → "Amount exceeds the vendor ceiling by 41%." → "No payout request was issued."
- Not: "Uh oh! We couldn't process this payout 😔"

**Person.** Mostly impersonal — the subject is the system, not the reader ("Execution blocked", "Routed to human review"). Second person only when describing the reader's own authority: "You are annotating, not deciding." First person plural is never used; Sentinel does not say "we".

**Casing.** Sentence case for everything a human reads: titles, buttons, descriptions. UPPERCASE only in two places: the 11px mono eyebrow labels (`CASE`, `SURFACE`, `HUMAN REVIEW`) and status badges (`BLOCKED`, `ESCALATED`). The pipeline stages **WEIGH** and **GOVERN** are written in caps when named as authorities ("Decided by GOVERN"), sentence case as pipeline stages in a track.

**Numbers and machine values are always mono and tabular.** Ids (`CASE-2041`, `EXEC-8841`), timestamps to the millisecond in audit contexts (`14:02:14.118`) and to the minute in queues (`14:02`), policy names (`payout-v4`), scores (`0.82`), amounts (`₹18,40,000`). Never round a machine value for looks.

**Length.** Headlines one sentence. Reasons one sentence each, labelled (`TRIGGER`, `CONFLICT`, `EFFECT`). Body copy caps at ~68ch.

**Forbidden words in review surfaces:** approve, authorise, override, force, unblock, retry now. Allowed: annotate, record, note, flag for policy owner, request re-evaluation.

**Empty states are calm and factual:** "No annotations recorded." "All contributing agents agreed on the chosen option." Never celebratory ("You're all caught up! 🎉").

**Emoji: never.** Not in UI, not in copy, not in docs. Unicode is used only as structural punctuation: `·` as a separator in mono strings, `→` between pipeline stages, `/` in breadcrumbs.

---

## VISUAL FOUNDATIONS

**Colour.** One accent, everything else is ink. Signal blue (`--accent` #1C48A8) marks selection, links and the single primary action per view. The neutral is a cool graphite ramp (`--ink-*`) — surfaces are white on a #F7F8FA app field; the console/audit plane inverts to #0B0E13. Status colour is *earned*, never decorative: green allowed, amber escalated, red blocked, graphite failed, plum agent-conflict — each as a foreground/background pair (`--status-*-fg/-bg`) plus a dot. Two background colours maximum per screen (app field + surface), plus the dark plane where machine records live. No gradients anywhere. No purple-blue hero washes.

**Type.** IBM Plex Sans for language, IBM Plex Mono for machine values — the split is semantic, not aesthetic, and it is the system's strongest signal. Display 30 / title 20 / heading 16 / lead 15 / subheading 13 / body 14 / caption 12, negative tracking on everything 16px and up (`--ls-heading` −0.014em, `--ls-display` −0.022em). Labels are 11px mono uppercase at +0.08em. Weights: 400 body, 500 for emphasis and controls, 600 headings. No italics.

**Spacing & density.** 4px base with 2/6/10/14 half-steps for console density. Rows are 44px, controls 30px (36px large), panel padding 14–16px, gaps 12px inside panels and 16px between them. Compact but never cramped: line-height stays at 1.45 in body copy.

**Backgrounds & imagery.** None. No photography, no illustration, no patterns, no textures, no noise. The interface is paper-flat surfaces and lines; the only "image" is data. If a marketing surface ever needs imagery, it should be cool-toned, desaturated, and architectural — never warm stock photography of people at laptops.

**Borders and elevation.** Sentinel separates with lines, not shadows. Hairline `--border-hairline` inside lists, `--border-subtle` for container edges, `--border-strong` for control edges, `--border-emphasis` for checkbox/radio strokes. Shadows exist only for things that genuinely float: `--shadow-1` resting controls, `--shadow-2` toasts, `--shadow-popover` dialogs. Inner shadows are used once — `--shadow-hairline` as an inset outline. No coloured left-border accent cards.

**Corner radii.** 2–6px only. Controls and badges 3–4px, panels 6px, pill radius reserved strictly for status dots and switch tracks. Nothing is more rounded than 8px; nothing is a "bubble".

**Cards.** There are no cards — there is `Panel`: white surface, 1px `--border-subtle`, 6px radius, no shadow, optional 40px header with a mono eyebrow + title, optional footer in caption grey. Stat cards are replaced by `KeyValue` (label over value) and `ReliabilityMeter` (segmented bar). Nesting stops at one level.

**Status semantics.** `StatusBadge` is the only place status colour appears at full strength; a `SeverityDot` is used where a badge would shout. Selected rows get `--bg-selected` plus a 2px inset accent rule on the left — never a border box. `DecisionSummary` carries its status as a 2px top border and keeps the rest of the block neutral, so a screen full of decisions reads as structure rather than alarm.

**Interaction states.** Hover: a one-step background lift (`--bg-hover`) and text going from secondary to primary — never a colour change, never a scale. Press: one step darker (`--bg-active`, or `--accent-press` on primary buttons); no shrink, no bounce. Focus: 2px `--accent` outline at 1px offset, plus a 3px `--focus-ring` halo on text inputs. Disabled: 45% opacity, no colour change, `not-allowed` cursor. Selected: tint + inset rule. Active nav item: `--bg-active` + medium weight.

**Animation.** Functional only, 80–260ms on `--ease-standard` cubic-bezier(.2,0,.2,1). Colour and background transitions on controls; position transition on the switch knob; opacity fades for tooltips and toasts. Status colour never animates or pulses except one case: `SeverityDot pulse` for a live attention state. No entrance animations, no skeleton shimmer, no springs, no parallax.

**Transparency & blur.** Almost never. Two exceptions: the dialog scrim (`--overlay-scrim` 44% ink + 2px blur) and white-alpha borders/fills on the dark console plane (`rgba(255,255,255,.06–.14)`). No frosted panels, no translucent sidebars.

**Layout rules.** Fixed chrome: 52px dark top bar (always), 236px sidebar (always), 380px right inspector on queue views. Content maxes at 1160px. Tables are borderless grids on a panel — hairline row separators, mono right-aligned numeric columns, no zebra striping, no vertical rules. The audit trail is always full-width and always on the dark plane.

---

## ICONOGRAPHY

- **Set:** Lucide (1.5px stroke, outline, 24px grid), **substituted** — no brand icon set was provided. Please supply the real set if one exists.
- **Delivery:** each glyph is fetched as an individual SVG from `unpkg.com/lucide-static@0.469.0/icons/<name>.svg` and applied as a CSS `mask`, so it inherits `currentColor`. No sprite sheet, no icon font, no PNGs, no hand-drawn inline SVG.
- **Always via `<Icon name="…">`.** Never paste raw SVG into a screen.
- **Sizes:** 12–13px inside badges and dense rows, 14–15px in controls and nav, 16px default, 18–20px in headers. Nothing larger — Sentinel has no decorative or hero icons.
- **Colour:** icons take the colour of their context (secondary grey in nav, status foreground inside a badge). An icon is never the only carrier of meaning; it always sits beside a word.
- **Recurring glyphs and their fixed meanings:** `shield-check` govern/allowed action, `shield-x` blocked, `triangle-alert` failed, `arrow-up-right` escalated/open, `git-compare` agent disagreement, `git-branch` policy, `message-square` / `message-square-plus` human review annotation, `scroll-text` audit trail, `terminal` execution, `activity` reliability, `inbox` cases, `lock` authority boundary, `circle-slash` nothing happened, `clock` pending.
- **Emoji: never used.** Unicode marks used as glyphs: `·` `→` `/` only.

---

## Index

| Path | What it is |
| --- | --- |
| `styles.css` | Root entry — `@import` list only. Consumers link this one file. |
| `tokens/` | `fonts.css` (Google Fonts import) · `colors.css` · `typography.css` · `spacing.css` · `elevation.css` · `motion.css` · `base.css` (element resets, link colours) · `theme-dark.css` (`.sentinel-dark` — the product's real foundation) |
| `guidelines/` | 19 foundation specimen cards: Colors (ink, signal blue, status, surfaces, text, borders), Type (families, scale, body, mono, labels), Spacing (scale, radii, layout constants, density, elevation, motion), Brand (wordmark, pipeline vocabulary) |
| `components/` | Reusable primitives, grouped by concern — see below |
| `ui_kits/control_plane/` | The product surface — dark control-plane console (`index.html`): control plane, cases, decision record, human review, reliability, audit, scenario. Supersedes the earlier light `ui_kits/console/`, which was removed. |
| `assets/` | Empty — no logo or brand imagery was supplied |
| `SKILL.md` | Agent Skills manifest for use outside this project |

### Components

**core/** — `Icon`, `Button`, `IconButton`, `Badge`, `Tag`, `Tooltip`
**forms/** — `Input`, `Textarea`, `Select`, `Checkbox`, `Radio`, `Switch`
**surfaces/** — `Panel`, `SectionHeader`, `KeyValue`
**navigation/** — `SideNav`, `Tabs`
**feedback/** — `InlineNotice`, `Dialog`, `Toast`
**status/** — `StatusBadge`, `SeverityDot`, `ReliabilityMeter`
**governance/** — `PipelineTrack`, `CaseRow`, `CandidateOption`, `DecisionSummary`, `AgentDisagreement`, `AuditTrail`
**pipeline/** — `CausalChain`

Each component directory holds `<Name>.jsx`, `<Name>.d.ts`, `<Name>.prompt.md`, and one `@dsCard` HTML showing its states.

### Intentional additions

No source defined a component inventory, so the set above is authored: the standard primitive set (button, icon button, badge, tag, tooltip, input, textarea, select, checkbox, radio, switch, panel, tabs, dialog, toast, notice) plus two groups the product cannot be expressed without:

- **status/** (`StatusBadge`, `SeverityDot`, `ReliabilityMeter`) — a fixed outcome vocabulary is the point of the product; leaving it to ad-hoc colour would let outcomes drift.
- **governance/** (`PipelineTrack`, `CaseRow`, `CandidateOption`, `DecisionSummary`, `AgentDisagreement`, `AuditTrail`) — makes the WEIGH → GOVERN → Execution → Review pipeline legible and encodes the review-authority boundary so a designer cannot accidentally imply a reviewer can override GOVERN.
- **core/Icon** — a wrapper so the substituted glyph set can be swapped in one file.
- **pipeline/CausalChain** — the product's causal spine, AGENTS → CONFLICT → RESOLVE → WEIGH → GOVERN → EXECUTOR, used at three scales (command bar, case row, decision record). Without it the pipeline would be redrawn ad hoc on every screen.

---

## PRODUCT FOUNDATION: THE DARK CONTROL PLANE

The product does not run on the light theme. `.sentinel-dark` on the app root re-points every semantic token to a graphite/near-black foundation (`--bg-app` #0A0C11, surfaces #101319/#161A21), lifts the accent to electric indigo #4C7DF0, adds a teal executor accent, and brightens status hues for dark legibility. Light tokens remain the foundation for documents, print and specimen cards.

Rules specific to the control plane:
- **Near-monochrome until state requires colour.** The palette is neutral graphite (#0B0B0D app, #0F1012 surface) with warm off-white ink (#E9E7E3). The accent is a *muted steel* (#7F8CA3), used for focus and selection only — never as a fill on headers, buttons at rest, or large areas. Status hues are desaturated (sage #7FA98F allowed, ochre #C39A57 escalated, clay #C87A6C blocked, mauve #9A8FB0 conflict) so colour reads as meaning.
- **Outcomes are words, not pills.** "Blocked" in clay, "Executed" in sage. Tinted badge backgrounds are reserved for the specimen cards and light-theme contexts.
- **Three levels of disclosure, never collapsed into one screen.** Level 1 (Control plane, Cases) answers what happened and whether it needs me — five fields per row, no chain, no latencies, no policy revisions. Level 2 (Decision record) answers why, with the causal chain as the page's spine. Level 3 (closed disclosures, Audit) is forensic.
- **The chain appears at three intensities and no more:** a quiet band of stage names on the Control plane, the structural spine of the Decision record, and animated in Scenario. Never once per table row.
- **No cards.** Sections are grouped by a hairline rule, an 11px mono eyebrow and space (`Block` in the kit's `Primitives.jsx`). `Panel`, `SectionHeader`, `KeyValue`, `ReliabilityMeter`, `CandidateOption`, `DecisionSummary`, `AgentDisagreement` and `PipelineTrack` remain in the library for consumers but are absent from product screens — each was a box where type would do.
- **Navigation is one 40px bar:** brand, six surfaces with a 1px ink underline on the active one, and an attention count. No second row, no live chain in the chrome, no sidebar; contextual filtering lives inside the surface that needs it.
- **No glow.** `--glow-accent` is a 1px steel ring at most, and the product screens don't use it.
- **Colour is state.** Status hues appear only on outcome words, chain stage marks, signal dots and one chart. Nothing else is coloured.
- **Mono carries the machine.** Ids, surfaces (`payouts.settle`), policies, timestamps, scores, latencies, queue depths — all mono, tabular, never rounded.
