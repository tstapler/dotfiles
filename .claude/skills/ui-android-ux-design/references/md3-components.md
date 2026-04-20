# Material Design 3 Components — Android UX Reference

Specification reference for MD3 component usage in Jetpack Compose. Load when choosing between component variants or implementing specific components correctly.

## Button Hierarchy

Use button types in this priority order on any screen:

| Type | Compose | When to Use |
|---|---|---|
| Filled | `Button` | Single primary action per screen |
| Filled Tonal | `FilledTonalButton` | Secondary action, less emphasis than filled |
| Outlined | `OutlinedButton` | Cancel, secondary without tonal emphasis |
| Text | `TextButton` | Lowest emphasis — inline, list items, dialogs |
| Elevated | `ElevatedButton` | Needs separation from background (avoid on cards) |
| FAB | `FloatingActionButton` | Persistent primary action across the screen |
| Extended FAB | `ExtendedFloatingActionButton` | FAB with visible label (use when FAB alone is ambiguous) |

**Rules:**
- Never show two filled buttons on the same screen
- Dialog primary action = text button; destructive dialog primary = filled button (red)
- FAB minimum size: 56×56dp; mini FAB: 40×40dp; large FAB: 96×96dp

```kotlin
// Correct: dialog button order (dismiss left, confirm right)
AlertDialog(
    onDismissRequest = onDismiss,
    dismissButton = {
        TextButton(onClick = onDismiss) { Text("Cancel") }
    },
    confirmButton = {
        // Destructive: use error color
        Button(
            onClick = onConfirm,
            colors = ButtonDefaults.buttonColors(
                containerColor = MaterialTheme.colorScheme.error
            )
        ) { Text("Delete") }
    },
    title = { Text("Delete note?") },
    text = { Text("This action cannot be undone.") }
)
```

## Cards

| Type | Compose | Use When |
|---|---|---|
| Elevated | `Card` (default) | Content on flat surface, needs separation |
| Filled | `Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant))` | Content on elevated surface |
| Outlined | `OutlinedCard` | Selection state, delineation without elevation |

```kotlin
// Selectable card with correct state
Card(
    modifier = Modifier
        .fillMaxWidth()
        .semantics { selected = isSelected },
    colors = CardDefaults.cardColors(
        containerColor = if (isSelected)
            MaterialTheme.colorScheme.primaryContainer
        else
            MaterialTheme.colorScheme.surface
    ),
    onClick = { onSelect() }
) {
    // 16dp internal padding (standard)
    Column(modifier = Modifier.padding(16.dp)) {
        Text(title, style = MaterialTheme.typography.titleMedium)
        Text(subtitle, style = MaterialTheme.typography.bodyMedium)
    }
}
```

## Text Fields

| Type | Use When |
|---|---|
| `OutlinedTextField` | Forms, settings — clear boundaries needed |
| `TextField` (filled) | Dense UIs, search bars within surfaces |

```kotlin
var text by remember { mutableStateOf("") }
var isError by remember { mutableStateOf(false) }

OutlinedTextField(
    value = text,
    onValueChange = { text = it; isError = it.length > 100 },
    label = { Text("Note title") },
    placeholder = { Text("Enter a title...") },
    supportingText = {
        if (isError) Text("Title must be under 100 characters")
        else Text("${text.length}/100")
    },
    isError = isError,
    singleLine = true,
    keyboardOptions = KeyboardOptions(
        capitalization = KeyboardCapitalization.Sentences,
        imeAction = ImeAction.Next
    ),
    keyboardActions = KeyboardActions(
        onNext = { focusManager.moveFocus(FocusDirection.Down) }
    )
)
```

**Input field rules:**
- Always show a label (placeholder disappears; label floats up)
- `supportingText` for help text and character counts (below field)
- `errorMessage` takes precedence over `supportingText` when `isError = true`
- `singleLine = true` for short inputs; `maxLines` for bounded multiline

## Chips

| Type | Compose | Use When |
|---|---|---|
| Assist | `AssistChip` | Contextual suggestions (not persistent) |
| Filter | `FilterChip` | Toggle-able filter states |
| Input | `InputChip` | Represent user-entered values (tags) |
| Suggestion | `SuggestionChip` | Auto-complete options |

```kotlin
// Filter chips in a row (use LazyRow for many)
LazyRow(
    horizontalArrangement = Arrangement.spacedBy(8.dp),
    contentPadding = PaddingValues(horizontal = 16.dp)
) {
    items(filters) { filter ->
        FilterChip(
            selected = filter.isActive,
            onClick = { filter.toggle() },
            label = { Text(filter.name) },
            leadingIcon = if (filter.isActive) {
                { Icon(Icons.Default.Check, contentDescription = null, Modifier.size(FilterChipDefaults.IconSize)) }
            } else null
        )
    }
}
```

## Dialogs

