---
name: ui-android-ux-design
description: Apply Android Material Design 3 (Material You) UX best practices when implementing Android UI features, reviewing Compose code, or making design decisions for gesture navigation, edge-to-edge layout, touch targets, accessibility, and motion. Use when writing or reviewing Jetpack Compose UI code targeting Android, choosing between navigation patterns, sizing touch targets, handling system insets, or answering questions about Android-specific UX guidelines. Essential for KMP projects with Android targets.
---

# Android UX Design — Material Design 3

Apply these guidelines when implementing Android UI in Jetpack Compose. They reflect Material Design 3 (Material You), Google's official 2024–2025 guidance, and platform requirements for Android 14+.

## Core Measurements (Non-Negotiable)

| Constraint | Value | Notes |
|---|---|---|
| Touch target minimum | 48×48dp | Applies to all interactive elements |
| Touch target spacing | 8dp between targets | Prevents mis-taps |
| Spacing grid | 8dp base | All spacing/padding in multiples of 8 |
| Body text minimum | 14sp | Never smaller for readable content |
| Caption/label minimum | 11sp | Only for non-essential labels |
| Contrast ratio (text) | 4.5:1 WCAG AA | Normal text on background |
| Contrast ratio (large text) | 3:1 WCAG AA | 18sp+ or 14sp bold |
| Contrast ratio (UI components) | 3:1 | Icons, borders, focus indicators |
| Feedback latency maximum | 100ms | Ripple/state change must be instant |
| Animation minimum frame rate | 60fps | Target 120fps on high-refresh devices |

## Navigation Pattern Selection

```
How many top-level destinations?
├── 2 → Segmented control or tabs (NOT bottom nav)
├── 3–5 → Bottom navigation bar (thumb-friendly default)
└── 6+ → Navigation drawer (bottom sheet drawer on phone)

Does the user need to reach anything in ≤3 taps?
└── YES required — if a flow exceeds 3 taps, flatten the hierarchy

Is this a detail/sub-screen?
└── Use top app bar with Up button (back arrow), NOT bottom nav
```

**Bottom Navigation Rules:**
- Show 3–5 destinations only; each needs an icon + label
- Active destination shows filled icon + color tint from `MaterialTheme.colorScheme.primary`
- Never hide bottom nav on scroll for primary destinations (it disorients users)
- Safe area: add `WindowInsets.navigationBars` padding so nav bar draws behind system nav

**Reference:** `references/navigation-patterns.md` for drawer, modal, and rail variants

## Edge-to-Edge Layout

Every Android screen must draw under both status bar and navigation bar.

```kotlin
// In Activity.onCreate() — apply once
WindowCompat.setDecorFitsSystemWindows(window, false)

// In each Compose screen — consume insets appropriately
Scaffold(
    topBar = { /* TopAppBar gets status bar insets automatically */ },
    bottomBar = { /* BottomNavigation gets nav bar insets automatically */ },
    contentWindowInsets = WindowInsets.safeContent  // pass remaining to content
) { paddingValues ->
    LazyColumn(
        contentPadding = paddingValues  // includes both top and bottom insets
    ) { ... }
}
```

**Rules:**
- Status bar: background can be transparent; text/icons auto-adapt via `WindowInsetsController`
- Navigation bar: always add `navigationBars` padding to last scrollable item or bottom bar
- Never place tap targets inside gesture inset zones (16dp sides on gesture nav devices)
- Floating action buttons need `WindowInsets.navigationBars` + 16dp extra padding

**Reference:** `references/edge-to-edge.md` for full inset type guide and common pitfalls

## Touch and Interaction

```kotlin
// Correct: explicit minimum touch target
Box(
    modifier = Modifier
        .sizeIn(minWidth = 48.dp, minHeight = 48.dp)
        .clickable { ... }
)

// Incorrect for small icons — use minimumInteractiveComponentSize()
Icon(
    modifier = Modifier
        .minimumInteractiveComponentSize()  // Compose enforces 48dp automatically
        .clickable { ... }
)
```

**Haptic feedback — when to use:**
| Action | Haptic Type |
|---|---|
| Confirm destructive action | `HapticFeedbackType.LongPress` |
| Toggle switch/checkbox | `HapticFeedbackType.TextHandleMove` |
| Drag item to new position | `HapticFeedbackType.LongPress` |
| Error / failed action | None (use visual feedback only) |
| Pull-to-refresh complete | `HapticFeedbackType.LongPress` |

## Accessibility Essentials

```kotlin
// Good: meaningful description without type (type is announced automatically)
Icon(
    contentDescription = "Delete note"  // NOT "Delete button" or "Delete icon"
)

// Good: semantic grouping for complex items
Row(
    modifier = Modifier.semantics(mergeDescendants = true) {}
) {
    Icon(contentDescription = null)  // null = decorative, excluded from TalkBack
    Text("Important label")
}

// Good: custom action for swipe-to-delete (TalkBack can't swipe)
Modifier.semantics {
    customActions = listOf(
        CustomAccessibilityAction("Delete") { onDelete(); true }
    )
}
```

**Accessibility checklist:**
- [ ] All interactive elements have `contentDescription` or `clickLabel`
- [ ] Decorative images have `contentDescription = null`
- [ ] Custom gestures have `semantics { customActions }` fallback
- [ ] Focus order is logical (default is reading order; use `traversalIndex` to fix)
- [ ] Text scales correctly at 200% font size without truncation
- [ ] Color is never the only differentiator (add shape, label, or icon)

European Accessibility Act (2025): WCAG 2.1 AA compliance is legally required for EU apps. Treat accessibility as a hard requirement, not optional polish.

