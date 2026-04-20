# Animation and Motion — Android UX Reference

Transition specs, spring parameters, and Material Expressive patterns for Jetpack Compose. Load when implementing screen transitions, element animations, or physics-based motion.

## Material Motion System (MD3)

Material Design 3 defines five motion types. Choose the correct one for each interaction:

| Motion Type | When to Use | Easing | Duration |
|---|---|---|---|
| **Emphasized** | Spatial navigation (full-screen transitions) | `EmphasizedEasing` (custom cubic) | 500ms |
| **Emphasized Decelerate** | Elements entering the screen | `EmphasizedDecelerateEasing` | 400ms |
| **Emphasized Accelerate** | Elements leaving the screen | `EmphasizedAccelerateEasing` | 200ms |
| **Standard** | Most UI changes, non-spatial | `StandardEasing` (cubic) | 300ms |
| **Standard Decelerate** | Enter (no spatial relationship) | `StandardDecelerateEasing` | 250ms |
| **Standard Accelerate** | Exit (no spatial relationship) | `StandardAccelerateEasing` | 200ms |

```kotlin
// Material Emphasized easing (for primary spatial transitions)
val EmphasizedEasing = CubicBezierEasing(0.2f, 0.0f, 0.0f, 1.0f)
val EmphasizedDecelerateEasing = CubicBezierEasing(0.05f, 0.7f, 0.1f, 1.0f)
val EmphasizedAccelerateEasing = CubicBezierEasing(0.3f, 0.0f, 0.8f, 0.15f)
val StandardEasing = CubicBezierEasing(0.2f, 0.0f, 0.0f, 1.0f)
val StandardDecelerateEasing = CubicBezierEasing(0.0f, 0.0f, 0.0f, 1.0f)
val StandardAccelerateEasing = CubicBezierEasing(0.3f, 0.0f, 1.0f, 1.0f)
```

## Material Expressive (2025) — Spring-Based Motion

Material Expressive replaces duration-based tweens with physics-based springs for primary transitions. Springs feel natural because they respond to interruption gracefully.

```kotlin
// Recommended spring specs for different use cases
object MaterialSprings {
    // Spatial transitions (element moves between positions)
    val spatial = spring<Dp>(
        dampingRatio = Spring.DampingRatioNoBouncy,
        stiffness = Spring.StiffnessMedium       // ~400ms equivalent
    )
    
    // Expressive / emphasized (slight bounce for delight)
    val expressive = spring<Dp>(
        dampingRatio = Spring.DampingRatioLowBouncy,
        stiffness = Spring.StiffnessMedium       // visible, tasteful bounce
    )
    
    // Quick response (FAB, chips, toggles)
    val responsive = spring<Dp>(
        dampingRatio = Spring.DampingRatioNoBouncy,
        stiffness = Spring.StiffnessMediumLow    // faster feel
    )
    
    // Gentle (expand/collapse, bottom sheet)
    val gentle = spring<Dp>(
        dampingRatio = Spring.DampingRatioNoBouncy,
        stiffness = Spring.StiffnessLow          // ~600ms equivalent
    )
}

// Spring stiffness reference values
// Spring.StiffnessHigh      = 10000 → ~100ms
// Spring.StiffnessMedium    = 400   → ~350ms  
// Spring.StiffnessMediumLow = 200   → ~500ms
// Spring.StiffnessLow       = 100   → ~700ms
// Spring.StiffnessVeryLow   = 50    → ~1000ms
```

## Screen Transitions (Compose Navigation)

```kotlin
// With Compose Navigation + AnimatedNavHost
AnimatedNavHost(
    navController = navController,
    startDestination = "home",
    enterTransition = {
        slideIntoContainer(
            AnimatedContentTransitionScope.SlideDirection.Start,
            animationSpec = tween(400, easing = EmphasizedDecelerateEasing)
        )
    },
    exitTransition = {
        slideOutOfContainer(
            AnimatedContentTransitionScope.SlideDirection.Start,
            animationSpec = tween(200, easing = EmphasizedAccelerateEasing)
        )
    },
    popEnterTransition = {
        slideIntoContainer(
            AnimatedContentTransitionScope.SlideDirection.End,
            animationSpec = tween(400, easing = EmphasizedDecelerateEasing)
        )
    },
    popExitTransition = {
        slideOutOfContainer(
            AnimatedContentTransitionScope.SlideDirection.End,
            animationSpec = tween(200, easing = EmphasizedAccelerateEasing)
        )
    }
) {
    composable("home") { HomeScreen() }
    composable("detail/{id}") { DetailScreen() }
}
```

## Predictive Back Animation (Android 14+)

```kotlin
// Predictive Back uses STANDARD_DECELERATE interpolator
// This is handled automatically when using Compose Navigation 2.7+
// with enableOnBackInvokedCallback = true in AndroidManifest.xml

// For custom predictive back:
@RequiresApi(Build.VERSION_CODES.UPSIDE_DOWN_CAKE)
@Composable
fun PredictiveBackContent(onBack: () -> Unit) {
    val predictiveBackProgress by rememberPredictiveBackProgress()
    
    // Scale down slightly as user swipes back
    Box(
        modifier = Modifier
            .graphicsLayer {
                val scale = lerp(1f, 0.9f, predictiveBackProgress)
                scaleX = scale
                scaleY = scale
                // 8dp offset from edge during preview
                translationX = lerp(0f, 8.dp.toPx(), predictiveBackProgress)
            }
    ) {
        // Screen content
    }
}
```

## Element Animations

### Visibility (AnimatedVisibility)

