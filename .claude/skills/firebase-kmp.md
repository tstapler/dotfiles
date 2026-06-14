---
name: firebase-kmp
description: Firebase + Firestore best practices for Kotlin Multiplatform (KMP) apps,
  including the wasmJs target via JS interop and Android via the gitlive SDK. Apply
  when writing Firestore security rules, implementing auth flows, creating Firestore
  repositories, or debugging permission errors. Covers create/update rule distinction,
  offline persistence behavior, auth race conditions, DataStore integration, and
  wasmJs interop pitfalls. Use this to avoid the specific bugs that have recurred
  in the Sortie project.
---

# Firebase + Firestore for Kotlin Multiplatform

Apply these rules when writing or reviewing any code that touches Firebase Auth,
Firestore, Firestore security rules, or DataStore in a KMP project.

---

## 1. Firestore Security Rules — The Three Most Dangerous Mistakes

### Mistake 1: `setDoc(merge:true)` does NOT always trigger `update`

The rule that fires depends on whether the document **already exists on the server**,
NOT on which SDK method you called:

| SDK call | Doc exists? | Rule triggered |
|---|---|---|
| `setDoc(ref, data)` | No | **create** |
| `setDoc(ref, data)` | Yes | **update** |
| `setDoc(ref, data, { merge:true })` | No | **create** |
| `setDoc(ref, data, { merge:true })` | Yes | **update** |
| `updateDoc(ref, data)` | No | Client-side error (never reaches rules) |
| `updateDoc(ref, data)` | Yes | **update** |
| `addDoc(collection, data)` | Always new | **create** |

**Implication**: if you call `setDoc(merge:true)` (patchDocument) on a **non-existent**
user doc trying to set `householdId`, Firestore fires the `update` rule. The `update`
rule accesses `resource.data` — which is null for a non-existent doc — and the whole
rule evaluation errors → **permission denied**.

**Fix**: use `setDoc` (no merge) for initial document creation. This triggers `create`.

```javascript
// Creates doc → triggers 'create' rule
await setDoc(docRef, data);

// Merges into doc → triggers 'create' if new, 'update' if existing
await setDoc(docRef, data, { merge: true });
```

### Mistake 2: `allow write: if false` does NOT block `allow create`

Rules use OR logic. Any `allow` statement that matches grants access. A `false`
condition only adds a false branch — it never cancels a true branch elsewhere.

```
// This DOES allow create even with write:false
match /users/{userId} {
  allow write: if false;                               // ← this does NOT block create
  allow create: if request.auth.uid == userId;         // ← this allows create
}
```

**Always do**: write explicit `allow create`, `allow update`, `allow delete` rules.
Never rely on `allow write: if false` to block a sub-operation.

### Mistake 3: `request.query.filters` does not exist

`request.query` only has three fields: `limit`, `offset`, `orderBy`. There is no way
to inspect a query's `where()` clauses in security rules.

```
// WRONG — request.query.filters does not exist, rule always errors/denies
allow list: if 'inviteCode' in request.query.filters;

// RIGHT — enforce filter by putting the dimension in the collection path
match /households/{householdId}/trips/{tripId} {
  allow list: if isMember(householdId);  // path binding IS the filter
}
```

**Always do**: put the primary access-control dimension in the Firestore path, not
just in a field. A query scoped to `/households/{hid}/trips` automatically restricts
to that household.

---

## 2. Firestore Security Rules — Correct Patterns

### `resource.data` in update rules

`resource` is the document's current server state (before the write).
For `create` rules, `resource` is `null` — never access `resource.data` in a create rule.
For `update` rules, always guard: `resource != null && resource.data.field`.

```
// Update rule for setting householdId for the first time
allow update: if request.auth.uid == userId
    && (
      !("householdId" in request.resource.data)       // not writing householdId → ok
      || !("householdId" in resource.data)            // first write → ok (resource.data exists since this is update)
      || request.resource.data.householdId == resource.data.householdId  // idempotent → ok
    );
```

### `isMember` helper — get() costs money

Every `get()` or `exists()` in rules counts as a billed Firestore read.
Limit: 10 `get()` calls per single-document request, 20 per transaction.

```
// Expensive — called for every subcollection access
function isMember(householdId) {
  return request.auth != null
    && get(/databases/$(database)/documents/users/$(request.auth.uid)).data.householdId == householdId;
}
```

Cache results in `let` bindings when the same doc is read multiple times in one rule chain.

### allow list vs. allow get vs. allow read

`allow read` = `allow get` + `allow list`. Separate them when needed:

```
match /households/{householdId} {
  allow get: if isMember(householdId);   // single doc read: members only
  allow list: if request.auth != null    // query by inviteCode: any auth'd user
    && request.query.limit <= 1;
}
```

### hasOnly / hasAll / hasAny for update rules

For update rules, check **only changed fields** using `diff()`:

```
// Only allows updating name and status — nothing else
allow update: if request.resource.data.diff(resource.data)
  .affectedKeys().hasOnly(['name', 'status']);
```

Do not use `request.resource.data.keys().hasOnly(...)` in update rules —
it includes all existing fields, making an allowlist nearly impossible.

---

## 3. Firebase Auth + KMP — The Profile Race Condition

### The problem

`onAuthStateChanged` fires **immediately** with the partial Firebase Auth user
(`uid`, `email`, `displayName`). The Firestore profile fetch (`loadUserProfile`)
runs **asynchronously** after. The UI can become interactive before the user doc
exists in Firestore.

If the user clicks "Create Group" before `ensureUserDocExists` finishes:
1. `createHousehold` calls `patchDocument("users/$uid", {householdId: newId})`
2. The user doc doesn't exist yet → `setDoc(merge:true)` triggers `create` rule
3. `create` rule: `!("householdId" in request.resource.data)` → FALSE → **denied**

### The fix: emission counting

`observeCurrentUser()` emits twice per sign-in:
1. **Emission 1**: partial user (immediate, from Firebase Auth)
2. **Emission 2**: full user (after `loadUserProfile` + `ensureUserDocExists`)

Gate interactive onboarding on the second emission:

```kotlin
// AuthViewModel
private var authEmissionCount = 0
private val _profileReady = MutableStateFlow(false)
val profileReady: StateFlow<Boolean> = _profileReady.asStateFlow()

init {
    viewModelScope.launch {
        authRepository.observeCurrentUser().collect { user ->
            if (user == null) { authEmissionCount = 0; _profileReady.value = false }
            else {
                authEmissionCount++
                if (authEmissionCount >= 2) _profileReady.value = true
            }
            _currentUser.value = user
        }
    }
}

// SortieApp — don't show onboarding buttons until profile is ready
OnboardingScreen(isLoading = !profileReady || !inviteChecked || onboardingLoading)
```

### Always use createDocument for first user doc creation

`ensureUserDocExists` must use `setDoc` WITHOUT merge to trigger `create` rule:

```kotlin
// WRONG — triggers 'update' on non-existent doc → permission denied
firestoreClient.patchDocument("users/${uid}", fields)

// RIGHT — triggers 'create' rule → allowed
firestoreClient.createDocument("users/${uid}", fields)
```

### observeCurrentUser — single listener, real unsubscribe

```kotlin
override fun observeCurrentUser(): Flow<User?> = callbackFlow {
    val unsubscribeHandle = JsInterop.onAuthStateChange { jsUser ->
        val user = jsUser?.let { extractPartialUser(it) }
        _currentUser.value = user
        trySend(user)
        user?.let { partial ->
            GlobalScope.launch {
                val full = loadUserProfile(partial.uid, partial)
                if (_currentUser.value?.uid == partial.uid) {  // guard against concurrent signOut
                    _currentUser.value = full
                    trySend(full)
                }
            }
        }
    }
    awaitClose { jsInvokeNoArgs(unsubscribeHandle) }  // MUST unsubscribe
}
```

Never register a second `onAuthStateChanged` listener in an `init` block. One listener
is enough; registering two causes duplicate profile loads and tricky state races.

---

## 4. Firestore Offline Persistence — The Hidden Behavior

### `await setDoc(...)` hangs forever when offline

With `persistentLocalCache`, write Promises resolve only after **server acknowledgment**.
If the device is offline, the write queues locally but the Promise hangs indefinitely.

```kotlin
// BAD — navigation/UI update blocked by offline write
suspend fun saveTrip(trip: Trip) {
    firestoreClient.patchDocument("trips/${trip.id}", encode(trip))
    navController.navigate(TripList)  // never reached while offline
}

// GOOD — fire and forget write, drive UI from snapshot listener
fun saveTrip(trip: Trip, scope: CoroutineScope) {
    scope.launch(CoroutineExceptionHandler { _, e -> showError(e.message) }) {
        firestoreClient.patchDocument("trips/${trip.id}", encode(trip))
    }
    navController.navigate(TripList)  // proceeds immediately
}
```

### Permission-denied errors arrive late with persistence