**Reference:** `references/accessibility.md` for TalkBack testing protocol and automated scanner usage

## Material Design 3 Color System

| Role | Usage |
|---|---|
| `primary` | Key actions, FAB, selected state |
| `onPrimary` | Text/icons on primary containers |
| `primaryContainer` | Tonal buttons, highlighted surfaces |
| `secondary` | Supporting actions, chips |
| `tertiary` | Contrasting accents, special elements |
| `surface` | Card/sheet backgrounds |
| `surfaceVariant` | Alternate surface (input fields, chips) |
| `error` / `errorContainer` | Destructive actions, validation |
| `outline` | Borders, dividers |
| `outlineVariant` | Subtle dividers |

**Dynamic color (Material You):** Always derive colors from `MaterialTheme.colorScheme` — never hardcode hex values. On Android 12+, these automatically adapt to the user's wallpaper. Use `dynamicLightColorScheme` / `dynamicDarkColorScheme` with fallback static schemes.

```kotlin
val colorScheme = when {
    Build.VERSION.SDK_INT >= Build.VERSION_CODES.S -> {
        if (darkTheme) dynamicDarkColorScheme(context)
        else dynamicLightColorScheme(context)
    }
    darkTheme -> DarkColorScheme   // your static fallback
    else -> LightColorScheme
}
```

## Predictive Back Gesture (Android 14+ / API 34+)

Predictive Back previews the destination before the user completes the back gesture. Required behavior for modern Android apps.

```kotlin
// Enable in AndroidManifest.xml (required)
// android:enableOnBackInvokedCallback="true"

// In Compose Navigation — handled automatically by NavHost
// For custom back handling:
BackHandler(enabled = showDialog) {
    showDialog = false
}

// Predictive back animation for custom transitions
// Use STANDARD_DECELERATE interpolator with 8dp screen edge margin
// NavHost handles this automatically when using Compose Navigation 2.7+
```

**Rules:**
- Never intercept Back in ways that trap the user (no back → same screen)
- Sheet/dialog dismiss on back is expected behavior — implement it
- The system 8dp screen edge margin is reserved; place no interactive content there

## Motion and Animation Principles (Material Expressive 2025)

| Motion Type | Easing | Duration |
|---|---|---|
| Enter screen/element | `EaseOutCubic` | 300–450ms |
| Exit screen/element | `EaseInCubic` | 200–300ms |
| Emphasis (spring) | Spring (stiffness=Medium) | Physics-based |
| Position change | `EaseInOutCubic` | 300–500ms |
| Fade in | Linear | 150–250ms |

**Material Expressive spring animations (2025):**
```kotlin
// Preferred for element transitions — feels physical
val springSpec = spring<Dp>(
    dampingRatio = Spring.DampingRatioMediumBouncy,
    stiffness = Spring.StiffnessMedium
)
// Use animate*AsState with springSpec for natural motion
```

**Rules:**
- Never animate more than 3 properties simultaneously on the same element
- Respect `LocalReduceMotion` — check before playing decorative animations
- Duration below 100ms is imperceptible; above 500ms feels sluggish for UI feedback
- Entry animations: elements should slide + fade, not just appear

**Reference:** `references/animation-motion.md` for full transition specs and KMP animation patterns

## KMP / Compose Multiplatform Considerations

When implementing for SteleKit (KMP targeting Android + Desktop + iOS + Web):

```
Is this behavior Android-specific?
├── YES → put in androidMain source set, use expect/actual
└── NO → implement in commonMain

Is this a platform UI pattern?
├── Bottom navigation → Android + Web (shared)
├── Navigation rail → Desktop + tablet (shared)
├── Tab bar → iOS (separate)
└── Sidebar → Desktop-specific
```

**Shared Compose code that's safe cross-platform:**
- `MaterialTheme`, `colorScheme`, typography
- `Scaffold`, `TopAppBar`, `BottomAppBar`
- All layout composables (`Box`, `Column`, `Row`, `LazyColumn`)
- `Modifier.semantics {}` (accessibility)

**Android-only (wrap in `expect/actual` or `androidMain`):**
- `WindowCompat.setDecorFitsSystemWindows()`
- `dynamicDarkColorScheme()` / `dynamicLightColorScheme()`
- `HapticFeedbackType` (desktop has no haptics)
- `BackHandler` with Predictive Back

## Quick Decision Checklist

Before finalizing any Android UI implementation:

- [ ] All touch targets are 48×48dp minimum with 8dp spacing
- [ ] Screen draws edge-to-edge with correct inset consumption
- [ ] Colors come from `MaterialTheme.colorScheme` (never hardcoded)
- [ ] Interactive elements have accessibility descriptions
- [ ] Navigation follows ≤3 tap depth rule
- [ ] Animations respect `LocalReduceMotion`
- [ ] Haptic feedback used only for confirmation actions
- [ ] Contrast ratio verified (4.5:1 text, 3:1 UI components)

## Reference Files

Load these when deeper guidance is needed:

| File | When to load |
|---|---|
| `references/navigation-patterns.md` | Choosing nav drawer, modal bottom sheet, navigation rail, or top app bar variants |
| `references/edge-to-edge.md` | Complex inset scenarios, keyboard avoidance, multi-window |
| `references/accessibility.md` | TalkBack testing, screen reader order, custom semantic actions |
| `references/md3-components.md` | Specific Material 3 component specs (buttons, cards, dialogs, chips, FAB) |
| `references/animation-motion.md` | Transition specs, shared element transitions, spring parameters |