```kotlin
// Fade + slide — standard show/hide
AnimatedVisibility(
    visible = isVisible,
    enter = fadeIn(animationSpec = tween(150)) +
            slideInVertically(
                animationSpec = tween(300, easing = EmphasizedDecelerateEasing),
                initialOffsetY = { it / 4 }  // starts 25% below final position
            ),
    exit = fadeOut(animationSpec = tween(100)) +
           slideOutVertically(
               animationSpec = tween(200, easing = EmphasizedAccelerateEasing),
               targetOffsetY = { it / 4 }
           )
) {
    Content()
}
```

### Size Changes (animateContentSize)

```kotlin
// Smooth expand/collapse
Card(
    modifier = Modifier.animateContentSize(
        animationSpec = spring(
            dampingRatio = Spring.DampingRatioNoBouncy,
            stiffness = Spring.StiffnessMediumLow
        )
    )
) {
    Column {
        Text("Title")
        if (isExpanded) {
            Text("Additional content that appears on expand")
        }
    }
}
```

### Value Animation (animate*AsState)

```kotlin
// Position
val offsetX by animateDpAsState(
    targetValue = if (isOpen) 0.dp else (-300.dp),
    animationSpec = spring(
        dampingRatio = Spring.DampingRatioNoBouncy,
        stiffness = Spring.StiffnessMedium
    ),
    label = "drawer offset"
)

// Color
val backgroundColor by animateColorAsState(
    targetValue = if (isSelected)
        MaterialTheme.colorScheme.primaryContainer
    else
        MaterialTheme.colorScheme.surface,
    animationSpec = tween(200, easing = StandardEasing),
    label = "card background"
)

// Float (scale, alpha, rotation)
val scale by animateFloatAsState(
    targetValue = if (isPressed) 0.95f else 1f,
    animationSpec = spring(stiffness = Spring.StiffnessHigh),
    label = "press scale"
)
```

### List Item Animations (Compose 1.7+)

```kotlin
LazyColumn {
    items(items, key = { it.id }) { item ->
        ItemComposable(
            item = item,
            modifier = Modifier.animateItem(  // handles add/remove/reorder
                fadeInSpec = tween(300),
                fadeOutSpec = tween(200),
                placementSpec = spring(stiffness = Spring.StiffnessMediumLow)
            )
        )
    }
}
```

## Reduced Motion Support

Always check for reduced motion preference:

```kotlin
@Composable
fun rememberReduceMotion(): Boolean {
    return LocalReduceMotion.current.enabled
}

// Usage
@Composable
fun AnimatedCard(content: @Composable () -> Unit) {
    val reduceMotion = LocalReduceMotion.current.enabled
    
    Card(
        modifier = Modifier.animateContentSize(
            animationSpec = if (reduceMotion) snap() else spring(...)
        )
    ) {
        content()
    }
}

// For decorative animations (particles, idle loops): skip entirely
if (!LocalReduceMotion.current.enabled) {
    DecorativeAnimation()
}
```

**Rule:** Decorative animations = opt-out with `LocalReduceMotion`. Functional animations (state change feedback) = keep but reduce duration by 70%.

## Shimmer / Loading Placeholders

```kotlin
@Composable
fun ShimmerEffect(modifier: Modifier = Modifier) {
    val transition = rememberInfiniteTransition(label = "shimmer")
    val shimmerTranslate by transition.animateFloat(
        initialValue = 0f,
        targetValue = 1000f,
        animationSpec = infiniteRepeatable(
            animation = tween(1200, easing = LinearEasing),
            repeatMode = RepeatMode.Restart
        ),
        label = "shimmer translate"
    )
    
    Box(
        modifier = modifier
            .background(
                brush = Brush.linearGradient(
                    colors = listOf(
                        MaterialTheme.colorScheme.surfaceVariant,
                        MaterialTheme.colorScheme.surface,
                        MaterialTheme.colorScheme.surfaceVariant
                    ),
                    start = Offset(shimmerTranslate - 500f, 0f),
                    end = Offset(shimmerTranslate, 0f)
                ),
                shape = MaterialTheme.shapes.small
            )
    )
}
```

## Performance Rules

| Rule | Rationale |
|---|---|
| Animate only `alpha`, `scale`, `translation`, `rotation` | These run on the GPU render thread |
| Avoid animating `size` with `fillMaxSize` in loops | Forces layout re-measurement on every frame |
| Use `graphicsLayer {}` for transforms instead of `Modifier.offset()` | `graphicsLayer` doesn't trigger recomposition |
| Label all `animateXAsState` with `label =` parameter | Enables Layout Inspector animation debugger |
| Never animate more than 3 properties simultaneously | Performance and perceptual clarity |
| Keep durations under 500ms for UI feedback | Longer feels sluggish; use spring for longer physical effects |
| Test on a mid-range device (not Pixel 9 Pro) | Ensures 60fps on real user hardware |

## Shared Element Transitions (Compose 1.7+)

```kotlin
// Define shared elements with matching keys
// List item
ListItem(
    modifier = Modifier.sharedElement(
        rememberSharedContentState(key = "note-${note.id}"),
        animatedVisibilityScope = this  // from AnimatedContent scope
    )
)

// Detail screen
DetailHeader(
    modifier = Modifier.sharedElement(
        rememberSharedContentState(key = "note-${note.id}"),
        animatedVisibilityScope = this
    )
)

// Wrap NavHost with SharedTransitionLayout
SharedTransitionLayout {
    NavHost(navController, startDestination = "list") {
        composable("list") {
            animatedComposable { ListScreen() }
        }
        composable("detail/{id}") {
            animatedComposable { DetailScreen() }
        }
    }
}
```