```kotlin
// Standard informational dialog
AlertDialog(
    onDismissRequest = onDismiss,
    icon = { Icon(Icons.Default.Warning, contentDescription = null) },
    title = { Text("Unsaved changes") },
    text = { Text("You have unsaved changes. Discard them?") },
    confirmButton = {
        TextButton(onClick = onConfirm) { Text("Discard") }
    },
    dismissButton = {
        TextButton(onClick = onDismiss) { Text("Keep editing") }
    }
)

// Custom content dialog
Dialog(onDismissRequest = onDismiss) {
    Card(
        shape = MaterialTheme.shapes.extraLarge,  // MD3 dialog shape = extraLarge (28dp corner)
        modifier = Modifier.padding(horizontal = 16.dp)
    ) {
        Column(modifier = Modifier.padding(24.dp)) {
            Text("Title", style = MaterialTheme.typography.headlineSmall)
            Spacer(Modifier.height(16.dp))
            // Custom content
        }
    }
}
```

**Dialog rules:**
- Dismiss on click outside: always implement `onDismissRequest`
- Back gesture must dismiss the dialog
- No more than 2 actions; avoid 3-button dialogs
- Use `AlertDialog` for 90% of cases; `Dialog` only when content is truly custom

## Snackbars

```kotlin
val snackbarHostState = remember { SnackbarHostState() }

Scaffold(
    snackbarHost = { SnackbarHost(snackbarHostState) }
) { /* content */ }

// Show snackbar (always in a coroutine)
LaunchedEffect(errorMessage) {
    if (errorMessage != null) {
        val result = snackbarHostState.showSnackbar(
            message = errorMessage,
            actionLabel = "Retry",
            duration = SnackbarDuration.Long  // 10s for actions; Short (4s) for info
        )
        when (result) {
            SnackbarResult.ActionPerformed -> retryAction()
            SnackbarResult.Dismissed -> { /* user dismissed */ }
        }
    }
}
```

**Snackbar rules:**
- One snackbar at a time (SnackbarHostState queues automatically)
- Snackbar is positioned above FAB automatically by Scaffold
- Action label max 2 words; no punctuation
- Duration: Short (4s) for info, Long (10s) if action needed, Indefinite only for critical errors

## Lists and Dividers

```kotlin
// Standard list item (MD3 ListItem)
ListItem(
    headlineContent = { Text("Note title") },
    supportingContent = { Text("Last edited today") },
    leadingContent = {
        Icon(Icons.Default.Note, contentDescription = null)
    },
    trailingContent = {
        IconButton(onClick = { /* ... */ }) {
            Icon(Icons.Default.MoreVert, contentDescription = "Note options")
        }
    },
    modifier = Modifier.clickable { onNoteClick() }
)

// Dividers between sections (not between every item)
HorizontalDivider(
    modifier = Modifier.padding(horizontal = 16.dp),
    color = MaterialTheme.colorScheme.outlineVariant
)
```

## Progress Indicators

| Indicator | Compose | When |
|---|---|---|
| Circular indeterminate | `CircularProgressIndicator()` | Unknown duration loading |
| Circular determinate | `CircularProgressIndicator(progress = { value })` | Known progress |
| Linear indeterminate | `LinearProgressIndicator()` | Page-level loading (top of screen) |
| Linear determinate | `LinearProgressIndicator(progress = { value })` | File upload/download |

```kotlin
// Page-level loading at top (under top app bar)
if (isLoading) {
    LinearProgressIndicator(
        modifier = Modifier.fillMaxWidth()
    )
}

// Content-level loading overlay
if (isLoading) {
    Box(contentAlignment = Alignment.Center, modifier = Modifier.fillMaxSize()) {
        CircularProgressIndicator()
    }
}
```

## Typography Scale

| Style | Use For | Size |
|---|---|---|
| `displayLarge` | Hero numbers, splash screen | 57sp |
| `displayMedium` | Large headers | 45sp |
| `displaySmall` | Important numbers | 36sp |
| `headlineLarge` | Screen title (large top bar) | 32sp |
| `headlineMedium` | Screen title (medium top bar) | 28sp |
| `headlineSmall` | Dialog title | 24sp |
| `titleLarge` | App bar title | 22sp |
| `titleMedium` | Card title, list primary | 16sp / medium weight |
| `titleSmall` | Section label | 14sp / medium weight |
| `bodyLarge` | Primary body text | 16sp |
| `bodyMedium` | Secondary body text | 14sp |
| `bodySmall` | Caption, metadata | 12sp |
| `labelLarge` | Button text | 14sp / medium weight |
| `labelMedium` | Chip text, tab label | 12sp |
| `labelSmall` | Badge, overline | 11sp |

Always use `MaterialTheme.typography.*` — never hardcode sp values. Custom fonts must be set in `Typography` within your theme.

## Shape Scale

| Token | Corner Radius | Components |
|---|---|---|
| `extraSmall` | 4dp | Small chips |
| `small` | 8dp | Text fields, small buttons |
| `medium` | 12dp | Cards, buttons, menus |
| `large` | 16dp | Navigation drawer |
| `extraLarge` | 28dp | Bottom sheets, large cards, dialogs |
| `full` | 50% (pill) | FAB, chips, badges |

```kotlin
// Access shapes from theme
Card(shape = MaterialTheme.shapes.medium) { }
Button(shape = MaterialTheme.shapes.full) { }  // pill-shaped button
```
