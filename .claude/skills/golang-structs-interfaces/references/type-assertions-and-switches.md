# Type Assertions & Type Switches

## Safe Type Assertion

Type assertions MUST use the comma-ok form to avoid panics:

```go
// Good — safe
s, ok := val.(string)
if !ok {
    // handle
}

// Bad — panics if val is not a string
s := val.(string)
```

## Type Switch

Discover the dynamic type of an interface value:

```go
switch v := val.(type) {
case string:
    fmt.Println(v)
case int:
    fmt.Println(v * 2)
case io.Reader:
    io.Copy(os.Stdout, v)
default:
    fmt.Printf("unexpected type %T\n", v)
}
```

## Optional Behavior with Type Assertions

Check if a value supports additional capabilities without requiring them upfront:

```go
type Flusher interface {
    Flush() error
}

func writeData(w io.Writer, data []byte) error {
    if _, err := w.Write(data); err != nil {
        return err
    }
    // Flush only if the writer supports it
    if f, ok := w.(Flusher); ok {
        return f.Flush()
    }
    return nil
}
```

This pattern is used extensively in the standard library (e.g., `http.Flusher`, `io.ReaderFrom`).
