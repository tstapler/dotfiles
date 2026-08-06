//! A `PushMetricExporter` that persists OTel metric data points to a local
//! SQLite database instead of shipping them over OTLP — cmdcrush is a
//! one-shot CLI with no collector to talk to, so the DB is the sink.
//! Read it back with `sqlite3` or a future `cmdcrush stats` subcommand.

use std::path::{Path, PathBuf};
use std::sync::Mutex;
use std::time::Duration;

use opentelemetry::KeyValue;
use opentelemetry_sdk::error::{OTelSdkError, OTelSdkResult};
use opentelemetry_sdk::metrics::data::{AggregatedMetrics, MetricData, ResourceMetrics};
use opentelemetry_sdk::metrics::exporter::PushMetricExporter;
use opentelemetry_sdk::metrics::Temporality;
use rusqlite::Connection;

pub struct SqliteMetricsExporter {
    conn: Mutex<Connection>,
}

/// OTel's numeric metric kinds (`u64`, `i64`, `f64`) don't all implement
/// `Into<f64>` (u64/i64 -> f64 can be lossy), so bridge them explicitly
/// instead of requiring a blanket conversion the SDK's own types don't offer.
trait ToF64: Copy {
    fn to_f64(self) -> f64;
}
impl ToF64 for u64 {
    fn to_f64(self) -> f64 {
        self as f64
    }
}
impl ToF64 for i64 {
    fn to_f64(self) -> f64 {
        self as f64
    }
}
impl ToF64 for f64 {
    fn to_f64(self) -> f64 {
        self
    }
}

impl SqliteMetricsExporter {
    pub fn open(path: &Path) -> rusqlite::Result<Self> {
        if let Some(parent) = path.parent() {
            std::fs::create_dir_all(parent).ok();
        }
        let conn = Connection::open(path)?;
        conn.pragma_update(None, "journal_mode", "WAL")?;
        conn.execute(
            "CREATE TABLE IF NOT EXISTS otel_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                exported_at TEXT NOT NULL,
                metric_name TEXT NOT NULL,
                attributes TEXT NOT NULL,
                value REAL,
                count INTEGER,
                sum_value REAL,
                min_value REAL,
                max_value REAL
            )",
            (),
        )?;
        Ok(Self {
            conn: Mutex::new(conn),
        })
    }

    fn attrs_to_json(attrs: &[KeyValue]) -> String {
        let mut map = serde_json::Map::new();
        for kv in attrs {
            map.insert(kv.key.as_str().to_string(), serde_json::Value::String(kv.value.to_string()));
        }
        serde_json::Value::Object(map).to_string()
    }

    fn insert_sum<T: ToF64>(
        &self,
        conn: &Connection,
        name: &str,
        data: &MetricData<T>,
    ) -> rusqlite::Result<()> {
        if let MetricData::Sum(sum) = data {
            let now = chrono::Utc::now().to_rfc3339();
            for dp in sum.data_points() {
                conn.execute(
                    "INSERT INTO otel_metrics (exported_at, metric_name, attributes, value) VALUES (?1, ?2, ?3, ?4)",
                    rusqlite::params![
                        now,
                        name,
                        Self::attrs_to_json(&dp.attributes().cloned().collect::<Vec<_>>()),
                        dp.value().to_f64(),
                    ],
                )?;
            }
        }
        Ok(())
    }

    fn insert_histogram<T: ToF64>(
        &self,
        conn: &Connection,
        name: &str,
        data: &MetricData<T>,
    ) -> rusqlite::Result<()> {
        if let MetricData::Histogram(hist) = data {
            let now = chrono::Utc::now().to_rfc3339();
            for dp in hist.data_points() {
                let min: Option<f64> = dp.min().map(ToF64::to_f64);
                let max: Option<f64> = dp.max().map(ToF64::to_f64);
                conn.execute(
                    "INSERT INTO otel_metrics (exported_at, metric_name, attributes, count, sum_value, min_value, max_value) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7)",
                    rusqlite::params![
                        now,
                        name,
                        Self::attrs_to_json(&dp.attributes().cloned().collect::<Vec<_>>()),
                        dp.count() as i64,
                        dp.sum().to_f64(),
                        min,
                        max,
                    ],
                )?;
            }
        }
        Ok(())
    }
}

impl PushMetricExporter for SqliteMetricsExporter {
    async fn export(&self, metrics: &ResourceMetrics) -> OTelSdkResult {
        let conn = self
            .conn
            .lock()
            .map_err(|e| OTelSdkError::InternalFailure(format!("stats db lock poisoned: {e}")))?;

        for scope in metrics.scope_metrics() {
            for metric in scope.metrics() {
                let name = metric.name().to_string();
                let result = match metric.data() {
                    AggregatedMetrics::U64(data) => match data {
                        MetricData::Sum(_) => self.insert_sum(&conn, &name, data),
                        MetricData::Histogram(_) => self.insert_histogram(&conn, &name, data),
                        _ => Ok(()),
                    },
                    AggregatedMetrics::I64(data) => match data {
                        MetricData::Sum(_) => self.insert_sum(&conn, &name, data),
                        MetricData::Histogram(_) => self.insert_histogram(&conn, &name, data),
                        _ => Ok(()),
                    },
                    AggregatedMetrics::F64(data) => match data {
                        MetricData::Sum(_) => self.insert_sum(&conn, &name, data),
                        MetricData::Histogram(_) => self.insert_histogram(&conn, &name, data),
                        _ => Ok(()),
                    },
                };
                result.map_err(|e| OTelSdkError::InternalFailure(format!("stats db insert failed: {e}")))?;
            }
        }
        Ok(())
    }

    fn force_flush(&self) -> OTelSdkResult {
        Ok(())
    }

    fn shutdown_with_timeout(&self, _timeout: Duration) -> OTelSdkResult {
        Ok(())
    }

    fn temporality(&self) -> Temporality {
        Temporality::Cumulative
    }
}

pub fn default_db_path() -> PathBuf {
    if let Ok(p) = std::env::var("CMDCRUSH_STATS_DB") {
        return PathBuf::from(p);
    }
    let base = std::env::var("HOME").map(PathBuf::from).unwrap_or_else(|_| std::env::temp_dir());
    base.join(".cache").join("cmdcrush").join("stats.db")
}
