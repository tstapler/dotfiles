---
name: ui-design-system
description: Generate a complete design system for any product type. Use when building UI, choosing colors/fonts/styles, or starting any frontend project.
---

# UI/UX Pro Max — Design Intelligence (No-Install Version)

Comprehensive design guide for web and mobile applications. Contains 50+ styles, 161 color palettes, 57 font pairings, 161 product types with reasoning rules, 99 UX guidelines, and 25 chart types across 10 technology stacks.

> **Source**: Adapted from [nextlevelbuilder/ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) (MIT). Python script replaced with inline reasoning. All UX rules preserved verbatim.

## When to Apply

This Skill should be used when the task involves **UI structure, visual design decisions, interaction patterns, or user experience quality control**.

### Must Use

- Designing new pages (Landing Page, Dashboard, Admin, SaaS, Mobile App)
- Creating or refactoring UI components (buttons, modals, forms, tables, charts, etc.)
- Choosing color schemes, typography systems, spacing standards, or layout systems
- Reviewing UI code for user experience, accessibility, or visual consistency
- Implementing navigation structures, animations, or responsive behavior
- Making product-level design decisions (style, information hierarchy, brand expression)
- Improving perceived quality, clarity, or usability of interfaces

### Skip

- Pure backend logic, API/database design, infrastructure, or DevOps work

**Decision criteria**: If the task will change how a feature **looks, feels, moves, or is interacted with**, this Skill should be used.

## Rule Categories by Priority

| Priority | Category | Impact | Key Checks (Must Have) | Anti-Patterns (Avoid) |
|----------|----------|--------|------------------------|------------------------|
| 1 | Accessibility | CRITICAL | Contrast 4.5:1, Alt text, Keyboard nav, Aria-labels | Removing focus rings, Icon-only buttons without labels |
| 2 | Touch & Interaction | CRITICAL | Min size 44×44px, 8px+ spacing, Loading feedback | Reliance on hover only, Instant state changes (0ms) |
| 3 | Performance | HIGH | WebP/AVIF, Lazy loading, Reserve space (CLS < 0.1) | Layout thrashing, Cumulative Layout Shift |
| 4 | Style Selection | HIGH | Match product type, Consistency, SVG icons (no emoji) | Mixing flat & skeuomorphic randomly, Emoji as icons |
| 5 | Layout & Responsive | HIGH | Mobile-first breakpoints, Viewport meta, No horizontal scroll | Horizontal scroll, Fixed px container widths, Disable zoom |
| 6 | Typography & Color | MEDIUM | Base 16px, Line-height 1.5, Semantic color tokens | Text < 12px body, Gray-on-gray, Raw hex in components |
| 7 | Animation | MEDIUM | Duration 150–300ms, Motion conveys meaning, Spatial continuity | Decorative-only animation, Animating width/height, No reduced-motion |
| 8 | Forms & Feedback | MEDIUM | Visible labels, Error near field, Helper text, Progressive disclosure | Placeholder-only label, Errors only at top, Overwhelm upfront |
| 9 | Navigation Patterns | HIGH | Predictable back, Bottom nav ≤5, Deep linking | Overloaded nav, Broken back behavior, No deep links |
| 10 | Charts & Data | LOW | Legends, Tooltips, Accessible colors | Relying on color alone to convey meaning |

## Quick Reference

### 1. Accessibility (CRITICAL)

- `color-contrast` — Minimum 4.5:1 ratio for normal text (large text 3:1)
- `focus-states` — Visible focus rings on interactive elements (2–4px)
- `alt-text` — Descriptive alt text for meaningful images
- `aria-labels` — aria-label for icon-only buttons; accessibilityLabel in native
- `keyboard-nav` — Tab order matches visual order; full keyboard support
- `form-labels` — Use label with for attribute
- `skip-links` — Skip to main content for keyboard users
- `heading-hierarchy` — Sequential h1→h6, no level skip
- `color-not-only` — Don't convey info by color alone (add icon/text)
- `dynamic-type` — Support system text scaling; avoid truncation as text grows
- `reduced-motion` — Respect prefers-reduced-motion; reduce/disable animations when requested
- `voiceover-sr` — Meaningful accessibilityLabel/accessibilityHint; logical reading order
- `escape-routes` — Provide cancel/back in modals and multi-step flows
- `keyboard-shortcuts` — Preserve system and a11y shortcuts; offer keyboard alternatives for drag-and-drop

