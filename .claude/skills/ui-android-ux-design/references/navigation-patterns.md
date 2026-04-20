# Navigation Patterns — Android UX Reference

Deep reference for Android navigation patterns in Jetpack Compose. Load when choosing between structural navigation variants or implementing complex navigation.

## Pattern Selection Matrix

| Pattern | Destinations | Screen Size | Use When |
|---|---|---|---|
| Bottom navigation bar | 3–5 | Phone (portrait) | Primary app sections, thumb reachable |
| Navigation rail | 3–7 | Tablet / landscape phone | Side-accessible in larger viewports |
| Navigation drawer (modal) | 5+ | Phone | Overflow destinations beyond 5 |
| Navigation drawer (permanent) | 5+ | Desktop / large tablet | Always-visible sidebar |
| Top tabs | 2–5 | Any | Sibling views of the same content type |
| Bottom sheet navigation | Contextual | Phone | Temporary context switching |

## Bottom Navigation Bar

```kotlin
NavigationBar(
    modifier = Modifier
        .windowInsetsPadding(WindowInsets.navigationBars)  // consume nav bar inset
) {
    destinations.forEach { destination ->
        NavigationBarItem(
            selected = currentDestination == destination.route,
            onClick = { navController.navigate(destination.route) {
                popUpTo(navController.graph.findStartDestination().id) {
                    saveState = true
                }
                launchSingleTop = true
                restoreState = true
            }},
            icon = {
                // Show filled icon when selected, outlined when not
                if (currentDestination == destination.route)
                    Icon(destination.selectedIcon, contentDescription = null)
                else
                    Icon(destination.unselectedIcon, contentDescription = null)
            },
            label = { Text(destination.label) },
            alwaysShowLabel = true  // never hide labels on bottom nav
        )
    }
}
```

**Rules:**
- Use `saveState = true` and `restoreState = true` to preserve scroll/state per tab
- `launchSingleTop = true` prevents duplicate backstack entries
- `popUpTo(startDestination)` ensures Back from any tab goes to start, then exits app
- Icon fills on selection signal state to color-blind users (do not rely on color alone)

## Navigation Rail (Tablet / Landscape)

```kotlin
NavigationRail(
    modifier = Modifier
        .windowInsetsPadding(WindowInsets.systemBars)
        .fillMaxHeight()
) {
    // Optional: FAB at top of rail
    FloatingActionButton(onClick = { /* primary action */ }) {
        Icon(Icons.Default.Add, contentDescription = "New note")
    }
    Spacer(Modifier.height(16.dp))

    destinations.forEach { destination ->
        NavigationRailItem(
            selected = currentDestination == destination.route,
            onClick = { /* same navigation logic as bottom nav */ },
            icon = { Icon(destination.icon, contentDescription = null) },
            label = { Text(destination.label) }
        )
    }
}
```

**Layout with Rail:**
```kotlin
Row(Modifier.fillMaxSize()) {
    NavigationRail { /* ... */ }
    Box(Modifier.weight(1f)) {
        NavHost(navController = navController, ...) { /* ... */ }
    }
}
```

## Adaptive Navigation (Phone vs Tablet)

```kotlin
// Detect layout class and switch navigation pattern
val windowSizeClass = calculateWindowSizeClass()

when (windowSizeClass.widthSizeClass) {
    WindowWidthSizeClass.Compact -> {
        // Phone: bottom navigation bar
        BottomNavScaffold(navController, destinations)
    }
    WindowWidthSizeClass.Medium -> {
        // Foldable / landscape phone: navigation rail
        NavigationRailScaffold(navController, destinations)
    }
    WindowWidthSizeClass.Expanded -> {
        // Tablet / desktop: permanent navigation drawer
        PermanentDrawerScaffold(navController, destinations)
    }
}
```

## Modal Bottom Sheet (Contextual Navigation)

Use for: secondary destinations, filters, share targets — NOT for primary app structure.

```kotlin
val sheetState = rememberModalBottomSheetState()
var showSheet by remember { mutableStateOf(false) }

if (showSheet) {
    ModalBottomSheet(
        onDismissRequest = { showSheet = false },
        sheetState = sheetState,
        windowInsets = WindowInsets.navigationBars  // critical: sheet must not overdraw nav bar
    ) {
        // Content inside sheet
        // Add bottom padding for gesture handle area
        Column(
            modifier = Modifier
                .navigationBarsPadding()
                .padding(horizontal = 16.dp)
        ) { /* ... */ }
    }
}
```

**Rules:**
- Drag handle visible at top of sheet (default in Material 3)
- Back gesture dismisses sheet — implement `BackHandler` if custom dismiss logic needed
- Sheet content minimum height: enough to feel intentional (at least 30% screen height)
- Avoid nested scrollable content in sheets without `nestedScroll` setup

## Top App Bar Variants

| Variant | When to Use |
|---|---|
| `TopAppBar` | Single-line title, small screens |
| `MediumTopAppBar` | Medium title that collapses on scroll |
| `LargeTopAppBar` | Hero title for primary screens (homepage, settings root) |
| `CenterAlignedTopAppBar` | Brand-centered layouts |

```kotlin
// Scrollable top app bar — collapses as content scrolls
val scrollBehavior = TopAppBarDefaults.enterAlwaysScrollBehavior()

Scaffold(
    topBar = {
        LargeTopAppBar(
            title = { Text("All Notes") },
            navigationIcon = {
                // Only show Up button on non-root screens
                if (!isRootDestination) {
                    IconButton(onClick = { navController.navigateUp() }) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, "Back")
                    }
                }
            },
            scrollBehavior = scrollBehavior
        )
    },
    modifier = Modifier.nestedScroll(scrollBehavior.nestedScrollConnection)
) { /* content */ }
```

## Deep Linking

```kotlin
// Define deep links in NavGraph
composable(
    route = "note/{noteId}",
    arguments = listOf(navArgument("noteId") { type = NavType.StringType }),
    deepLinks = listOf(navDeepLink {
        uriPattern = "stelekit://note/{noteId}"
    })
) { backStackEntry ->
    NoteScreen(noteId = backStackEntry.arguments?.getString("noteId") ?: "")
}
```

## Back Stack Rules

1. The Back button must never trap the user (pressing Back must make progress toward exit or previous context)
2. Dialogs and bottom sheets dismiss on Back — never let Back navigate past a dialog without dismissing it first
3. Nested `NavHost` instances need their own Back handling with `BackHandler`
4. `popUpTo` with `inclusive = true` clears the destination itself from the stack

## Gesture Navigation Zone Avoidance

On gesture navigation devices (Android 10+), the system reserves:
- Left and right edges (16dp): Back gesture zones
- Bottom edge (varies, typically 32dp+): Home/recents gesture zone

**Never place interactive content in these zones.** Use `WindowInsets.systemGestures` to get the exact insets:

```kotlin
val gestureInsets = WindowInsets.systemGestures.asPaddingValues()
// Ensure your content padding respects gestureInsets.calculateStartPadding()
// and gestureInsets.calculateEndPadding()
```
