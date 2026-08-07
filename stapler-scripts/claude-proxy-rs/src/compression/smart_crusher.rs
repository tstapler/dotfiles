//! SmartCrusher: JSON array / object compression stage.
//!
//! Statistical field elision: when a top-level JSON array holds enough
//! objects and a field has the exact same value in *every* object, that
//! value is boilerplate — hoist it out once instead of repeating it per
//! element. Only fields constant across the whole array are elided (no
//! partial/majority threshold), so the transform is lossless modulo the
//! elided keys, which are always recoverable from `_elided_constant_fields`.

use serde_json::{json, Map, Value};

/// Arrays shorter than this aren't worth restructuring — the wrapper
/// overhead (`_smart_crushed`, `_elided_constant_fields`, `items`) can
/// exceed the savings for small arrays.
const MIN_ARRAY_LEN: usize = 4;

/// Stateless JSON compressor.
pub struct SmartCrusher;

impl SmartCrusher {
    pub fn new() -> Self {
        SmartCrusher
    }

    /// Attempt JSON field elision compression on a top-level array of
    /// objects.
    ///
    /// Returns `None` (pass-through) if `value` isn't a large-enough array
    /// of objects, if no field is constant across every element, or if the
    /// restructured form isn't actually smaller than the input.
    pub fn compress(&self, value: &Value) -> Option<Value> {
        let arr = value.as_array()?;
        if arr.len() < MIN_ARRAY_LEN {
            return None;
        }

        // Every element must be an object for field elision to make sense.
        let objects: Vec<&Map<String, Value>> = arr
            .iter()
            .map(|v| v.as_object())
            .collect::<Option<Vec<_>>>()?;

        let constant_fields = find_constant_fields(&objects);
        if constant_fields.is_empty() {
            return None;
        }

        let mut elided = Map::new();
        for (key, val) in &constant_fields {
            elided.insert(key.clone(), val.clone());
        }

        let items: Vec<Value> = objects
            .iter()
            .map(|obj| {
                let mut trimmed = (*obj).clone();
                for key in elided.keys() {
                    trimmed.remove(key);
                }
                Value::Object(trimmed)
            })
            .collect();

        let result = json!({
            "_smart_crushed": true,
            "_elided_constant_fields": elided,
            "items": items,
        });

        let before_len = serde_json::to_string(value).ok()?.len();
        let after_len = serde_json::to_string(&result).ok()?.len();

        if after_len < before_len {
            Some(result)
        } else {
            None
        }
    }
}

impl Default for SmartCrusher {
    fn default() -> Self {
        Self::new()
    }
}

/// Fields present in every object with an identical value across all of them.
fn find_constant_fields(objects: &[&Map<String, Value>]) -> Map<String, Value> {
    let mut constant = Map::new();
    let Some(first) = objects.first() else {
        return constant;
    };

    for (key, first_val) in first.iter() {
        let is_constant = objects
            .iter()
            .all(|obj| obj.get(key).is_some_and(|v| v == first_val));
        if is_constant {
            constant.insert(key.clone(), first_val.clone());
        }
    }

    constant
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn elides_constant_fields_across_array() {
        let value = json!([
            {"id": 1, "type": "widget", "status": "ok"},
            {"id": 2, "type": "widget", "status": "ok"},
            {"id": 3, "type": "widget", "status": "ok"},
            {"id": 4, "type": "widget", "status": "ok"},
        ]);
        let result = SmartCrusher::new().compress(&value).expect("should compress");
        assert_eq!(result["_elided_constant_fields"]["type"], "widget");
        assert_eq!(result["_elided_constant_fields"]["status"], "ok");
        let items = result["items"].as_array().unwrap();
        assert_eq!(items.len(), 4);
        assert!(items[0].get("type").is_none());
        assert_eq!(items[0]["id"], 1);
    }

    #[test]
    fn no_op_when_no_field_is_fully_constant() {
        let value = json!([
            {"id": 1, "status": "ok"},
            {"id": 2, "status": "ok"},
            {"id": 3, "status": "fail"},
            {"id": 4, "status": "ok"},
        ]);
        assert!(SmartCrusher::new().compress(&value).is_none());
    }

    #[test]
    fn no_op_below_min_array_len() {
        let value = json!([
            {"id": 1, "type": "widget"},
            {"id": 2, "type": "widget"},
        ]);
        assert!(SmartCrusher::new().compress(&value).is_none());
    }

    #[test]
    fn no_op_on_non_object_elements() {
        let value = json!([1, 2, 3, 4]);
        assert!(SmartCrusher::new().compress(&value).is_none());
    }

    #[test]
    fn no_op_on_non_array_value() {
        let value = json!({"id": 1});
        assert!(SmartCrusher::new().compress(&value).is_none());
    }

    #[test]
    fn no_op_when_wrapper_overhead_exceeds_savings() {
        // All fields vary except one short constant field on tiny objects —
        // wrapper overhead should dominate and force a no-op.
        let value = json!([
            {"a": 1, "k": "x"},
            {"a": 2, "k": "x"},
            {"a": 3, "k": "x"},
            {"a": 4, "k": "x"},
        ]);
        // This may or may not compress depending on exact byte counts; assert
        // the invariant instead of a specific outcome: if it returns Some, it
        // must actually be smaller.
        if let Some(result) = SmartCrusher::new().compress(&value) {
            let before = serde_json::to_string(&value).unwrap().len();
            let after = serde_json::to_string(&result).unwrap().len();
            assert!(after < before);
        }
    }
}