### 2. Touch & Interaction (CRITICAL)

- `touch-target-size` — Min 44×44pt (Apple) / 48×48dp (Material); extend hit area beyond visual bounds if needed
- `touch-spacing` — Minimum 8px/8dp gap between touch targets
- `hover-vs-tap` — Use click/tap for primary interactions; don't rely on hover alone
- `loading-buttons` — Disable button during async operations; show spinner or progress
- `error-feedback` — Clear error messages near problem
- `cursor-pointer` — Add cursor-pointer to clickable elements (Web)
- `gesture-conflicts` — Avoid horizontal swipe on main content; prefer vertical scroll
- `tap-delay` — Use touch-action: manipulation to reduce 300ms delay (Web)
- `standard-gestures` — Use platform standard gestures consistently; don't redefine
- `system-gestures` — Don't block system gestures (Control Center, back swipe, etc.)
- `press-feedback` — Visual feedback on press (ripple/highlight; MD state layers)
- `haptic-feedback` — Use haptic for confirmations and important actions; avoid overuse
- `gesture-alternative` — Don't rely on gesture-only interactions; always provide visible controls
- `safe-area-awareness` — Keep primary touch targets away from notch, Dynamic Island, gesture bar
- `no-precision-required` — Avoid requiring pixel-perfect taps on small icons or thin edges
- `swipe-clarity` — Swipe actions must show clear affordance or hint (chevron, label, tutorial)
- `drag-threshold` — Use a movement threshold before starting drag to avoid accidental drags

### 3. Performance (HIGH)

- `image-optimization` — Use WebP/AVIF, responsive images (srcset/sizes), lazy load non-critical assets
- `image-dimension` — Declare width/height or use aspect-ratio to prevent layout shift (CLS)
- `font-loading` — Use font-display: swap/optional to avoid invisible text (FOIT)
- `font-preload` — Preload only critical fonts; avoid overusing preload on every variant
- `critical-css` — Prioritize above-the-fold CSS
- `lazy-loading` — Lazy load non-hero components via dynamic import / route-level splitting
- `bundle-splitting` — Split code by route/feature to reduce initial load and TTI
- `third-party-scripts` — Load third-party scripts async/defer; audit and remove unnecessary ones
- `reduce-reflows` — Avoid frequent layout reads/writes; batch DOM reads then writes
- `content-jumping` — Reserve space for async content to avoid layout jumps (CLS)
- `lazy-load-below-fold` — Use loading="lazy" for below-the-fold images and heavy media
- `virtualize-lists` — Virtualize lists with 50+ items
- `main-thread-budget` — Keep per-frame work under ~16ms for 60fps; move heavy tasks off main thread
- `progressive-loading` — Use skeleton screens / shimmer instead of long blocking spinners for >1s operations
- `input-latency` — Keep input latency under ~100ms for taps/scrolls
- `debounce-throttle` — Use debounce/throttle for high-frequency events (scroll, resize, input)
- `offline-support` — Provide offline state messaging and basic fallback (PWA / mobile)
- `network-fallback` — Offer degraded modes for slow networks (lower-res images, fewer animations)

### 4. Style Selection (HIGH)

