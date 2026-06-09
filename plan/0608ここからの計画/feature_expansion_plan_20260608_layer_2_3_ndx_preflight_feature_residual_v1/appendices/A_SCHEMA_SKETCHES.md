<!--
作成日: 2026-06-08_20:18 JST
更新日: 2026-06-08_20:18 JST
-->

# Appendix A: Schema Sketches

## ndx_data_source_resolution.v1

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "schemas/ndx_data_source_resolution.v1.schema.json",
  "type": "object",
  "additionalProperties": false,
  "required": ["schema_version", "dag_id", "dag_artifact_hash", "sources"],
  "properties": {
    "schema_version": {"const": "ndx_data_source_resolution.v1"},
    "dag_id": {"type": "string"},
    "dag_artifact_hash": {"type": "string", "pattern": "^sha256:[0-9a-f]{64}$"},
    "sources": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["source_id", "status", "external_api_required", "credentials_required"],
        "properties": {
          "source_id": {"type": "string"},
          "status": {"enum": ["required", "optional", "deferred", "excluded"]},
          "external_api_required": {"type": "boolean"},
          "credentials_required": {"type": "boolean"},
          "proxy_for": {"type": "array", "items": {"type": "string"}},
          "caveats": {"type": "array", "items": {"type": "string"}}
        }
      }
    }
  }
}
```

## ndx_feature_manifest.v1

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "schemas/ndx_feature_manifest.v1.schema.json",
  "type": "object",
  "additionalProperties": false,
  "required": ["schema_version", "dag_id", "dag_artifact_hash", "row_count", "columns", "leakage_check"],
  "properties": {
    "schema_version": {"const": "ndx_feature_manifest.v1"},
    "dag_id": {"type": "string"},
    "dag_artifact_hash": {"type": "string"},
    "row_count": {"type": "integer", "minimum": 0},
    "columns": {"type": "array", "items": {"type": "string"}},
    "dropped_row_count": {"type": "integer", "minimum": 0},
    "leakage_check": {
      "type": "object",
      "required": ["status", "source_ts_max_lte_feature_ts", "outcome_not_in_model_inputs"],
      "properties": {
        "status": {"enum": ["pass", "fail"]},
        "source_ts_max_lte_feature_ts": {"type": "boolean"},
        "outcome_not_in_model_inputs": {"type": "boolean"}
      }
    }
  }
}
```

## ndx_open_gap_residual_manifest.v1

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "schemas/ndx_open_gap_residual_manifest.v1.schema.json",
  "type": "object",
  "additionalProperties": false,
  "required": ["schema_version", "dag_id", "dag_artifact_hash", "feature_manifest_hash", "model_config_hash", "row_count", "factor_columns"],
  "properties": {
    "schema_version": {"const": "ndx_open_gap_residual_manifest.v1"},
    "dag_id": {"type": "string"},
    "dag_artifact_hash": {"type": "string"},
    "feature_manifest_hash": {"type": "string"},
    "model_config_hash": {"type": "string"},
    "row_count": {"type": "integer", "minimum": 0},
    "factor_columns": {"type": "array", "items": {"type": "string"}},
    "model_type": {"enum": ["rolling_ols"]},
    "min_window": {"type": "integer", "minimum": 2}
  }
}
```
