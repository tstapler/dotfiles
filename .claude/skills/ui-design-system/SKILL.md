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

The Rule Categories table above gives the priority and headline checks/anti-patterns per
category. For the complete rule list — every named rule (`color-contrast`, `touch-target-size`,
`spring-physics`, etc.) with its full description, organized under the same §1–§10 numbering
used throughout this skill — see [Quick Reference: Full Rule Lists](references/rules-quick-reference.md).

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

**Reasoning rules** (apply in order: PATTERN → STYLE → COLORS → TYPOGRAPHY → ANTI-PATTERNS): match product type to a landing-page pattern (e.g. SaaS/Tool → Feature-Rich Showcase), match industry to a style per the `style-match` rule (§4), pick colors per the `color-semantic` rule (§6), select a Google Fonts pairing for the style mood, then apply industry-specific anti-pattern exclusions (e.g. no dark mode for healthcare, no glassmorphism overuse for enterprise B2B).

See [Design System Reasoning Rules](references/design-system-reasoning.md) for the full per-industry mapping tables (pattern, style, hex color values, font pairings, and anti-pattern exclusions for wellness, finance, healthcare, tech/SaaS, food, creative, children's, gaming/Web3, and enterprise).

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

---

## Related Skills

| Skill | When to apply |
|-------|--------------|
| `ui-react-best-practices` | Optimize React/Next.js performance after the design system is defined |
| `ui-web-design-guidelines` | Audit UI code against 100+ web best practices and accessibility rules |
| `ui-composition-patterns` | Build flexible React component APIs that implement design system tokens |
| `ui-android-ux-design` | Apply Material Design 3 specifics when the stack targets Android/Compose |
| `ui-frontend-design` | Create visually distinctive interfaces that embody the design system |
| `pm-brand-guidelines` | Enforce brand color, typography, and logo rules within the design system |