- `style-match` — Match style to product type (see Design System Reasoning below)
- `consistency` — Use same style across all pages
- `no-emoji-icons` — Use SVG icons (Heroicons, Lucide), not emojis
- `color-palette-from-product` — Choose palette from product/industry
- `effects-match-style` — Shadows, blur, radius aligned with chosen style
- `platform-adaptive` — Respect platform idioms (iOS HIG vs Material)
- `state-clarity` — Make hover/pressed/disabled states visually distinct
- `elevation-consistent` — Use a consistent elevation/shadow scale
- `dark-mode-pairing` — Design light/dark variants together
- `icon-style-consistent` — Use one icon set/visual language across the product
- `system-controls` — Prefer native/system controls over fully custom ones
- `blur-purpose` — Use blur to indicate background dismissal (modals, sheets), not as decoration
- `primary-action` — Each screen should have only one primary CTA; secondary actions visually subordinate

### 5. Layout & Responsive (HIGH)

- `viewport-meta` — width=device-width initial-scale=1 (never disable zoom)
- `mobile-first` — Design mobile-first, then scale up to tablet and desktop
- `breakpoint-consistency` — Use systematic breakpoints (375 / 768 / 1024 / 1440)
- `readable-font-size` — Minimum 16px body text on mobile (avoids iOS auto-zoom)
- `line-length-control` — Mobile 35–60 chars per line; desktop 60–75 chars
- `horizontal-scroll` — No horizontal scroll on mobile
- `spacing-scale` — Use 4pt/8dp incremental spacing system (Material Design)
- `touch-density` — Keep component spacing comfortable for touch
- `container-width` — Consistent max-width on desktop (max-w-6xl / 7xl)
- `z-index-management` — Define layered z-index scale (0 / 10 / 20 / 40 / 100 / 1000)
- `fixed-element-offset` — Fixed navbar/bottom bar must reserve safe padding for underlying content
- `scroll-behavior` — Avoid nested scroll regions that interfere with the main scroll experience
- `viewport-units` — Prefer min-h-dvh over 100vh on mobile
- `orientation-support` — Keep layout readable and operable in landscape mode
- `content-priority` — Show core content first on mobile; fold or hide secondary content
- `visual-hierarchy` — Establish hierarchy via size, spacing, contrast — not color alone

### 6. Typography & Color (MEDIUM)

- `line-height` — Use 1.5-1.75 for body text
- `line-length` — Limit to 65-75 characters per line
- `font-pairing` — Match heading/body font personalities
- `font-scale` — Consistent type scale (e.g. 12 14 16 18 24 32)
- `contrast-readability` — Darker text on light backgrounds (e.g. slate-900 on white)
- `text-styles-system` — Use platform type system: iOS Dynamic Type / Material 5 type roles
- `weight-hierarchy` — Bold headings (600–700), Regular body (400), Medium labels (500)
- `color-semantic` — Define semantic color tokens (primary, secondary, error, surface, on-surface) not raw hex
- `color-dark-mode` — Dark mode uses desaturated / lighter tonal variants, not inverted colors
- `color-accessible-pairs` — Foreground/background pairs must meet 4.5:1 (AA) or 7:1 (AAA)
- `color-not-decorative-only` — Functional color (error red, success green) must include icon/text
- `truncation-strategy` — Prefer wrapping over truncation; when truncating use ellipsis and provide full text via tooltip
- `number-tabular` — Use tabular/monospaced figures for data columns, prices, and timers
- `whitespace-balance` — Use whitespace intentionally to group related items and separate sections

### 7. Animation (MEDIUM)

- `duration-timing` — Use 150–300ms for micro-interactions; complex transitions ≤400ms; avoid >500ms
- `transform-performance` — Use transform/opacity only; avoid animating width/height/top/left
- `loading-states` — Show skeleton or progress indicator when loading exceeds 300ms
- `excessive-motion` — Animate 1-2 key elements per view max
- `easing` — Use ease-out for entering, ease-in for exiting; avoid linear for UI transitions
- `motion-meaning` — Every animation must express a cause-effect relationship, not just be decorative
- `state-transition` — State changes should animate smoothly, not snap
- `continuity` — Page/screen transitions should maintain spatial continuity
- `spring-physics` — Prefer spring/physics-based curves over linear for natural feel
- `exit-faster-than-enter` — Exit animations shorter than enter (~60–70% of enter duration)
- `stagger-sequence` — Stagger list/grid item entrance by 30–50ms per item
- `shared-element-transition` — Use shared element / hero transitions for visual continuity
- `interruptible` — Animations must be interruptible; user tap/gesture cancels in-progress animation
- `no-blocking-animation` — Never block user input during an animation
- `scale-feedback` — Subtle scale (0.95–1.05) on press for tappable cards/buttons
- `motion-consistency` — Unify duration/easing tokens globally
- `modal-motion` — Modals/sheets should animate from their trigger source
- `navigation-direction` — Forward navigation animates left/up; backward animates right/down
- `layout-shift-avoid` — Animations must not cause layout reflow or CLS; use transform for position changes

