---
name: cmp-ui-testing
description: Compose Multiplatform UI testing guide for SteleKit. Covers the two-layer testing strategy: createComposeRule-based interaction tests (click, assert, type) using ComposeUITestBase, and Roborazzi screenshot regression tests. Use when writing new Compose UI tests, adding screenshot tests, or understanding how the existing jvmTest UI test infrastructure works.
---

# Compose Multiplatform UI Testing — SteleKit

SteleKit uses a two-layer UI testing strategy, both running in `kmp/src/jvmTest/` via `./gradlew jvmTest`:

| Layer | Purpose | Base / Tool |
|---|---|---|
| **Interaction tests** | Assert UI state: displayed text, clicks, navigation | `ComposeUITestBase` + `createComposeRule` |
| **Screenshot tests** | Visual regression: catch rendering regressions | `createComposeRule` + Roborazzi |

Both run headlessly on JVM — no display, no running app needed.

---

## Layer 1: Interaction Tests

### Base class: `ComposeUITestBase`

**Location:** `kmp/src/jvmTest/kotlin/dev/stapler/stelekit/ui/ComposeUITestBase.kt`

Wires the full fake dependency graph. Subclass it and write tests immediately — no boilerplate.

```kotlin
class MyFeatureTest : ComposeUITestBase() {

    @Test
    fun `search dialog shows results`() {
        composeTestRule.setContent {
            StelekitTheme {
                SearchDialog(
                    viewModel = viewModel,
                    onDismiss = {}
                )
            }
        }

        // Interact
        composeTestRule.onNodeWithContentDescription("Search input").performTextInput("journals")

        // Assert
        composeTestRule.onNodeWithText("Journals").assertIsDisplayed()
    }

    @Test
    fun `clicking a page link navigates`() {
        var navigatedTo: String? = null

        composeTestRule.setContent {
            StelekitTheme {
                JournalsView(
                    viewModel = JournalsViewModel(/* ... */),
                    blockRepository = blockRepo,
                    isDebugMode = false,
                    onLinkClick = { navigatedTo = it }
                )
            }
        }

        composeTestRule.onNodeWithText("[[Welcome]]").performClick()
        assertEquals("Welcome", navigatedTo)
    }
}
```

### What `ComposeUITestBase` provides

```kotlin
// Pre-wired fakes — use these directly in setContent{}
val composeTestRule  // createComposeRule() — the JUnit4 rule
val pageRepo         // PopulatedFakePageRepository
val blockRepo        // PopulatedFakeBlockRepository
val fakeFileSystem   // FakeFileSystem
val scope            // CoroutineScope(Dispatchers.Unconfined)
val graphLoader      // GraphLoader(fakeFileSystem, pageRepo, blockRepo)
val graphWriter      // GraphWriter(PlatformFileSystem())
val searchRepo       // InMemorySearchRepository()
val platformSettings // PlatformSettings()
val blockStateManager
val viewModel        // StelekitViewModel — lazy, full wiring
```

### Key interaction APIs

```kotlin
// Find nodes
composeTestRule.onNodeWithText("Save")
composeTestRule.onNodeWithContentDescription("Close")
composeTestRule.onNode(hasText("foo") and hasClickAction())
composeTestRule.onAllNodesWithText("item")

// Actions
.performClick()
.performTextInput("hello")
.performTextClearance()
.performScrollTo()
.performImeAction()   // submit/search on keyboard
.performKeyInput { pressKey(Key.Enter) }

// Assertions
.assertIsDisplayed()
.assertDoesNotExist()
.assertIsEnabled()
.assertIsNotEnabled()
.assertTextEquals("exact text")
.assertContentDescriptionEquals("desc")

// Wait for async state
composeTestRule.waitUntil(timeoutMillis = 3_000) {
    composeTestRule.onAllNodesWithText("Loaded").fetchSemanticsNodes().isNotEmpty()
}
```

### Fake fixtures

**Location:** `kmp/src/jvmTest/kotlin/dev/stapler/stelekit/ui/fixtures/`

| Class | What it provides |
|---|---|
| `FakeFileSystem` | No-op filesystem (reads return `""`, writes return `true`) |
| `FakePageRepository` | In-memory `PageRepository` over a `MutableStateFlow<Map>` |
| `FakeBlockRepository` | In-memory `BlockRepository` |
| `PopulatedFakePageRepository` | Pre-seeded with sample pages from `TestFixtures` |
| `PopulatedFakeBlockRepository` | Pre-seeded with sample blocks |

