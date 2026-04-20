# Accessibility — Android UX Reference

Deep reference for Android accessibility in Jetpack Compose. Load when implementing TalkBack support, fixing semantic issues, or preparing for accessibility audits.

## Legal Context (2025)

**European Accessibility Act (EAA)**: Effective June 2025, all digital products/services sold in the EU must meet WCAG 2.1 Level AA. This applies to Android apps distributed in EU markets. Non-compliance risks market withdrawal and fines.

**Minimum standards:**
- WCAG 2.1 AA contrast ratios (4.5:1 normal text, 3:1 large text / UI components)
- All functionality available without touch gestures (TalkBack alternative actions)
- Text resizable to 200% without content loss
- No content that flashes more than 3 times per second

## Semantics API Reference

```kotlin
// Merge descendants into a single accessible node
Modifier.semantics(mergeDescendants = true) { }

// Custom accessible label (overrides default)
Modifier.semantics { contentDescription = "Delete note titled Shopping list" }

// Mark as heading for navigation
Modifier.semantics { heading() }

// Custom click action label
Modifier.semantics { onClick(label = "Open note") { true } }

// Custom swipe actions (critical: TalkBack can't perform swipe gestures)
Modifier.semantics {
    customActions = listOf(
        CustomAccessibilityAction(label = "Delete") { onDelete(); true },
        CustomAccessibilityAction(label = "Archive") { onArchive(); true }
    )
}

// Announce live region changes (for dynamic content)
Modifier.semantics { liveRegion = LiveRegionMode.Polite }
// LiveRegionMode.Assertive interrupts current speech (use sparingly)

// Indicate selection state
Modifier.semantics { selected = isSelected }

// Indicate disabled state
Modifier.semantics { disabled() }

// Progress indicator
Modifier.semantics {
    progressBarRangeInfo = ProgressBarRangeInfo(current = 0.7f, range = 0f..1f)
}

// State description
Modifier.semantics { stateDescription = if (isExpanded) "Expanded" else "Collapsed" }
```

## Content Description Rules

| Element | contentDescription | Rationale |
|---|---|---|
| Icon button (Delete) | `"Delete"` | Action only; no "button" (type announced) |
| Icon button (Delete note) | `"Delete note"` | Add object if context needed |
| Decorative icon next to text | `null` | Skip; text provides context |
| Image with meaning | `"Photo of sunset over mountains"` | Describe what the image communicates |
| Progress indicator | `null` (use `progressBarRangeInfo`) | Structured semantic instead |
| Logo / brand image | `"SteleKit"` | Name only |
| Toggle (off) | Use `stateDescription = "Off"` | State separate from label |

**Never include:**
- The word "button", "image", "icon" — TalkBack announces the role automatically
- Implementation details ("RecyclerView item", "Card")
- Redundant repetition of visible text that TalkBack would already read

## Focus Order and Traversal

Compose reads elements in layout order (top-to-bottom, left-to-right by default).

```kotlin
// Fix logical reading order when layout order differs from reading order
Row {
    // Visual: [Image] [Title] [Subtitle]
    // Reading order should be: Title, Subtitle, Image (image is decorative)
    Image(
        modifier = Modifier.semantics { contentDescription = null }  // decorative
    )
    Column {
        Text("Title", modifier = Modifier.semantics { traversalIndex = -1f })  // reads first
        Text("Subtitle", modifier = Modifier.semantics { traversalIndex = 0f })
    }
}
// Lower traversalIndex = reads earlier
// Default traversalIndex is 0f; use negative values to read before default elements
```

## Custom Gestures — Accessibility Alternative

Whenever you implement a custom touch gesture, provide a semantic alternative:

```kotlin
// Swipe-to-delete list item
Box(
    modifier = Modifier
        .swipeable(/* ... */)
        .semantics {
            // TalkBack alternative: double-tap with two fingers, or custom action
            customActions = listOf(
                CustomAccessibilityAction("Delete this note") {
                    viewModel.deleteNote(note.id)
                    true
                }
            )
        }
)

// Drag-to-reorder
LazyColumn {
    items(notes, key = { it.id }) { note ->
        NoteItem(
            modifier = Modifier.semantics {
                customActions = listOf(
                    CustomAccessibilityAction("Move up") { viewModel.moveUp(note.id); true },
                    CustomAccessibilityAction("Move down") { viewModel.moveDown(note.id); true }
                )
            }
        )
    }
}
```

## Text Scaling

At 200% font scale, all text must remain readable without overlap or truncation.