### 8. Forms & Feedback (MEDIUM)

- `input-labels` — Visible label per input (not placeholder-only)
- `error-placement` — Show error below the related field
- `submit-feedback` — Loading then success/error state on submit
- `required-indicators` — Mark required fields (e.g. asterisk)
- `empty-states` — Helpful message and action when no content
- `toast-dismiss` — Auto-dismiss toasts in 3-5s
- `confirmation-dialogs` — Confirm before destructive actions
- `input-helper-text` — Provide persistent helper text below complex inputs
- `disabled-states` — Disabled elements use reduced opacity (0.38–0.5) + cursor change + semantic attribute
- `progressive-disclosure` — Reveal complex options progressively; don't overwhelm users upfront
- `inline-validation` — Validate on blur (not keystroke); show error only after user finishes input
- `input-type-keyboard` — Use semantic input types (email, tel, number) to trigger correct mobile keyboard
- `password-toggle` — Provide show/hide toggle for password fields
- `autofill-support` — Use autocomplete / textContentType attributes for system autofill
- `undo-support` — Allow undo for destructive or bulk actions
- `success-feedback` — Confirm completed actions with brief visual feedback
- `error-recovery` — Error messages must include a clear recovery path (retry, edit, help link)
- `multi-step-progress` — Multi-step flows show step indicator or progress bar; allow back navigation
- `error-clarity` — Error messages must state cause + how to fix (not just "Invalid input")
- `focus-management` — After submit error, auto-focus the first invalid field
- `error-summary` — For multiple errors, show summary at top with anchor links to each field
- `touch-friendly-input` — Mobile input height ≥44px
- `destructive-emphasis` — Destructive actions use semantic danger color (red) and are visually separated
- `toast-accessibility` — Toasts must not steal focus; use aria-live="polite" for screen reader announcement
- `aria-live-errors` — Form errors use aria-live region or role="alert" to notify screen readers

### 9. Navigation Patterns (HIGH)

- `bottom-nav-limit` — Bottom navigation max 5 items; use labels with icons
- `drawer-usage` — Use drawer/sidebar for secondary navigation, not primary actions
- `back-behavior` — Back navigation must be predictable and consistent; preserve scroll/state
- `deep-linking` — All key screens must be reachable via deep link / URL
- `tab-bar-ios` — iOS: use bottom Tab Bar for top-level navigation
- `top-app-bar-android` — Android: use Top App Bar with navigation icon for primary structure
- `nav-label-icon` — Navigation items must have both icon and text label
- `nav-state-active` — Current location must be visually highlighted in navigation
- `nav-hierarchy` — Primary nav vs secondary nav must be clearly separated
- `modal-escape` — Modals and sheets must offer a clear close/dismiss affordance
- `search-accessible` — Search must be easily reachable; provide recent/suggested queries
- `breadcrumb-web` — Web: use breadcrumbs for 3+ level deep hierarchies
- `state-preservation` — Navigating back must restore previous scroll position, filter state, and input
- `gesture-nav-support` — Support system gesture navigation (iOS swipe-back, Android predictive back)
- `adaptive-navigation` — Large screens (≥1024px) prefer sidebar; small screens use bottom/top nav
- `navigation-consistency` — Navigation placement must stay the same across all pages
- `avoid-mixed-patterns` — Don't mix Tab + Sidebar + Bottom Nav at the same hierarchy level
- `modal-vs-navigation` — Modals must not be used for primary navigation flows
- `focus-on-route-change` — After page transition, move focus to main content region for screen reader users
- `persistent-nav` — Core navigation must remain reachable from deep pages
- `destructive-nav-separation` — Dangerous actions must be visually and spatially separated from normal nav items