If a write is queued offline and the security rules change before the device reconnects,
the write is rejected when it finally reaches the server. The `Promise` rejects long
after the original call. Always attach a `CoroutineExceptionHandler` to write coroutines.

### Real-time listeners: prefer `onSnapshot` over poll-then-fetch

`WasmTripRepository` uses 30-second polling. Prefer `onSnapshot` for live data:

```javascript
// jsInterop.js — already implemented
export function firestoreOnSnapshot(collectionPath, onUpdate, onError) { ... }
```

---

## 5. Jetpack DataStore in KMP (including wasmJs)

DataStore 1.2+ supports Android, iOS, JVM, JS, and **wasmJs** via `WebLocalStorage`.

### When to use DataStore vs. Firestore

| DataStore | Firestore |
|---|---|
| User preferences (theme, locale) | Shared data needing multi-device sync |
| Auth tokens, feature flags | Trip lists, packing items |
| Onboarding step tracking | Real-time collaborative state |
| UI state that never syncs | Queryable server-side data |

### Setup (KMP + wasmJs)

```kotlin
// build.gradle.kts — commonMain
implementation("androidx.datastore:datastore-preferences:1.2.1")

// expect/actual pattern
expect fun createDataStore(): DataStore<Preferences>

// wasmJsMain (same as jsMain)
actual fun createDataStore(): DataStore<Preferences> = DataStoreFactory.create(
    storage = WebLocalStorage(
        serializer = PreferencesSerializer,
        name = "sortie.preferences_pb"
    )
)

// androidMain
actual fun createDataStore(context: Context): DataStore<Preferences> =
    DataStoreFactory.create(
        storage = FileStorage(
            serializer = PreferencesSerializer,
            produceFile = { context.filesDir.resolve("sortie.preferences_pb") }
        )
    )
```

**Always create as a singleton.** Multiple instances on the same file/key throw.

---

## 6. wasmJs Interop Pitfalls

### No `dynamic` type — use `JsAny`

```kotlin
// WRONG — dynamic not supported in wasmJs
fun foo(): dynamic = js("{ key: 'value' }")

// RIGHT
@JsFun("() => ({ key: 'value' })")
external fun makeObj(): JsAny

@JsFun("(obj) => obj.key")
external fun getKey(obj: JsAny): String
```

### ES module imports only

```kotlin
@file:JsModule("./jsInterop.js")
package com.sortie.shared.interop

external object JsInterop {
    fun triggerGoogleSignInPopup(): Unit
    fun onAuthStateChange(callback: (JsAny?) -> Unit): JsAny
}
```

All wasmJs external declarations must use `@JsModule` with ESM paths. No CommonJS.

### `GlobalScope.launch` — use sparingly, always handle exceptions

wasmJs is single-threaded. `GlobalScope.launch` is unstructured — exceptions are
silently dropped. Reserve for truly fire-and-forget operations; always add a handler:

```kotlin
@OptIn(DelicateCoroutinesApi::class)
GlobalScope.launch {
    val full = loadUserProfile(uid, fallback)
    if (_currentUser.value?.uid == uid) {
        _currentUser.value = full
        trySend(full)
    }
}
// Better long-term: inject a structured CoroutineScope tied to the app lifecycle
```

### Promise bridging

```kotlin
// JsAny returned from JS interop is a Promise — use awaitString() / awaitUnit()
@Suppress("UNCHECKED_CAST")
private suspend fun JsAny.awaitString(): String {
    val promise = this as kotlin.js.Promise<JsAny>
    return jsToString(promise.await())
}
```

---

## 7. Quick Checklist Before Any Firestore Write

Before writing `patchDocument` / `createDocument`:

1. **Does the target document exist?**
   - Yes → `patchDocument` (setDoc merge:true, triggers `update` rule)
   - No → `createDocument` (setDoc without merge, triggers `create` rule)
   - Unknown → ensure it exists first OR write a rule that handles both

2. **Does your security rule handle both create AND update paths?**
   - If you use `patchDocument` on a path that might not exist, your `allow update` rule
     must not access `resource.data` (it will be null and cause a permission error)

3. **Is the user profile loaded before you write householdId to the user doc?**
   - Check `profileReady` state; don't allow interaction until second auth emission

4. **Are you using `setDoc` without merge for the first creation of any document?**
   - `ensureUserDocExists`, `createHousehold`, `createDocument` all use setDoc (no merge)
   - Only `patchDocument` uses setDoc with merge (for existing documents)

5. **Does your write coroutine have error handling?**
   - All fire-and-forget writes need `CoroutineExceptionHandler`
   - Offline writes queue silently; permission errors arrive late on reconnect