```kotlin
// Bad: fixed height clips text at large font scales
Box(modifier = Modifier.height(48.dp)) {
    Text("Label")  // clips at 200% scale
}

// Good: minimum height with natural growth
Box(modifier = Modifier.heightIn(min = 48.dp)) {
    Text("Label")  // grows with font
}

// Good: avoid maxLines without ellipsis consideration
Text(
    text = longText,
    maxLines = 2,
    overflow = TextOverflow.Ellipsis  // graceful truncation rather than clip
)

// Check font scale in code
val fontScale = LocalDensity.current.fontScale
if (fontScale > 1.3f) {
    // Apply compact layout variant
}
```

## Color and Contrast

```kotlin
// Use MaterialTheme roles — they're designed to meet contrast requirements
Text(
    text = "Important text",
    color = MaterialTheme.colorScheme.onSurface  // guaranteed contrast on Surface
)

// Never use opacity to reduce contrast
Text(
    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.38f)  // BAD: fails contrast
)

// For disabled state, use the provided disabled content color
Text(
    color = if (enabled)
        MaterialTheme.colorScheme.onSurface
    else
        MaterialTheme.colorScheme.onSurface.copy(alpha = ContentAlpha.disabled)  // intentional low contrast for disabled
)

// Always pair color changes with shape/icon/label changes
// Never use color alone to communicate state
```

**Contrast ratio verification:**
- Normal text (< 18sp, non-bold): 4.5:1 minimum
- Large text (≥ 18sp, or ≥ 14sp bold): 3:1 minimum
- UI components and graphics: 3:1 against adjacent colors
- Decorative elements: no contrast requirement

## Live Regions for Dynamic Content

```kotlin
// Countdown timer that updates
var timeLeft by remember { mutableStateOf("30 seconds") }

Text(
    text = timeLeft,
    modifier = Modifier.semantics {
        liveRegion = LiveRegionMode.Polite  // announces changes after current speech finishes
    }
)

// Error messages — use Assertive only for critical, time-sensitive errors
Snackbar(
    modifier = Modifier.semantics {
        liveRegion = LiveRegionMode.Polite  // snackbars announce when shown
    }
)

// Loading state
if (isLoading) {
    CircularProgressIndicator(
        modifier = Modifier.semantics {
            contentDescription = "Loading your notes"
        }
    )
}
```

## Testing Protocol

### Automated Testing (run first)

1. Enable in Android Studio: Tools → Accessibility Scanner
2. On device: Settings → Accessibility → Accessibility Scanner
3. Run with Compose UI tests:

```kotlin
@Test
fun noteItem_hasAccessibleContent() {
    composeTestRule.setContent {
        NoteItem(note = testNote, onDelete = {})
    }
    
    // Verify content description exists
    composeTestRule
        .onNodeWithContentDescription("Delete")
        .assertExists()
    
    // Verify minimum touch target size
    composeTestRule
        .onNodeWithContentDescription("Delete")
        .assertWidthIsAtLeast(48.dp)
        .assertHeightIsAtLeast(48.dp)
}
```

### Manual TalkBack Testing (required before release)

1. Enable TalkBack: Settings → Accessibility → TalkBack
2. Gesture cheat sheet:
   - Single tap: move focus
   - Double tap: activate focused element
   - Swipe right/left: next/previous element
   - Swipe up then right: open TalkBack menu
   - Two-finger swipe up: scroll up
3. Test checklist:
   - [ ] Navigate to every interactive element using only swipe right
   - [ ] Activate each element with double tap
   - [ ] Confirm all custom gestures have TalkBack alternatives
   - [ ] Confirm no focus traps (can always navigate forward and back)
   - [ ] Confirm modal dialogs trap focus inside (correct behavior)
   - [ ] Confirm bottom sheet dismisses on back gesture
   - [ ] Test at 200% font scale

### Common TalkBack Bugs

| Symptom | Cause | Fix |
|---|---|---|
| TalkBack skips element | `contentDescription = null` on interactive element | Add meaningful contentDescription |
| TalkBack reads too much | Descendants not merged | Add `semantics(mergeDescendants = true)` |
| TalkBack reads "unlabelled" | No contentDescription | Provide description on icon/image |
| Focus order is wrong | Layout order != logical order | Use `traversalIndex` |
| Custom gesture unavailable | No semantic alternative | Add `customActions` |
| Swipe-to-delete inaccessible | Only touch gesture implemented | Add delete `customActions` |
| Modal doesn't trap focus | Using custom modal | Use Material3 `Dialog` or `ModalBottomSheet` |