### 10. Charts & Data (LOW)

- `chart-type` — Match chart type to data type (trend → line, comparison → bar, proportion → pie/donut)
- `color-guidance` — Use accessible color palettes; avoid red/green only pairs for colorblind users
- `data-table` — Provide table alternative for accessibility; charts alone are not screen-reader friendly
- `pattern-texture` — Supplement color with patterns, textures, or shapes
- `legend-visible` — Always show legend; position near the chart
- `tooltip-on-interact` — Provide tooltips/data labels on hover (Web) or tap (mobile)
- `axis-labels` — Label axes with units and readable scale
- `responsive-chart` — Charts must reflow or simplify on small screens
- `empty-data-state` — Show meaningful empty state when no data exists
- `loading-chart` — Use skeleton or shimmer placeholder while chart data loads
- `animation-optional` — Chart entrance animations must respect prefers-reduced-motion
- `large-dataset` — For 1000+ data points, aggregate or sample; provide drill-down for detail
- `number-formatting` — Use locale-aware formatting for numbers, dates, currencies
- `touch-target-chart` — Interactive chart elements (points, segments) must have ≥44pt tap area
- `no-pie-overuse` — Avoid pie/donut for >5 categories; switch to bar chart for clarity
- `legend-interactive` — Legends should be clickable to toggle series visibility
- `direct-labeling` — For small datasets, label values directly on the chart
- `sortable-table` — Data tables must support sorting with aria-sort indicating current sort state
- `screen-reader-summary` — Provide a text summary or aria-label describing the chart's key insight

---

## How to Use This Skill

### Workflow by Scenario

| Scenario | Trigger | Start From |
|----------|---------|------------|
| New project / page | "Build a landing page", "Build a dashboard" | Step 1 → Step 2 (design system) |
| New component | "Create a pricing card", "Add a modal" | Quick Reference relevant section |
| Choose style / color / font | "What style fits a fintech app?" | Step 2 (design system reasoning) |
| Review existing UI | "Review this page for UX issues" | Quick Reference §1-§3 checklist |
| Fix a UI bug | "Button hover is broken", "Layout shifts on load" | Quick Reference → relevant section |
| Improve / optimize | "Make this faster", "Improve mobile experience" | Quick Reference §3 (performance) |
| Add charts / data viz | "Add an analytics dashboard chart" | Quick Reference §10 |

---

### Step 1: Analyze User Requirements

Extract from the user request:
- **Product type**: SaaS, e-commerce, healthcare, portfolio, food, finance, gaming, etc.
- **Target audience**: Consumer vs. B2B, age group, usage context
- **Style keywords**: playful, vibrant, minimal, dark, content-first, luxury, etc.
- **Tech stack**: React/Next.js, Tailwind, Vue, SwiftUI, React Native, Flutter, etc.

---

### Step 2: Generate Design System (REQUIRED)

Generate a complete design system through structured reasoning. Always do this before writing UI code. Output it in this format:

```
+------------------------------------------------------------------+
|  TARGET: [Project Name] - RECOMMENDED DESIGN SYSTEM             |
+------------------------------------------------------------------+
|                                                                  |
|  PATTERN: [Landing page / layout pattern]                        |
|     Why: [1-line rationale]                                      |
|     CTA: [placement strategy]                                    |
|     Sections: [ordered list of page sections]                   |
|                                                                  |
|  STYLE: [Style name]                                             |
|     Keywords: [mood descriptors]                                 |
|     Best For: [product categories]                               |
|     Performance: Excellent/Good | Accessibility: WCAG AA/AAA     |
|                                                                  |
|  COLORS:                                                         |
|     Primary:    #XXXXXX ([name])                                 |
|     Secondary:  #XXXXXX ([name])                                 |
|     CTA:        #XXXXXX ([name])                                 |
|     Background: #XXXXXX ([name])                                 |
|     Text:       #XXXXXX ([name])                                 |
|     Notes: [palette rationale + contrast check]                  |
|                                                                  |
|  TYPOGRAPHY: [Heading Font] / [Body Font]                        |
|     Mood: [personality descriptors]                              |
|     Best For: [product categories]                               |
|     Google Fonts: https://fonts.google.com/share?selection...    |
|                                                                  |
|  KEY EFFECTS:                                                    |
|     [Effect 1] + [Effect 2] + [Effect 3]                         |
|                                                                  |
|  AVOID (Anti-patterns):                                          |
|     [Anti-pattern 1] + [Anti-pattern 2] + [Anti-pattern 3]      |
|                                                                  |
|  PRE-DELIVERY CHECKLIST:                                         |
|     [ ] No emojis as icons (use SVG: Heroicons/Lucide)           |
|     [ ] cursor-pointer on all clickable elements                 |
|     [ ] Hover states with smooth transitions (150-300ms)         |
|     [ ] Light mode: text contrast 4.5:1 minimum                  |
|     [ ] Focus states visible for keyboard nav                    |
|     [ ] prefers-reduced-motion respected                         |
|     [ ] Responsive: 375px, 768px, 1024px, 1440px                 |
|                                                                  |
+------------------------------------------------------------------+
```

**Reasoning rules** (apply in order):

**PATTERN** — Match product type to landing page pattern:
- SaaS/Tool → Feature-Rich Showcase or Interactive Product Demo
- Service/Consulting/B2B → Trust & Authority or Social Proof-Focused
- Consumer product → Hero-Centric or Conversion-Optimized
- Creative/Agency/Portfolio → Storytelling-Driven or Minimal & Direct
- Simple app/MVP → Minimal & Direct

**STYLE** — Match to industry (apply `style-match` rule from §4):
- Wellness / Beauty / Spa → Soft UI Evolution, Neumorphism
- SaaS / Tech / AI → Glassmorphism, Minimalism, AI-Native UI
- Finance / Banking / Legal → Minimalism, Swiss Modernism 2.0 (no AI gradients, no neon)
- Healthcare / Medical → Accessible & Ethical, Soft UI Evolution (no dark mode)
- Gaming / Entertainment → Cyberpunk UI, Dark Mode (OLED), Vibrant & Block-based
- E-commerce / Retail → Flat Design, Claymorphism, Conversion-Optimized
- Portfolio / Creative Agency → Brutalism, Neubrutalism, Motion-Driven, Editorial Grid
- Food / Restaurant → Organic Biophilic, Skeuomorphism (warm palettes)
- Education / Children → Claymorphism, Flat Design (high contrast, friendly)
- NFT / Web3 / Crypto → Cyberpunk UI, Dark Mode, Aurora UI

