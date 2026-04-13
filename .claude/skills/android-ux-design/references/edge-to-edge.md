# Edge-to-Edge Layout — Android UX Reference

Full reference for drawing behind system bars in Jetpack Compose. Load for complex inset scenarios, keyboard avoidance, or multi-window support.

## Inset Type Reference

| Inset Type | What It Is | Use When |
|---|---|---|
| `WindowInsets.statusBars` | Height of status bar | Padding behind status bar only |
| `WindowInsets.navigationBars` | Height of nav bar / gesture bar | Padding behind nav bar |
| `WindowInsets.systemBars` | Union of status + nav bars | Full system chrome padding |
| `WindowInsets.ime` | Keyboard height | Text input screens |
| `WindowInsets.safeDrawing` | `systemBars + displayCutout` | Safe to draw in |
| `WindowInsets.safeContent` | `safeDrawing + ime` | Safe for interactive content |
| `WindowInsets.systemGestures` | Back/home gesture zones | Avoid tap targets here |
| `WindowInsets.displayCutout` | Notch / camera cutout area | Content near cutout |
| `WindowInsets.tappableElement` | Smallest tappable safe area | Most conservative option |

**Rule of thumb:**
- Content (text, images): `safeDrawing`
- Interactive elements: `safeContent` or explicit `systemBars + ime`
- Avoid gesture interference: also check `systemGestures`

## Foundation Setup

```kotlin
// Activity.onCreate() — required once per Activity
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        // Step 1: opt into edge-to-edge drawing
        enableEdgeToEdge()  // API 35+: also sets transparent system bars
        // OR for API 29-34:
        // WindowCompat.setDecorFitsSystemWindows(window, false)
        
        setContent {
            MyAppTheme {
                MyApp()
            }
        }
    }
}
```

## Scaffold Pattern (Most Common)

`Scaffold` from Material 3 automatically wires insets for its slots:

```kotlin
Scaffold(
    topBar = {
        TopAppBar(
            title = { Text("Notes") }
            // TopAppBar automatically pads for status bar
        )
    },
    bottomBar = {
        NavigationBar {
            // NavigationBar automatically pads for navigation bar
        }
    },
    floatingActionButton = {
        FloatingActionButton(
            onClick = { /* ... */ }
            // FAB automatically respects navigation bar
        ) {
            Icon(Icons.Default.Add, "New note")
        }
    }
) { paddingValues ->
    // paddingValues = top bar height + bottom bar height (already includes system bars)
    LazyColumn(
        contentPadding = paddingValues  // apply to content
    ) {
        items(notes) { NoteItem(it) }
    }
}
```

## Screen Without Scaffold

```kotlin
@Composable
fun FullBleedScreen() {
    Box(
        modifier = Modifier
            .fillMaxSize()
            .windowInsetsPadding(WindowInsets.systemBars)  // manual inset consumption
    ) {
        // content
    }
}
```

## Keyboard Avoidance (IME Insets)

```kotlin
// Option 1: Scaffold handles it with safeContent (Compose 1.5+)
Scaffold(
    contentWindowInsets = WindowInsets.safeContent
) { paddingValues ->
    Column(modifier = Modifier.padding(paddingValues)) {
        TextField(value = text, onValueChange = { text = it })
    }
}

// Option 2: Manual IME padding for custom layouts
Column(
    modifier = Modifier
        .fillMaxSize()
        .imePadding()          // adds padding equal to keyboard height
        .navigationBarsPadding()
) {
    Spacer(Modifier.weight(1f))
    TextField(value = text, onValueChange = { text = it })
}
```

**Important:** `imePadding()` must be applied AFTER `fillMaxSize()` to work correctly. The column/box must be able to measure without the keyboard first.

## Status Bar Content Color

```kotlin
// Light status bar (dark icons on light background)
enableEdgeToEdge(
    statusBarStyle = SystemBarStyle.light(
        scrim = android.graphics.Color.TRANSPARENT,
        darkScrim = android.graphics.Color.TRANSPARENT
    )
)

// Auto-detect from window background (default in enableEdgeToEdge())
// Light theme → dark icons; Dark theme → light icons
```

## Navigation Bar Background

```kotlin
// Fully transparent nav bar (Android 10+ gesture nav users see nothing)
// Android 3-button nav: system draws a scrim automatically
enableEdgeToEdge(
    navigationBarStyle = SystemBarStyle.auto(
        lightScrim = android.graphics.Color.TRANSPARENT,
        darkScrim = android.graphics.Color.TRANSPARENT
    )
)
```

## Handling Cutouts (Notch / Punch-hole Camera)

```kotlin
@Composable
fun ContentWithCutoutAwareness() {
    val displayCutout = WindowInsets.displayCutout

    Box(
        modifier = Modifier
            .fillMaxSize()
            .windowInsetsPadding(displayCutout)  // never draw important content behind cutout
    ) {
        // Safe to render here
    }
}
```

**Rule:** Decorative backgrounds can extend into the cutout area. Text and interactive elements must not.

## LazyColumn / LazyGrid Edge-to-Edge

```kotlin
// Correct: content visible behind top/bottom bars, but scrollable past them
LazyColumn(
    contentPadding = PaddingValues(
        top = WindowInsets.statusBars.asPaddingValues().calculateTopPadding() + 16.dp,
        bottom = WindowInsets.navigationBars.asPaddingValues().calculateBottomPadding() + 16.dp,
        start = 16.dp,
        end = 16.dp
    )
) {
    items(data) { Item(it) }
}

// Simpler with Scaffold: use paddingValues from content lambda
```

## Multi-Window and Foldables

```kotlin
// WindowSizeClass for adaptive layout decisions
@OptIn(ExperimentalMaterial3AdaptiveApi::class)
@Composable
fun AdaptiveApp() {
    val windowSizeClass = calculateWindowSizeClass()
    
    // In multi-window mode, insets still apply correctly
    // WindowCompat handles this automatically
    
    // Check if foldable is in tabletop posture
    val posture = currentWindowAdaptiveInfo().windowPosture
    if (posture.isTabletop) {
        // Split content above/below fold
    }
}
```

## Common Pitfalls

| Problem | Symptom | Fix |
|---|---|---|
| Content behind keyboard | TextField scrolls under keyboard | Add `imePadding()` or use `safeContent` |
| Taps blocked by nav bar | Bottom buttons unreachable | Add `navigationBarsPadding()` or `Scaffold` bottom bar |
| White bar under nav bar | App background not extending | `WindowCompat.setDecorFitsSystemWindows(window, false)` |
| Status bar text invisible | White text on white background | Use `enableEdgeToEdge()` with correct `SystemBarStyle` |
| Content behind notch | Text clipped by camera hole | Add `displayCutout` insets to content padding |
| Gesture conflict | Swipe in app conflicts with Back | Check `systemGestures` insets; move targets inward |
| Double padding in Scaffold | Extra space at top/bottom | Don't apply `windowInsetsPadding` AND use Scaffold together; pick one |

## Inset Debugging

```kotlin
// Visualize insets during development
Modifier.border(1.dp, Color.Red)  // temporary: see actual content area

// Check inset values programmatically
val insets = WindowInsets.systemBars
val topDp = with(LocalDensity.current) { insets.getTop(this).toDp() }
val bottomDp = with(LocalDensity.current) { insets.getBottom(this).toDp() }
Log.d("Insets", "top=$topDp, bottom=$bottomDp")
```