To test with custom data, instantiate `FakePageRepository(listOf(myPage))` directly — don't use the pre-seeded `Populated*` variants when you need specific content.

---

## Layer 2: Screenshot Tests (Roborazzi)

### How it works

Screenshot tests render a composable headlessly, capture a PNG, and compare it to a stored golden image. A changed pixel fails the test.

**Dependencies (already in `build.gradle.kts`):**
- `ui-test-junit4-desktop:1.8.0`
- `io.github.takahirom.roborazzi:roborazzi-compose-desktop`

### Writing a screenshot test

```kotlin
class MyScreenshotTest {

    @get:Rule
    val composeTestRule = createComposeRule()

    @Test
    fun sidebar_expanded_light() {
        composeTestRule.setContent {
            StelekitTheme(themeMode = StelekitThemeMode.LIGHT) {
                LeftSidebar(
                    expanded = true,
                    isLoading = false,
                    favoritePages = emptyList(),
                    recentPages = emptyList(),
                    currentScreen = Screen.Journals,
                    onPageClick = {},
                    onNavigate = {},
                    onToggleFavorite = {}
                )
            }
        }

        composeTestRule.onRoot()
            .captureRoboImage("build/outputs/roborazzi/sidebar_expanded_light.png")
    }
}
```

### Golden image workflow

```bash
# First run — create goldens
./gradlew jvmTest -Proborazzi.test.record

# Subsequent runs — compare against goldens (CI default)
./gradlew jvmTest

# Update goldens after intentional visual changes
./gradlew jvmTest -Proborazzi.test.record
```

Screenshots land in `build/outputs/roborazzi/`. Commit the PNG files alongside your test to lock in the golden.

### Existing screenshot test classes

| Class | What it covers |
|---|---|
| `DesktopScreenshotTest` | Full desktop layout, light + dark |
| `MobileScreenshotTest` | Mobile layout |
| `JournalsViewScreenshotTest` | JournalsView |
| `DemoGraphScreenshotTest` | Demo graph content |
| `BottomNavScreenshotTest` | Mobile bottom nav |

---

## Running Tests

```bash
# All jvmTests (unit + UI + screenshots)
./gradlew jvmTest

# Single test class
./gradlew jvmTest --tests "dev.stapler.stelekit.ui.screens.PageViewUITest"

# Single method
./gradlew jvmTest --tests "dev.stapler.stelekit.ui.screens.PageViewUITest.pageView_showsPageTitle"

# Record new screenshot goldens
./gradlew jvmTest -Proborazzi.test.record
```

Tests run on `Dispatchers.Unconfined` in the fake scope — no real coroutine delays, instant state updates.

---

## Where to Put New Tests

| Test type | Package |
|---|---|
| Interaction test for a screen | `ui/screens/` (e.g. `JournalsViewUITest`) |
| Interaction test for a component | `ui/components/` (e.g. `SearchDialogTest`) |
| Screenshot for a screen | `ui/screenshots/` |
| Full layout screenshot | `ui/screenshots/DesktopScreenshotTest` or `MobileScreenshotTest` |

Extend `ComposeUITestBase` for interaction tests. Use `createComposeRule()` directly for screenshot tests (no base class needed — screenshots just render and capture).

---

## Pitfalls

**`ForgottenCoroutineScopeException`**
Don't pass `rememberCoroutineScope()` to a ViewModel in tests. Use `CoroutineScope(Dispatchers.Unconfined)` instead.

**Semantics not found**
Compose UI Test finds nodes via accessibility semantics. If `onNodeWithText("foo")` fails, the component may not emit the text as a semantics node. Add `Modifier.semantics { contentDescription = "..." }` or use `onNodeWithContentDescription`.

**Screenshot diffs on CI**
Font rendering and anti-aliasing differ across machines. If goldens recorded on macOS don't match Linux CI renders, record goldens on Linux (or in a Docker container that matches CI).

**`BlockStateManager` circular reference**
`ComposeUITestBase` uses `by lazy` for `viewModel` so `blockStateManager`'s `graphPathProvider` lambda can safely reference `viewModel` without triggering initialization before the constructor completes.