**COLORS** — Apply `color-semantic` rule from §6 (industry mood):
- Wellness: soft pinks (#E8B4B8), sage greens (#A8D5BA), warm whites, gold accents
- Finance: deep navy (#1A2B4B), cool grays, minimal accent (trust blue or green)
- Healthcare: clinical white, trust blue (#4A90D9), soft green (#6BB18E)
- Tech/SaaS (light): crisp white, electric blue (#2563EB) or violet, dark text
- Tech/SaaS (dark): near-black (#0F0F0F), neon accent (#00D4FF or #7C3AED)
- Food: warm orange (#E07A5F), cream (#FFF8F0), rich brown, appetizing reds
- Creative/Portfolio: high contrast, bold primary, minimal palette
- Always verify 4.5:1 contrast ratio for body text; NEVER use gray-on-gray

**TYPOGRAPHY** — Select Google Fonts pairing matching the style mood:
- Luxury / Wellness: Cormorant Garamond + Montserrat (elegant, calming)
- Modern SaaS / Startup: Inter + Inter (clean, scales well)
- Editorial / Blog: Playfair Display + Source Sans Pro (authoritative, readable)
- Friendly / Consumer / App: DM Sans + DM Serif Display (warm, approachable)
- Technical / Dev Tool: JetBrains Mono + Inter (precise, professional)
- Bold / Agency: Cabinet Grotesk + Satoshi (contemporary, strong)
- Children / Playful: Nunito + Nunito (rounded, friendly)

**ANTI-PATTERNS** — Apply industry-specific exclusions:
- Banking/Finance: no AI purple/pink gradients, no neon, no playful rounded corners
- Healthcare: no aggressive animations, no dark mode (accessibility concern), no neon
- Children's apps: no adult color schemes, no harsh contrast, no dense typography
- Enterprise B2B: no glassmorphism overuse, no decorative animations, no brutalism

---

### Step 2b: Persist Design System (MASTER.md + Overrides)

Save the design system for cross-session consistency by creating these files:

**`design-system/MASTER.md`** — Global Source of Truth (colors, typography, spacing, components)

**`design-system/pages/[page-name].md`** — Page-specific overrides (deviations from Master only)

**Context-aware retrieval prompt** (use this at the start of each implementation session):
```
I am building the [Page Name] page. Please read design-system/MASTER.md.
Also check if design-system/pages/[page-name].md exists.
If the page file exists, prioritize its rules.
If not, use the Master rules exclusively.
Now, generate the code...
```

---

### Step 3: Apply Detailed Guidelines (As Needed)

Reference the Quick Reference sections above directly — no search script needed:

| Need | Reference |
|------|-----------|
| Accessibility audit | Quick Reference §1 |
| Touch/interaction review | Quick Reference §2 |
| Performance checklist | Quick Reference §3 |
| Style / color decisions | Quick Reference §4 + Step 2 reasoning |
| Layout / responsive issues | Quick Reference §5 |
| Typography / color rules | Quick Reference §6 |
| Animation timing | Quick Reference §7 |
| Form UX | Quick Reference §8 |
| Navigation structure | Quick Reference §9 |
| Charts / dashboards | Quick Reference §10 |

---

### Step 4: Stack-Specific Guidelines

For React / Next.js performance: use the **`ui-react-best-practices`** skill
For web accessibility / UI audit: use the **`ui-web-design-guidelines`** skill
For React component architecture: use the **`ui-composition-patterns`** skill

For SwiftUI / iOS: apply Apple HIG rules from §1-§9 (all `(Apple HIG)` annotations)
For Jetpack Compose / Android: apply Material Design rules from §1-§9 (all `(MD)` annotations)
For React Native: apply both HIG + Material annotations + `touch-target-size` (§2) strictly

---

## Common Rules for Professional UI

These are frequently overlooked issues that make UI look unprofessional.

### Icons & Visual Elements

| Rule | Standard | Avoid | Why It Matters |
|------|----------|--------|----------------|
| **No Emoji as Structural Icons** | Use vector-based icons (Lucide, Heroicons, react-native-vector-icons) | Using emojis (🎨 🚀 ⚙️) for navigation or system controls | Emojis are font-dependent, inconsistent across platforms, and can't be design-token controlled |
| **Vector-Only Assets** | Use SVG or platform vector icons | Raster PNG icons | Ensures scalability, crisp rendering, and dark/light mode adaptability |
| **Consistent Icon Sizing** | Define icon sizes as design tokens (icon-sm, icon-md = 24pt, icon-lg) | Mixing arbitrary values like 20pt / 24pt / 28pt randomly | Maintains rhythm and visual hierarchy |
| **Stroke Consistency** | Use a consistent stroke width (e.g., 1.5px or 2px) | Mixing thick and thin stroke styles | Inconsistent strokes reduce perceived polish |
| **Filled vs Outline Discipline** | Use one icon style per hierarchy level | Mixing filled and outline icons at the same level | Maintains semantic clarity |
| **Touch Target Minimum** | Minimum 44×44pt interactive area | Small icons without expanded tap area | Meets accessibility and platform standards |

### Light/Dark Mode Contrast

| Rule | Do | Don't |
|------|----|----- |
| **Surface readability (light)** | Keep cards/surfaces clearly separated from background | Overly transparent surfaces that blur hierarchy |
| **Text contrast (light)** | Maintain body text contrast ≥4.5:1 against light surfaces | Low-contrast gray body text |
| **Text contrast (dark)** | Maintain primary text contrast ≥4.5:1 and secondary text ≥3:1 | Dark mode text that blends into background |
| **Token-driven theming** | Use semantic color tokens mapped per theme | Hardcoded per-screen hex values |
| **Scrim and modal legibility** | Modal scrim 40-60% black | Weak scrim that leaves background competing |

### Layout & Spacing

| Rule | Do | Don't |
|------|----|----- |
| **Safe-area compliance** | Respect top/bottom safe areas for all fixed headers, tab bars | Placing fixed UI under notch, status bar, or gesture area |
| **8dp spacing rhythm** | Use consistent 4/8dp system for padding/gaps/section spacing | Random spacing increments with no rhythm |
| **Section spacing hierarchy** | Define vertical rhythm tiers (e.g., 16/24/32/48) by hierarchy | Similar UI levels with inconsistent spacing |
| **Scroll and fixed element coexistence** | Add bottom/top content insets so lists don't hide behind fixed bars | Scroll content obscured by sticky headers/footers |

---

## Pre-Delivery Checklist

Run through **§1–§3** (CRITICAL + HIGH) as a final review before any UI delivery.

### Visual Quality
- [ ] No emojis used as icons (use SVG instead)
- [ ] All icons come from a consistent icon family and style
- [ ] Semantic theme tokens are used consistently (no ad-hoc per-screen hardcoded colors)
- [ ] Pressed-state visuals do not shift layout bounds or cause jitter

### Interaction
- [ ] All tappable elements provide clear pressed feedback
- [ ] Touch targets meet minimum size (≥44×44pt iOS, ≥48×48dp Android)
- [ ] Micro-interaction timing stays in the 150-300ms range
- [ ] Disabled states are visually clear and non-interactive
- [ ] Screen reader focus order matches visual order, and interactive labels are descriptive

### Light/Dark Mode
- [ ] Primary text contrast ≥4.5:1 in both light and dark mode
- [ ] Secondary text contrast ≥3:1 in both light and dark mode
- [ ] Both themes are tested before delivery (not inferred from a single theme)

### Layout
- [ ] Safe areas are respected for headers, tab bars, and bottom CTA bars
- [ ] Scroll content is not hidden behind fixed/sticky bars
- [ ] Verified on small phone (375px), large phone, and tablet (portrait + landscape)
- [ ] 4/8dp spacing rhythm is maintained across component, section, and page levels
- [ ] Responsive breakpoints tested: 375px, 768px, 1024px, 1440px

### Accessibility
- [ ] All meaningful images/icons have accessibility labels
- [ ] Form fields have labels, hints, and clear error messages
- [ ] Color is not the only indicator
- [ ] Reduced motion and dynamic text size are supported without layout breakage
- [ ] Focus states visible for keyboard navigation

---

## Common Sticking Points

| Problem | Quick Reference Section |
|---------|------------------------|
| Can't decide on style/color | Step 2 design system reasoning |
| Dark mode contrast issues | §6: `color-dark-mode` + `color-accessible-pairs` |
| Animations feel unnatural | §7: `spring-physics` + `easing` + `exit-faster-than-enter` |
| Form UX is poor | §8: `inline-validation` + `error-clarity` + `focus-management` |
| Navigation feels confusing | §9: `nav-hierarchy` + `bottom-nav-limit` + `back-behavior` |
| Layout breaks on small screens | §5: `mobile-first` + `breakpoint-consistency` |
| Performance / jank | §3: `virtualize-lists` + `main-thread-budget` + `debounce-throttle` |
