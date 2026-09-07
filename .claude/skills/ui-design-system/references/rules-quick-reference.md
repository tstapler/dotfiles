# Quick Reference — Full Rule Lists (§1–§10)

The complete rule set behind the `SKILL.md` priority table. Section numbers (§1–§10)
are referenced throughout `SKILL.md` and its other reference files — jump to the
matching `###` heading below.

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
