# Validation Plan: gphotos-organizer-pipeline

**Date**: 2026-10-16
**Inputs**: `implementation/plan.md` (72 stories, 209 tasks, 10 epics, 13 waves; recounted by `grep -c '^#### Story'` and `'^##### Task'` and by `python3 implementation/waves.py --check` after triad repair pass 3), `requirements.md`, `design/ux.md` (UX-01..UX-118), `implementation/adversarial-review.md` (open concerns N1-N4).
**Conventions**: `G/` = `stapler-scripts/gphotos-organizer/`. Test names are plain snake_case functions `test_<unit>_should_<expected>_when_<condition>` (the language-native form of `methodName_should_ExpectedBehavior_When_Condition`), each in a `G/tests/test_*.py` file run as `uv run test_x.py` through `G/tests/_test_runner.py` (`run_tests(globals())`), the same convention as `stapler-scripts/llm-sync/test_review_gate.py` and `_test_runner.py`. No pytest. Domain Glossary terms (`ContentKey`, `PartialDate`, `PlaceholderClass`, `DecisionStatus`, `WriteState`, `UploadGate`, `AuditClear`, `DenyList`, ...) are used verbatim.

## Happy Path Scenario
Given the 2026-10-16 baseline (604/628 albums grandfathered as `uploaded_unverified`, a legacy-written placeholder population on the drive, and `2021 random photos` (id `9102dede1a50`, 9,161 files) deny-listed), when Tyler runs `index -> analyze -> fuse -> review -> plan -> fix-metadata --apply -> audit -> upload` on a scanned print with no EXIF, then the file's date is a `DateDecision` carrying confidence and voters, it is written to EXIF only above `--min-confidence` through a journaled, read-back-verified write (reversible by `undo --run`), an unresolved or placeholder-dated sibling is held in the review list and blocked at the `UploadGate`, and a later `audit` shows no remote item dated in the upload window.

## Plan Amendments These Tests Presuppose (found while designing the suite)
The four open reviewer concerns are folded in below as tests. `plan.md` Stories 1.9 and 8.7 do not yet state the behavior those tests pin, so the plan must absorb them before Wave W3 (1.9) and W11 (8.7) or the tests have nothing to bind to:
1. **N1** Story 8.7 `--apply` re-runs the Story 1.9 classifier with the current `FolderContext` and current on-disk value; a stored classification is a hint, not authority.
2. **N2** Story 8.7 adds `placeholders summary` (per-album grouped counts, signals, 5-file sample) and `placeholders revert --album <id>` (per-album dry-run/apply, one `run_id` per album invocation); weak-evidence classes require `--include-weak`.
3. **N3** Decision recorded by these tests: video is **out of scope** for 1.9/8.7 (documented gap, enforced by tests: videos never anchors, never reverted, counted as "not classified" in the scan report). Extending to QuickTime tags is a separate story; the `test_n3_*_extension_*` rows say which tests flip if the owner reverses this.
4. **N4** Signal (e) orders by `name.lower()` (the legacy writer's key, `metadata.py:123-125`), not by natural sort, and tolerates a bounded number of gaps (`max_gaps=1`). Note: the reviewer proposed "case-insensitive natural sort"; natural sort would order `a10` after `a2`, but the legacy writer put `a10` before `a2`, so natural sort would mis-reconstruct the ladder. The tests pin `name.lower()`.

## Amendment status (repair pass, 2026-10-16)
All four amendments above are now written into `plan.md`: N1, N2 and N3 in Story 8.7 (acceptance criteria "Selection is re-validated at apply", "Reviewable in pieces, and weak classes are opt-in", "Videos are out of scope") and Story 1.9 ("Videos are out of scope"); N4 in Story 1.9 (signal (e): `name.lower()`, `max_gaps=1`, natural sort rejected). Correction to item 4: the legacy sort key is `sorted(..., key=lambda p: p.name.lower())` at `G/metadata.py:119-122` (VERIFIED by reading the file), not `:123-125`. Tests renamed or added by the repair pass (to be written in Phase 5): `test_status_migration.py` now maps `fixed` and `verified` to `legacy_unverified` (not `written`) and `pending_fix` to `pending`; `test_upload_gate_v1.py` gains a row for a `UserOverride` / filename-anchor file with no `Verified` write (blocked) and a `source=exif` backed anchor (passes), a row for `unobservable` coverage and `baseline_count=0` (blocked), and a video row (not exempt); `test_plan_apply.py` gains rows for anchors/overrides written by `plan`, the preflight order, typed plan-id and `--yes`, and the backup-attestation, canary and free-space refusals (the typed token later changed from the plan id to the file count, triad repair pass 1); new files `test_drive_backup.py`, `test_precision_gate.py`, `test_anchor_census.py`, `test_seq_neighbor.py`, `test_evidence_redact.py`; `test_cli_shell.py` gains the `COMMANDS`/`GROUPS`/`LEGACY` naming-rule rows; `test_privacy.py` gains the album-title scan and the data-dir-inside-git/synced-folder refusal. Flagged-album totals in examples use 137.

## Requirement Catalog (37 IDs, derived from `requirements.md` and the plan header; SM1, SM2, SM5, SM6 revised by triad repair pass 1)

| ID | Source in requirements.md | Short description |
|---|---|---|
| S1 | In Scope 1, Open Questions 1-3 | Survey / build-vs-adopt decisions recorded (ADR-001..011, spikes) |
| S2 | In Scope 2 | Plugin architecture: interface, registry, per-file cache, fusion |
| S3a | In Scope 3 | Face cluster + identity labeling plugin |
| S3b | In Scope 3 | Age estimation plugin |
| S3c | In Scope 3 | Anchor calibration against known-date photos |
| S3d | In Scope 3 | Era-by-appearance (incl. optional cloud variant) |
| S3e | In Scope 3 | Date inference / fusion with sanity guards (birth bounds, folder-year bounds) |
| S4 | In Scope 4 | Review flow for low-confidence dates; EXIF write for high-confidence |
| S5 | In Scope 5 | Upload audit + remediation path |
| S6 | In Scope 6 | Truthful `metadata_status` / `upload_status`; plain-function tests |
| SM1 | Success Metric 1 | Bounded violations = 0 on observable albums, with the numeric bound B (decision/folder/filename `latest` + 1 year), `unbounded` and `unobservable` reported, baseline at the first audit; includes the audit enumeration that was the old Metric 5 |
| SM2 | Success Metric 2 | Held-out anchor median + p90 error by decade, color and age band each run; targets set after the baseline run (children +/-2, adults +/-8 provisional) |
| SM3 | Success Metric 3 | Every inferred date has confidence + provenance; only above-threshold written, rest to review |
| SM4 | Success Metric 4 | New analysis step as a plugin without editing `cli.py` core flow |
| SM5 | Success Metric 5 | Remediation of already-uploaded items: fixed / waived / open counts, target open = 0 |
| SM6 | Success Metric 6 | Review burden: open items by source, decided by action, auto-dated vs reviewed ratio, targets after baseline |
| C1 | Constraints: Privacy | Local by default; cloud only when explicitly enabled per run |
| C2 | Constraints: platform | Linux, uv/PEP 723, no GPU |
| C3 | Constraints: idempotent | Idempotent, resumable, dry-run/backup before source modification |
| C4 | Constraints: 2021 | Never upload `2021 random photos` until dates resolved |
| NF1 | NFR Performance | ~17k images overnight on CPU; results cached per file hash; reruns incremental |
| NF2 | NFR Scalability | Tens of thousands of images, single machine |
| NF3 | NFR Security | Confidential: biometric-adjacent data protected (modes 600/700, no names in logs) |
| NF4 | NFR Data residency | Embeddings/caches on local disk, not in dotfiles git |
| OB1 | Observability | Per-run report, loguru structured logs, local result store |
| RC1 | Risk Control | Dry-run default; recorded original-value journal; every write reversible |
| RC2 | Risk Control | Per-plugin enable flags; cloud off unless `--allow-cloud` |
| RC3 | Risk Control | Confidence threshold gates all writes |
| RC4 | Risk Control | Upload only after audit passes |
| BL1 | Baseline / Problem Statement | Placeholder `YYYY:01:01 12:00:00` fallback eliminated |
| BL2 | Baseline: quota | 429 handling exercised against a fake before real use |
| BL3 | Baseline: API limits | Google Photos date-edit/read capability confirmed by experiment |
| X1 | Plan header "measured fact" | Legacy-written placeholder population detected and quarantined (never anchors) |
| N1 | adversarial-review N1 | Revert selection re-validated at `--apply` |
| N2 | adversarial-review N2 | Per-album apply/summaries for the ~15k-file revert pool |
| N3 | adversarial-review N3 | Video tags: covered or gap documented and enforced |
| N4 | adversarial-review N4 | Signal (e) sort order and gap tolerance |

## Requirement -> Test Mapping

Each row: Requirement | Test File (`G/tests/`) | Test Name | Type | Scenario. Integration = real SQLite, real exiftool 13.55 on generated fixtures, or the fake `rclone` / `exiftool` executables selected by `GPHOTOS_RCLONE` / `GPHOTOS_EXIFTOOL`.

| Requirement | Test File | Test Name | Type | Scenario |
|-------------|-----------|-----------|------|----------|
| S1: survey/ADRs | test_adr_index.py | test_adr_directory_should_list_adr_001_to_011_with_status_when_scanned | Unit | Happy path: all 11 ADR files present, each has Status and Alternatives rejected |
| S1: survey/ADRs | test_adr_index.py | test_adr_lint_should_fail_when_adr_lacks_status_or_rejected_alternatives | Unit | Error path: synthetic ADR missing a section is rejected |
| S1: survey/ADRs | test_spike_outcomes.py | test_adr_006_and_adr_008_should_record_spike_outcomes_when_spikes_4_1_and_9_1_complete | Integration | Reads the real ADR files; fails if timing numbers (4.1) or capability findings (9.1: ModTime, patch response, undated placement, album re-use) are absent |
| S2: plugin architecture | test_contract.py | test_observation_should_raise_frozen_instance_error_when_field_assigned | Unit | Happy path: `Evidence` immutable |
| S2: plugin architecture | test_contract.py | test_confidence_should_raise_value_error_when_outside_zero_to_one | Unit | Error path: `Confidence(1.2)` |
| S2: plugin architecture | test_registry.py | test_registry_load_should_not_import_disabled_module_when_only_folder_year_enabled | Unit | `ml_plugins.faces` absent from `sys.modules` |
| S2: plugin architecture | test_registry.py | test_registry_order_should_raise_plugin_cycle_error_naming_both_when_after_dag_cyclic | Unit | Error path: age<->faces |
| S2: plugin architecture | test_runner.py | test_runner_should_report_60_cached_40_computed_when_60_of_100_rows_exist | Unit | Per-file cache |
| S2: plugin architecture | test_runner.py | test_runner_should_store_nine_rows_and_one_error_row_when_plugin_raises_on_file_seven | Unit | Error path: exit 0, `errors.jsonl`, `--retry-failed` hint |
| S2: plugin architecture | test_store.py | test_evidence_insert_should_be_idempotent_and_retain_stale_rows_when_plugin_version_bumped | Integration | Real SQLite: same key twice -> one row; version bump keeps old row |
| S2: plugin architecture | test_e2e_smoke.py | test_toy_plugin_should_add_three_evidence_rows_with_cli_py_unchanged_when_registry_entry_added | Integration | `registry.d/toy.toml` + plugin file only; `git diff --stat G/cli.py` empty |
| S3a: faces/identity | test_face_store.py | test_faces_plugin_should_flag_40px_face_low_quality_and_exclude_from_centroid_when_two_faces_found | Unit | Stub detector, canned boxes |
| S3a: faces/identity | test_face_store.py | test_faces_plugin_should_emit_decode_failed_abstain_and_error_row_when_jpeg_truncated | Unit | Error path: no crash |
| S3a: faces/identity | test_cluster.py | test_cluster_should_give_same_partition_with_outliers_minus_one_when_input_order_shuffled | Unit | Determinism over synthetic L2-normalised embeddings |
| S3a: faces/identity | test_cluster.py | test_cluster_should_separate_f1_f2_when_cannot_link_constraint_recorded | Unit | Error/override path: constraint beats HDBSCAN |
| S3a: faces/identity | test_cluster.py | test_labels_and_constraints_should_survive_when_pipeline_db_deleted_and_cluster_pass_rerun | Integration | `state.db` read-only from ML script; labels re-attach by `FaceId` |
| S3a: faces/identity | test_identity.py | test_identity_should_abstain_below_threshold_when_similarity_052_and_threshold_06 | Unit | Strict threshold |
| S3a: faces/identity | test_identity.py | test_identity_should_cap_confidence_at_04_and_skip_guards_when_top2_ambiguous | Unit | Error path: siblings not auto-assigned |
| S3a: faces/identity | test_people.py | test_people_add_should_reject_future_birth_with_example_when_born_2031 | Unit | Error path (UX S1) |
| S3a: faces/identity | test_ml_boundary.py | test_analyze_ml_should_write_one_noop_row_per_file_and_open_state_db_read_only_when_run_on_seeded_store | Integration | Real subprocess via `ML_CMD`; write attempt on `state.db` raises |
| S3a: faces/identity | test_faces_model_switch.py | test_faces_plugin_should_store_128d_sface_embeddings_and_leave_buffalo_rows_when_model_switched | Unit | License-clean fallback (Story 4.7) |
| S3a: faces/identity | test_faces_model_switch.py | test_cluster_should_cluster_per_model_id_and_warn_when_mixed_embeddings | Unit | Error path: dimension mismatch |
| S3b: age | test_age.py | test_age_plugin_should_grayscale_equalize_and_emit_sigma_with_weight_cap_03_when_uncalibrated | Unit | Happy path |
| S3b: age | test_age.py | test_age_plugin_should_abstain_face_too_small_when_face_under_60px | Unit | Error path |
| S3b: age | test_age_to_date.py | test_age_to_date_should_center_1985_interval_1983_to_1987_when_born_1980_age_5_sigma_2 | Unit | Happy path |
| S3b: age | test_age_to_date.py | test_age_to_date_should_drop_vote_implausible_age_when_implied_age_over_100_or_negative | Unit | Error path |
| S3b: age | test_age_to_date.py | test_age_to_date_should_route_review_group_age_disagreement_when_child_and_adult_years_differ_beyond_sigmas | Unit | Group photo uses smallest sigma |
| S3b: age | test_age_to_date.py | test_fuse_should_stay_below_08_and_route_review_when_adult_age_45_sigma_10_alone | Integration | Real `fuse_service` over stored age evidence |
| S3c: calibration | test_anchors.py | test_anchors_build_should_admit_only_20_genuine_and_print_excluded_counts_when_30_placeholder_and_suspect_present | Unit | Happy path; also see X1 |
| S3c: calibration | test_anchors.py | test_holdout_should_select_same_six_of_30_when_insertion_order_changes | Unit | Deterministic hold-out |
| S3c: calibration | test_calibration.py | test_calibration_should_fit_sigma_within_15_percent_of_4_when_40_anchors_with_known_error | Unit | Golden |
| S3c: calibration | test_calibration.py | test_calibration_should_cap_weight_02_and_print_uncalibrated_n3_when_bucket_has_3_anchors | Unit | Error/sparse path |
| S3c: calibration | test_calibration.py | test_calibration_should_report_heldout_metrics_without_using_them_to_fit_when_holdout_present | Unit | Leak guard |
| S3c: calibration | test_anchors.py | test_anchor_pins_should_survive_pipeline_db_deletion_when_pin_album_run | Integration | `state.db` `anchor_pins` + `s0502` migration |
| S3d: era | test_print_cues.py | test_print_cues_should_emit_era_interval_confidence_at_most_025_when_deckle_border_and_sepia_cast | Unit | Happy path |
| S3d: era | test_print_cues.py | test_print_cues_should_make_no_capture_date_claim_when_software_is_vuescan | Unit | Error path: scanner EXIF = scan date only |
| S3d: era | test_print_cues.py | test_dup_group_should_propagate_anchor_interval_at_weight_05_when_rotated_and_cropped_duplicate | Integration | Real dHash on generated images; propagation is ordinary evidence |
| S3d: era | test_era_regress.py | test_era_regress_should_beat_label_mean_baseline_mae_and_exclude_holdout_when_trained_on_two_gaussians | Unit | Happy path |
| S3d: era | test_era_regress.py | test_era_regress_should_cap_weight_025_and_group_appearance_when_prediction_emitted | Unit | Low-weight tiebreaker |
| S3d: era | test_cloud_vision.py | test_cloud_vision_should_make_zero_http_requests_when_allow_cloud_absent | Unit | Error path (also C1/RC2) |
| S3d: era | test_cloud_vision.py | test_cloud_vision_should_make_exactly_50_calls_and_log_each_when_sample_cap_50_spend_cap_1 | Integration | Fake HTTP client; `cloud-send.jsonl` rows with `ContentKey`, bytes, model |
| S3d: era | test_era_embed.py | test_era_embed_should_report_5_cached_when_run_twice_on_5_images | Integration | Stub encoder, real store |
| S3e: fusion | test_fusion_guards.py | test_birth_death_bounds_should_prune_to_19720304_through_1975_when_person_born_1972 | Unit | Golden |
| S3e: fusion | test_fusion_guards.py | test_fuse_should_return_conflict_empty_interval_when_birth_1972_and_folder_1950_to_1960 | Unit | Error path |
| S3e: fusion | test_fusion_guards.py | test_upload_window_ceiling_should_prune_dates_at_or_after_window_start_when_no_anchor_in_window | Unit | Pre-1995 scan cannot resolve to upload window (SM1) |
| S3e: fusion | test_fusion_scoring.py | test_scoring_should_cap_combined_weight_at_15_when_two_correlated_faces_votes | Unit | Dependence discount |
| S3e: fusion | test_fusion_scoring.py | test_scoring_should_equal_base_byte_for_byte_when_abstention_added | Unit | Property: monotonicity |
| S3e: fusion | test_fusion_scoring.py | test_fuse_should_return_review_when_only_one_independent_voter_group | Unit | Error path: `min_independent_voters=2` |
| S3e: fusion | test_fuse_service.py | test_fuse_should_write_10_decisions_and_print_status_histogram_when_10_files_have_evidence | Integration | Real SQLite |
| S3e: fusion | test_fuse_service.py | test_fuse_should_leave_conflict_and_write_state_unchanged_when_rerun_with_min_confidence_zero | Integration | Conflict never Eligible; `WriteState` is a journal join |
| S3e: fusion | test_fuse_service.py | test_fuse_should_rebuild_user_override_from_decisions_jsonl_when_pipeline_db_deleted | Integration | Owner input survives derived-store loss |
| S3e: fusion | test_plugin_folder_year.py | test_folder_year_should_emit_interval_without_point_when_folder_is_1985_1990 | Unit | Happy path |
| S3e: fusion | test_plugin_folder_year.py | test_folder_year_should_abstain_no_year_in_folder_when_misc_scans | Unit | Error path |
| S3e: fusion | test_plugin_filename_date.py | test_filename_date_should_emit_anchor_candidate_confidence_09_when_camera_name | Unit | Happy path |
| S3e: fusion | test_plugin_filename_date.py | test_fuse_should_return_conflict_routed_to_review_when_filename_2019_in_folder_1995 | Integration | Real `fuse_service` |
| S3e: fusion | test_dateparse.py | test_parse_filename_date_should_return_none_for_20230231_and_non_capture_prefixes_when_invalid | Unit | Error path |
| S3e: fusion | test_dateparse.py | test_partial_date_should_raise_value_error_when_day_precision_has_multi_year_interval | Unit | Illegal state unconstructible |
| S3e: fusion | test_dateparse.py | test_parse_folder_date_should_match_golden_json_when_run_over_every_golden_case | Unit | `golden/dateparse.json` |
| S3e: fusion | test_plugin_exif_anchor.py | test_exif_anchor_should_emit_098_anchor_candidate_when_genuine_canon_date | Unit | Happy path |
| S3e: fusion | test_plugin_exif_anchor.py | test_exif_anchor_should_emit_no_anchor_candidate_when_make_canon_but_class_suspect_or_legacy | Unit | Error path: Make does not rescue |
| S3e: fusion | test_plugin_date_stamp.py | test_date_stamp_should_abstain_suspect_reset_clock_when_stamp_reads_1_1_00 | Unit | OCR error path |
| S3e: fusion | test_plugin_date_stamp.py | test_date_stamp_should_read_19960314_confidence_07_when_orange_96_3_14_crop | Unit | Happy path |
| S4: review + write | test_decisions.py | test_decisions_fold_should_resolve_c12_to_reject_when_accept_then_reject_logged | Unit | Latest wins |
| S4: review + write | test_decisions.py | test_decisions_load_should_skip_torn_tail_and_keep_prefix_when_last_line_truncated | Unit | Error path |
| S4: review + write | test_review.py | test_review_set_should_store_user_override_confidence_1_and_fuse_as_user_override_when_date_1976_06 | Integration | Real store + fuse |
| S4: review + write | test_review.py | test_review_set_should_refuse_pre_birth_date_with_force_guard_hint_when_person_born_1980 | Unit | Error path |
| S4: review + write | test_review.py | test_review_undo_last_should_restore_accept_when_accept_then_reject_42 | Unit | Retraction primitive |
| S4: review + write | test_review_import.py | test_import_should_append_11_skip_1_duplicate_and_reject_unknown_c999_when_12_entries | Unit | Dry-run first, `--apply` required |
| S4: review + write | test_plan_apply.py | test_plan_should_contain_only_f1_and_list_f5_as_review_when_decisions_mixed | Unit | F5 = anchor with LegacyPlaceholder EXIF |
| S4: review + write | test_plan_apply.py | test_apply_should_write_only_gpo_year_keyword_when_year_precision_without_allow_flag | Unit | `YearPrecisionPolicy` rules 1-2 |
| S4: review + write | test_plan_apply.py | test_apply_should_write_july_1_noon_with_inferred_marker_when_allow_year_precision_for_album | Integration | Real exiftool; rule 3, `-P`, no `-overwrite_original` |
| S4: review + write | test_plan_apply.py | test_apply_should_refuse_in_place_write_on_exfat_without_workdir_when_mountinfo_says_exfat | Unit | Error path; no bypass flag |
| S4: review + write | test_plan_apply.py | test_apply_should_copy_write_verify_hash_then_rename_when_workdir_given | Integration | Fake mountinfo + real exiftool |
| S4: review + write | test_write_planner.py | test_plan_writes_should_match_characterization_golden_when_20_fixture_tuples | Unit | Refactor safety (8.1) |
| S4: review + write | test_write_planner.py | test_generate_tags_should_not_emit_chris_when_filename_is_christmas_1994 | Unit | Error path (word boundary) |
| S4: review + write | test_exif_reader.py | test_read_snapshots_should_match_exiftool_json_when_real_jpeg_read | Integration | Real exiftool 13.55 |
| S4: review + write | test_exif_reader.py | test_read_snapshots_should_use_at_most_ceil_50_over_chunk_processes_when_50_files | Unit | Batching |
| S5: audit + remediation | test_audit.py | test_audit_rclone_should_store_100_observed_rows_and_print_coverage_line_when_fake_lsjson_100_items | Integration | Fake rclone |
| S5: audit + remediation | test_audit.py | test_audit_should_print_setup_rclone_hint_and_change_nothing_when_token_expired | Integration | Error path |
| S5: audit + remediation | test_audit.py | test_audit_should_print_metric1_unmeasured_and_exit_0_when_modtime_not_exif_date | Integration | 9.1 fallback |
| S5: audit + remediation | test_takeout.py | test_takeout_parse_should_return_2016_11_24T15_06_40Z_when_photoTakenTime_1480000000 | Unit | Happy path |
| S5: audit + remediation | test_takeout.py | test_takeout_parse_should_pair_img_1_1_jpg_with_img_1_jpg_1_json_when_duplicate_name | Unit | Naming quirk |
| S5: audit + remediation | test_takeout.py | test_takeout_parse_should_stream_with_bounded_memory_and_count_unmatched_when_10000_sidecars | Integration | tracemalloc bound |
| S5: audit + remediation | test_audit_join.py | test_join_should_flag_item_not_cleared_by_decision_match_when_decision_built_from_legacy_placeholder | Unit | Error path |
| S5: audit + remediation | test_audit_join.py | test_audit_runs_should_feed_audit_clear_and_remediation_done_only_cleared_by_later_audit_when_audit_finishes | Integration | Real SQLite |
| S5: audit + remediation | test_remediation_webui.py | test_webui_plan_should_write_grouped_worklist_md_with_search_hint_and_zero_network_calls_when_12_items | Unit | Happy path |
| S5: audit + remediation | test_remediation_webui.py | test_remediation_done_should_print_no_worklist_item_x_when_unknown_item | Unit | Error path |
| S5: audit + remediation | test_remediation_trash.py | test_trash_reupload_should_block_with_n_remote_copies_when_audit_still_lists_old_items | Integration | Gate on audit, not self-report |
| S5: audit + remediation | test_remediation_trash.py | test_trash_reupload_should_refuse_bytes_unchanged_when_file_not_corrected | Unit | Dedup caveat |
| S5: audit + remediation | test_remediation_trash.py | test_trash_reupload_should_set_generation_2_and_pass_gate_when_zero_surviving_copies_and_all_verified | Integration | Fake rclone |
| S5: audit + remediation | test_remediation_gptk.py | test_unofficial_strategy_should_exit_with_tos_warning_when_risk_flag_absent | Unit | Opt-in guard |
| S5: audit + remediation | test_remediation_gptk.py | test_unofficial_strategy_should_write_filter_file_and_not_execute_toolkit_when_flag_given | Unit | Never executes |
| S6: truthful status | test_status_migration.py | test_loader_should_map_fixed_to_written_and_manifest_album_to_uploaded_unverified_when_legacy_json | Unit | Happy path |
| S6: truthful status | test_status_migration.py | test_scan_should_keep_written_status_when_rescan_over_same_drive | Integration | Root cause of all-pending (7a) |
| S6: truthful status | test_derived_status.py | test_album_status_should_be_mismatch_when_9_verified_and_1_mismatch_rows | Unit | Derived from journal |
| S6: truthful status | test_derived_status.py | test_no_assignment_to_metadata_status_should_remain_outside_derived_view_when_grepped | Unit | Static guard (`grep -rn 'metadata_status = '`) |
| S6: truthful status | test_derived_status.py | test_write_state_should_return_reverted_when_rows_pending_verified_reverted | Integration | Real `state.db` join |
| S6: truthful status | test_smoke.py | test_runner_should_exit_nonzero_and_print_ok_lines_when_one_test_fails | Integration | `make gphotos-test` against a temp failing copy (plain-function style itself) |
| SM1: no pre-anchor-date in upload window | test_fusion_guards.py | test_decisions_should_have_zero_pre_1995_scans_in_upload_window_when_ceiling_guard_active | Unit | Decisions-side line printed by `report accuracy` (5.5) |
| SM1: no pre-anchor-date in upload window | test_audit.py | test_audit_should_count_remote_items_dated_like_legacy_placeholder_even_when_outside_upload_window | Unit | Jan 1 / `12:00:00+5k` remote dates; third item not tagged |
| SM1: no pre-anchor-date in upload window | test_audit_join.py | test_audit_should_print_suspicious_placeholder_and_outside_interval_counts_when_join_flags_items | Integration | Output line exact format |
| SM2: held-out error | test_accuracy_report.py | test_report_accuracy_should_print_median_p90_by_decade_color_and_age_band_with_provisional_label_when_10_holdout_anchors_and_no_targets_set | Unit | Targets child +/-2, adult +/-8 are provisional until `[targets]` is set |
| SM2: held-out error | test_accuracy_report.py | test_report_accuracy_should_print_uncalibrated_not_pass_when_bucket_n_below_10 | Unit | Error path |
| SM2: held-out error | test_accuracy_report.py | test_report_accuracy_should_render_holdout_mae_rows_from_run_metrics_when_era_regress_ran | Integration | Reads real `run_metrics` |
| SM1: numeric bound | test_audit_join.py | test_metric1_line_should_count_bounded_violations_unbounded_and_unobservable_and_store_baseline_when_audit_ends | Unit | B = decision `latest`, else folder/filename `latest`; remote date > B + 1 year is a violation; no B counts as unbounded |
| SM1: numeric bound | test_audit_join.py | test_metric1_should_never_print_clean_for_unobservable_album_or_unbounded_item_when_zero_violations | Unit | Error path |
| SM2: baseline first | test_accuracy_report.py | test_report_accuracy_should_print_baseline_recorded_and_exit_0_when_targets_table_absent | Unit | Then pass/fail against `[targets]` when set |
| SM5: remediation counts | test_remediation_webui.py | test_remediation_waive_should_record_reason_and_count_waived_not_fixed_when_item_still_wrong_in_later_audit | Unit | fixed / waived / open |
| SM5: remediation counts | test_run_report.py | test_report_should_print_remediation_fixed_waived_open_and_waived_share_when_fixture_audit_items | Integration | Real stores |
| SM6: review burden | test_run_report.py | test_report_should_print_review_burden_open_by_source_decided_by_action_and_auto_dated_share_when_fixture | Integration | Group decisions counted per file; no pass/fail before targets |
| S4: cluster-sheet semantics | test_review_import.py | test_import_should_apply_cluster_accept_with_name_face_reject_as_cannot_link_and_face_accept_as_exemplar_when_cluster_sheet_export | Integration | Blocker fix; `gpo-decisions/2` |
| S4: cluster-sheet semantics | test_people.py | test_cluster_accept_after_face_reject_should_label_remaining_members_and_print_count_when_c12_f3_rejected | Integration | `Labeling 59 faces (1 rejected).` |
| S4: cluster-sheet semantics | test_review_import.py | test_import_should_ignore_every_cluster_label_and_face_member_entry_and_say_regenerate_when_cluster_run_id_differs | Unit | Error path; plan 7.4 and ux S5 now agree (all cluster entries, not only face entries) |
| S4: cluster-sheet semantics | test_review_import.py | test_import_should_refuse_cluster_accept_without_name_or_with_unknown_name_and_apply_others_when_mixed | Unit | Error path; did-you-mean |
| S4: per-source verbs | test_review.py | test_next_line_should_list_only_verbs_of_the_items_source_and_refuse_undefined_verb_when_each_of_seven_sources | Unit | UX-97 |
| S4: per-source verbs | test_review.py | test_placeholder_reject_should_append_genuine_owner_record_and_accept_legacy_record_when_aliases_used | Integration | Writes through to `placeholders.jsonl` |
| S4: review at scale | test_review.py | test_review_next_and_list_should_filter_by_source_album_severity_and_order_by_gain_when_flags_given | Unit | UX-70 |
| S4: review at scale | test_review.py | test_review_next_open_should_call_opener_with_sheet_anchor_and_print_file_url_when_gphotos_open_fake | Unit | UX-71 |
| S4: review at scale | test_review_groups.py | test_group_confirm_genuine_should_preview_refuse_apply_unviewed_over_50_and_retract_in_one_step_when_412_files | Integration | UX-73; `retract_group` |
| S4: review at scale | test_review_groups.py | test_placeholder_sheet_should_scale_sample_with_group_size_stratify_by_exif_timestamp_and_show_histogram_when_412_and_9161_files | Unit | UX-74, UX-103; 82 and 200 cards, same seed same cards |
| S4: review at scale | test_review_groups.py | test_group_decision_should_scale_to_15000_records_within_bounded_output_when_synthetic_pool | Unit | NF2 |
| S4: sheet pages | test_sheet_pages.py | test_album_sheet_should_cap_100_cards_page_nav_and_only_page_thumbnails_when_9161_files | Integration | UX-75 |
| S4: sheet pages | test_sheet_pages.py | test_cluster_index_should_list_all_clusters_with_status_and_gain_and_links_should_resolve_when_212_clusters | Unit | UX-72 |
| S4: sheet pages | test_sheet_pages.py | test_cluster_sheet_page_2_should_hold_next_24_faces_without_repeats_when_show_more | Unit | UX-76 |
| S4: sheet state | test_ux_sheet.py | test_localstorage_key_should_include_generation_hash_and_offer_old_decisions_when_sheet_regenerated | Playwright (file://) | UX-80 |
| S4: sheet state | test_ux_sheet.py | test_same_key_twice_should_toggle_to_undecided_u_should_undo_and_clear_all_should_confirm_when_pressed | Playwright (file://) | UX-81 |
| S4: sheet state | test_ux_sheet.py | test_cards_in_log_should_show_badge_and_export_should_mark_exported_when_sheet_opened | Playwright (file://) | UX-82 |
| S4: sheet state | test_ux_sheet.py | test_storage_throwing_should_show_banner_keep_memory_decision_and_export_when_quota_error | Playwright (file://) | UX-83 |
| S4: WCAG additions | test_ux_sheet.py | test_shortcuts_should_act_only_with_card_focus_and_checkbox_should_disable_them_when_body_focused | Playwright (file://) | UX-84 (WCAG 2.1.4) |
| S4: WCAG additions | test_ux_sheet.py | test_focus_should_stay_on_decided_control_and_arrow_keys_should_move_to_neighbour_card_without_wrapping_and_no_card_control_should_have_tabindex_minus_one_when_decisions_made | Playwright (file://) | UX-85 |
| S4: WCAG additions | test_ux_sheet.py | test_live_counter_should_announce_every_fifth_change_and_at_zero_when_ten_decisions | Playwright (file://) | UX-86 |
| S4: WCAG additions | test_ux_sheet.py | test_enlarge_dialog_should_open_with_1024_image_close_on_esc_and_return_focus_when_e_pressed | Playwright (file://) | UX-87 |
| S4: WCAG additions | test_ux_sheet.py | test_sheet_should_reflow_to_one_column_at_320px_and_never_cover_focused_card_with_header_when_tabbing | Playwright (file://) | UX-88 (WCAG 1.4.10, 2.4.11) |
| S4: WCAG additions | test_report_html.py | test_contrast_test_should_cover_focus_ring_state_icons_badges_and_dialog_in_both_themes_when_computed | Static HTML | UX-89 |
| S4: names and clusters | test_people.py | test_name_resolution_should_match_case_insensitive_and_alias_refuse_near_miss_with_did_you_mean_and_create_only_with_new_person_when_accept | Unit | UX-77 |
| S4: names and clusters | test_people.py | test_merge_should_print_pending_count_and_cluster_pass_cost_and_list_clusters_should_show_pending_when_intent_recorded | Unit | UX-78 |
| S4: usability | test_review_proto.py | test_fixture_should_generate_20_clusters_50_items_3_placeholder_albums_and_prototype_should_use_real_decisions_log_when_run | Integration | Story 7.5; the timed pass itself is a manual item |
| RC1: confirmation tiers | test_confirm.py | test_confirm_should_reject_empty_and_wrong_token_never_print_token_in_prompt_and_accept_yes_only_without_tty_when_t2 | Unit | UX-90 |
| RC1: confirmation tiers | test_confirm.py | test_confirm_t3_should_check_precondition_before_prompting_when_run_not_verified | Unit | `prewrite purge`, `undo --force`, `deny release` |
| RC1: confirmation tiers | test_plan_apply.py | test_apply_should_ask_for_file_count_not_plan_id_and_print_undo_command_in_summary_when_tty | Scripted CLI | Replaces the plan-id token (UX-11) |
| RC1: confirmation tiers | test_upload_gate_v1.py | test_upload_apply_should_ask_for_album_count_after_gate_lines_and_exclude_blocked_albums_when_21_uploadable | Scripted CLI | T2 |
| RC1: confirmation tiers | test_drive_backup.py | test_prewrite_purge_should_require_verified_run_and_typed_file_count_when_run_id_on_command_line | Unit | T3 |
| RC1: confirmation tiers | test_confirm.py | test_confirm_t3_should_refuse_album_id_and_accept_only_file_count_not_in_argv_when_deny_release_and_i_verified_trash | Unit | UX-98; a token equal to an argv element falls back to the next candidate count, and if all collide the command refuses cleanly (no raise) |
| RC1: confirmation tiers | test_drive_backup.py | test_backup_fsck_should_use_direct_then_sudo_on_tty_then_from_output_route_and_never_store_a_password_when_device_unreadable | Unit | UX-112; fake `fsck.exfat` and fake `sudo` |
| S4: export schema | test_review_import.py | test_import_should_keep_two_placeholder_groups_with_same_action_and_report_conflict_only_when_terminal_ts_after_decided_at | Unit | UX-99; `group_id`, `decided_at` |
| S4: export schema | test_review_import.py | test_import_should_validate_set_values_like_review_set_and_reject_each_refused_value_individually_when_future_today_birth_or_bad_format | Unit | UX-106 |
| S4: export schema | test_review_import.py | test_import_latest_and_glob_should_pick_newest_decisions_files_and_apply_should_regenerate_index_when_downloads_dir_has_212_exports | Integration | UX-105 |
| S4: cluster run guard | test_people.py | test_cluster_commands_should_refuse_stale_run_with_renumbering_message_and_echo_signature_without_run_when_cr7_vs_cr9 | Unit | UX-100; terminal and no-JS card commands |
| S4: fold order | test_people.py | test_face_reject_after_cluster_accept_should_remove_label_and_reject_of_accepted_cluster_should_preview_then_apply_when_c12 | Integration | UX-101 |
| S4: merge and split | test_people.py | test_split_should_append_two_face_rejects_under_one_batch_and_merge_one_cluster_link_and_one_undo_should_retract_both_when_c12_c40 | Unit | UX-101; no `split` action exists |
| S4: undo-last | test_review.py | test_undo_last_should_retract_last_nonretracted_line_or_batch_print_what_it_undoes_and_support_n_list_import_when_called_from_another_shell | Unit | UX-102 |
| S4: group guard | test_review_groups.py | test_confirm_genuine_should_accept_except_ids_leave_them_suspect_and_print_group_line_in_import_dry_run_when_three_exceptions | Integration | UX-103 |
| S4: progress per source | test_review.py | test_review_next_should_count_per_source_never_serve_placeholder_unfiltered_and_resurface_parked_skipped_and_rejected_via_state_when_leftovers | Unit | UX-104 |
| S4: progress per source | test_status_screen.py | test_status_should_print_per_source_review_rows_placeholder_row_and_follow_the_eight_rule_next_order_when_analyze_incomplete | Scripted CLI | UX-104, UX-111 |
| S4: sheet open and resume | test_sheet_pages.py | test_open_failure_should_print_file_url_and_exit_0_and_interrupted_all_should_resume_when_no_opener | Unit | UX-105 |
| RC1: confirmation tiers | test_placeholder_revert.py | test_revert_apply_should_ask_for_file_count_and_name_undo_run_and_irrecoverable_originals_when_tty | Scripted CLI | T2 |
| RC1: reversal map | test_labels.py | test_explain_reverse_should_list_ten_rows_each_with_reversing_command_and_limit_when_rendered | Unit | UX-91 |
| UX-62: vocabulary | test_labels.py | test_vocabulary_scan_should_enforce_rules_v1_to_v5_including_lowercase_outcomes_pending_column_and_held_on_review_screens_over_all_golden_screens_with_stale_allowlist_entries_failing_when_scanned | Unit | UX-92; the design's own samples pass (`Ignored`, `Not imported`, `left unchanged`, `attested`) |
| UX-62: vocabulary | test_cli_help.py | test_help_should_show_panels_in_workflow_order_each_command_once_with_status_epilog_when_full_app | Integration | UX-93 |
| UX-62: vocabulary | test_cli_help.py | test_alias_should_warn_on_stderr_only_and_match_stdout_and_exit_code_when_bare_review_severity | Integration | UX-94 |
| UX-62: vocabulary | test_completion.py | test_completion_should_offer_ids_names_albums_runs_without_importing_store_when_tab | Unit | UX-95 |
| Wave integration | test_wave_gate.py | test_wave_gate_should_fail_on_duplicate_command_duplicate_migration_name_and_broken_cli_module_when_fixtures_present | Integration | Story 1.14; pre-mortem 13 |
| Defect trace | test_metadata_accounting.py | test_argfile_should_contain_overwrite_original_once_per_execute_block_when_3_file_chunk | Unit | B4 pinned until 8.4 deletes the flag |
| SM3: confidence + provenance | test_contract.py | test_provenance_should_be_required_on_every_evidence_when_constructing_observation | Unit | Happy/err via TypeError |
| SM3: confidence + provenance | test_fuse_service.py | test_fuse_should_record_voters_and_guards_fired_in_decision_when_decision_stored | Integration | Real SQLite |
| SM3: confidence + provenance | test_plan_apply.py | test_plan_row_should_carry_confidence_and_voters_and_exclude_below_threshold_when_min_confidence_08 | Unit | Threshold gate |
| SM3: confidence + provenance | test_fusion_scoring.py | test_fuse_should_change_status_only_in_06_to_08_band_without_calling_plugins_when_threshold_lowered | Unit | Pure rerun |
| SM4: plugin without cli edit | test_cli_shell.py | test_cli_help_should_list_toy_and_leave_cli_py_hash_unchanged_when_cli_toy_py_added | Integration | Auto-discovery |
| SM4: plugin without cli edit | test_cli_shell.py | test_cli_help_should_warn_skipped_broken_module_and_exit_0_when_cli_broken_raises_import_error | Integration | Error path |
| SM4: plugin without cli edit | test_cli_size.py | test_cli_size_should_fail_new_command_over_40_lines_and_baseline_growth_when_measured | Unit | Ratchet |
| SM1: audit flags suspicious (old SM5, folded) | test_audit_join.py | test_join_should_flag_item_when_remote_date_in_upload_window_by_filename_and_size | Unit | Happy path |
| SM1: audit flags suspicious (old SM5, folded) | test_audit_join.py | test_join_should_report_remote_only_and_local_only_unmatched_counts_when_67_remote_only | Unit | Error/edge path |
| SM1: audit flags suspicious (old SM5, folded) | test_audit.py | test_audit_should_store_source_scoped_rows_and_state_coverage_when_rclone_vs_takeout | Integration | Coverage scoped by source |
| C1: privacy | test_registry.py | test_registry_load_should_skip_cloud_vision_with_exact_message_when_allow_cloud_false | Unit | Default deny |
| C1: privacy | test_cloud_vision.py | test_cloud_prompt_should_contain_no_folder_name_or_neighbor_dates_when_rendered | Unit | Image-only prompt |
| C1: privacy | test_privacy.py | test_cloud_send_log_should_contain_contentkey_bytes_model_timestamp_and_no_image_content_when_cloud_run | Integration | |
| C2: platform | test_cli_deps.py | test_cli_pep723_block_should_match_allow_list_and_exclude_ml_packages_when_parsed | Unit | `typer, loguru, rich, pydantic, Pillow, pillow-heif, tomli-w`; no onnxruntime/torch/insightface/scikit-learn/open_clip_torch |
| C2: platform | test_cli_deps.py | test_dependency_parity_should_import_every_pipeline_module_in_both_envs_when_checked | Integration | Real import in both dep sets |
| C2: platform | test_tools.py | test_tools_should_return_env_override_paths_and_system_binaries_when_unset | Unit | `GPHOTOS_EXIFTOOL` / `GPHOTOS_RCLONE` |
| C2: platform | test_ml_boundary.py | test_cli_help_should_not_import_heavy_modules_when_run_with_import_recorder | Integration | Pillow, store, ML libs not imported at `--help` |
| C3: idempotent / dry-run | test_atomic_io.py | test_write_json_atomic_should_keep_old_json_and_leave_no_tmp_when_writer_raises_after_10_bytes | Unit | Crash safety |
| C3: idempotent / dry-run | test_atomic_io.py | test_no_write_text_json_should_remain_in_g_when_grepped | Unit | All six sites swapped |
| C3: idempotent / dry-run | test_indexer.py | test_index_should_print_0_hashed_3_cached_when_rerun_unchanged | Integration | Real files, real store |
| C3: idempotent / dry-run | test_indexer.py | test_index_should_exit_1_with_recover_hint_when_exiftool_tmp_leftover_present | Integration | Error path |
| C3: idempotent / dry-run | test_e2e_smoke.py | test_dry_run_chain_should_leave_fixture_hashes_equal_when_scan_to_upload_dry_run | Integration | |
| C3: idempotent / dry-run | test_leftovers.py | test_find_leftovers_should_return_tmp_and_original_kinds_at_any_depth_when_nested_tree | Unit | |
| C3: idempotent / dry-run | test_leftovers.py | test_recover_quarantine_should_move_never_delete_and_only_list_originals_when_apply | Integration | |
| C4: 2021 deny | test_upload_gate.py | test_upload_should_record_zero_rclone_calls_and_print_blocked_when_album_id_9102dede1a50 | Integration | Fake rclone |
| C4: 2021 deny | test_upload_gate.py | test_upload_album_to_gphotos_should_raise_deny_list_blocked_when_renamed_folder_or_album_name_differs | Unit | Keyed on id AND normalised name AND path |
| C4: 2021 deny | test_upload_gate.py | test_deny_release_should_refuse_with_counts_when_review_or_conflict_remain_and_require_typed_id_when_clear | Unit | |
| C4: 2021 deny | test_upload_gate_v1.py | test_denied_video_in_2021_album_should_still_block_when_only_mp4_remains | Unit | Covers the known `.mp4_exiftool_tmp` file (ties to N3) |
| NF1: performance / cache | test_content_key.py | test_content_key_should_be_equal_while_sha256_differs_when_exif_date_written | Integration | Real exiftool, generated 64x64 JPEG |
| NF1: performance / cache | test_content_key.py | test_content_key_should_pin_sha256_at_first_index_when_format_image_data_md5_unstable | Integration | Per-format spike outcome (2.2a) |
| NF1: performance / cache | test_runner.py | test_runner_should_commit_first_50_rows_and_print_resume_line_when_keyboard_interrupt_at_51 | Unit | Interrupt safety |
| NF1: performance / cache | test_runner.py | test_analyze_should_map_ml_subprocess_crash_to_one_failed_exit_0_and_keep_prior_rows_when_killed_midbatch | Integration | Real subprocess, forced kill |
| NF1: performance / cache | test_spike_outcomes.py | test_time_faces_spike_should_print_images_per_sec_and_extrapolation_for_17145_when_run_on_synthetic_set | Integration | Spike script smoke; real 200-image run is a manual blocker |
| NF2: scalability | test_store.py | test_store_should_wait_busy_timeout_and_retry_when_second_process_holds_write_lock | Integration | Two real processes |
| NF2: scalability | test_runner.py | test_analyze_should_exit_1_naming_pid_when_analyze_lock_held | Integration | `flock` |
| NF2: scalability | test_takeout.py | test_takeout_parse_should_complete_17000_sidecars_within_bounded_memory_when_large_export | Integration | Scale check |
| NF2: scalability | test_placeholder_detector.py | test_classify_folder_should_handle_15000_files_within_10_seconds_when_synthetic_corpus | Unit | Ladder detection is per folder, not quadratic |
| NF3: security | test_datadir.py | test_datadir_should_create_mode_700_dir_and_600_files_when_resolved | Unit | |
| NF3: security | test_face_store.py | test_data_dir_files_should_all_be_mode_600_or_700_when_faces_run_completed | Integration | |
| NF3: security | test_people.py | test_logs_should_contain_zero_matches_for_person_name_when_labels_created | Integration | Names out of logs |
| NF3: security | test_people.py | test_people_edit_should_reject_death_before_birth_and_keep_bak_when_edit | Unit | Error path |
| NF4: data residency | test_privacy.py | test_git_check_ignore_should_ignore_db_thumbs_review_and_data_dir_outside_repo_when_default_resolved | Integration | Real `git check-ignore` |
| NF4: data residency | test_privacy.py | test_no_names_in_repo_should_pass_or_skip_when_people_toml_absent | Unit | Reports `skipped: no people.toml` |
| NF4: data residency | test_report_html.py | test_sheet_output_path_should_be_under_data_dir_not_repo_when_resolved | Unit | |
| OB1: observability | test_metrics.py | test_log_lines_should_carry_run_id_and_stage_and_content_key_on_error_when_any_command_runs | Integration | `DATA/logs/run-<id>.jsonl` |
| OB1: observability | test_metrics.py | test_run_metrics_should_sum_plugin_files_total_to_10_per_plugin_when_analyze_10_files | Integration | |
| OB1: observability | test_run_report.py | test_run_report_should_contain_all_seven_sections_when_run_on_fixture_corpus | Integration | |
| OB1: observability | test_run_report.py | test_run_report_should_render_person_3_not_name_unless_show_names_when_default | Unit | Redaction |
| OB1: observability | test_run_report.py | test_legacy_album_report_should_match_pre_change_golden_when_generate_markdown_report | Unit | Additive only |
| OB1: observability | test_quota.py | test_run_report_should_list_quota_events_when_429_occurred | Integration | |
| RC1: dry-run + journal + reversible | test_journal.py | test_apply_should_hold_pending_row_with_old_values_and_sha256_in_state_db_and_jsonl_when_exiftool_killed | Integration | Journal before write |
| RC1: dry-run + journal + reversible | test_journal.py | test_journal_should_mark_mismatch_and_halt_album_when_exiftool_silently_ignores_write | Integration | Error path |
| RC1: dry-run + journal + reversible | test_journal.py | test_undo_list_should_reproduce_reversions_from_jsonl_alone_when_state_db_replaced_by_empty_file | Integration | |
| RC1: dry-run + journal + reversible | test_journal.py | test_backup_state_should_copy_openable_db_with_same_rows_when_called | Integration | |
| RC1: dry-run + journal + reversible | test_undo.py | test_undo_should_restore_old_value_and_delete_absent_tags_when_run_applied | Integration | Real exiftool |
| RC1: dry-run + journal + reversible | test_undo.py | test_undo_should_skip_modified_after_run_unless_force_when_hash_differs | Integration | Error path |
| RC1: dry-run + journal + reversible | test_undo.py | test_undo_should_change_nothing_when_run_without_apply | Unit | Dry-run default |
| RC1: dry-run + journal + reversible | test_cli_shell.py | test_fix_metadata_apply_should_exit_1_legacy_writer_disabled_and_record_zero_exiftool_calls_when_run_before_plan_apply | Integration | Story 1.11 lock |
| RC1: dry-run + journal + reversible | test_plan_apply.py | test_no_overwrite_original_should_remain_in_g_when_grepped | Unit | Static guard after 8.4 |
| RC1: dry-run + journal + reversible | test_e2e_smoke.py | test_apply_then_undo_should_restore_prewrite_tag_snapshot_when_corpus_run | Integration | |
| RC2: per-plugin flags / cloud flag | test_registry.py | test_registry_should_honor_config_toml_enabled_false_for_ml_and_cloud_plugins_when_loaded | Unit | |
| RC2: per-plugin flags / cloud flag | test_ml_boundary.py | test_models_fetch_should_disable_only_that_plugin_and_exit_1_when_offline | Integration | Error path (UX-25) |
| RC2: per-plugin flags / cloud flag | test_cloud_vision.py | test_cloud_vision_should_not_even_import_module_when_allow_cloud_false | Unit | |
| RC3: threshold gate | test_plan_apply.py | test_plan_should_exclude_conflict_and_below_threshold_rows_when_min_confidence_08 | Unit | |
| RC3: threshold gate | test_fuse_service.py | test_conflict_should_remain_conflict_when_min_confidence_zero | Unit | Error path |
| RC4: upload only after audit | test_upload_gate_v1.py | test_gate_should_block_no_audit_covers_album_when_no_audit_newer_than_last_write | Unit | |
| RC4: upload only after audit | test_upload_gate_v1.py | test_gate_should_block_with_suspicious_count_and_allow_unaudited_should_warn_loudly_when_audit_lists_items | Integration | Real `audit_runs` |
| RC4: upload only after audit | test_upload_gate_v1.py | test_gate_should_block_one_of_forty_unresolved_and_year_only_files_when_review_status_present | Unit | |
| RC4: upload only after audit | test_upload_gate_v1.py | test_manifest_entry_should_hold_timestamp_rclone_counts_and_uploaded_unverified_when_upload_succeeds | Integration | Fake rclone |
| RC4: upload only after audit | test_upload_gate_v1.py | test_legacy_604_entries_should_load_uploaded_unverified_and_never_reupload_when_manifest_read | Unit | Grandfathering |
| BL1: placeholder fallback removed | test_placeholder_gate.py | test_fix_metadata_dry_run_should_make_zero_exiftool_calls_and_report_skipped_placeholder_9161_when_year_album | Integration | |
| BL1: placeholder fallback removed | test_placeholder_gate.py | test_allow_placeholder_should_list_warning_and_write_nothing_when_dry_run | Unit | Error/override path |
| BL1: placeholder fallback removed | test_placeholder_gate.py | test_scanner_and_ai_enrich_should_emit_year_precision_and_no_01_01_point_when_folder_1987 | Unit | |
| BL1: placeholder fallback removed | test_media_types.py | test_classify_should_return_dateable_image_for_webp_and_uploadable_only_for_3gp_when_called | Unit | |
| BL1: placeholder fallback removed | test_enrich_parity.py | test_enrich_mapping_data_should_equal_enrich_parity_golden_when_run_on_30_albums | Unit | Legacy pinned until removal |
| BL1: placeholder fallback removed | test_enrich_parity.py | test_ai_enrich_enrich_mapping_data_and_infer_cmd_should_not_be_importable_when_task_10_5c_done | Unit | Adapter removed; fails if still imported |
| BL1: placeholder fallback removed | test_plugin_event.py | test_event_plugin_should_return_month_interval_with_rule_id_and_abstain_on_year_only_when_christmas_1994_and_1987 | Unit | Intentional-diff golden `event_plugin.json` |
| BL2: quota seam | test_quota.py | test_upload_with_quota_retry_should_sleep_injected_reset_and_write_manifest_once_when_429_then_ok | Unit | |
| BL2: quota seam | test_quota.py | test_upload_with_quota_retry_should_return_failure_not_exception_when_always_429_max_waits_3 | Unit | Error path |
| BL2: quota seam | test_quota.py | test_upload_should_resume_and_leave_manifest_consistent_when_ctrl_c_during_wait | Integration | Fake rclone, signal injection |
| BL3: API capability | test_spike_outcomes.py | test_gphotos_spike_script_should_redact_secrets_and_write_evidence_file_when_run_against_fake_rclone | Integration | Scripted check of the spike harness only |
| BL3: API capability | test_audit.py | test_audit_should_select_takeout_fallback_message_when_spike_marks_rclone_dates_untrusted | Unit | Ties 9.1 outcome to behavior |
| BL3: API capability | test_remediation_trash.py | test_strategy_selection_should_print_fallback_to_webui_never_silent_when_trash_reupload_lacks_verified_plan | Unit | Error path |
| X1: legacy placeholders | test_placeholder_detector.py | test_classify_should_match_all_golden_truth_table_rows_when_run_over_placeholder_detector_json | Unit | All 5 rules |
| X1: legacy placeholders | test_placeholder_detector.py | test_time_signature_should_match_120340_not_120341_not_130000_when_boundary | Unit | Boundary |
| X1: legacy placeholders | test_placeholder_detector.py | test_anchor_eligible_should_be_true_only_for_genuine_when_called_for_each_class | Unit | |
| X1: legacy placeholders | test_placeholder_detector.py | test_confirm_genuine_should_require_typed_date_for_legacy_and_exit_1_on_mismatch_when_yes_flag_only | Unit | Error path |
| X1: legacy placeholders | test_placeholder_detector.py | test_placeholders_scan_should_write_report_with_cross_tab_and_leave_fixture_hashes_equal_when_run | Integration | Real exiftool on fixtures |
| X1: legacy placeholders | test_placeholder_revert.py | test_revert_apply_should_write_exactly_two_legacy_files_and_list_two_suspect_in_review_when_mixed_fixture | Integration | Quarantine default; 6-file fixture |
| X1: legacy placeholders | test_placeholder_revert.py | test_revert_should_make_undo_restore_placeholder_values_when_applied_with_workdir | Integration | Journaled + reversible |
| X1: legacy placeholders | test_e2e_smoke.py | test_legacy_placeholder_groups_should_never_be_anchor_or_planned_and_block_upload_when_fixture_chain_run | Integration | 10.5 end-to-end |
| N1: re-validate at apply | test_placeholder_revert.py | test_n1_revert_apply_should_skip_and_report_reclassified_when_file_added_to_folder_breaks_ladder_after_dry_run | Integration | Dry-run lists file; add a non-ladder file so run <3; apply skips, reports `reclassified: Suspect` |
| N1: re-validate at apply | test_placeholder_revert.py | test_n1_revert_apply_should_skip_file_when_on_disk_value_changed_since_dry_run | Integration | Safe-original check (value mismatch) |
| N1: re-validate at apply | test_placeholder_revert.py | test_n1_revert_apply_should_honor_confirm_genuine_recorded_between_dry_run_and_apply_when_owner_confirms | Integration | Latest `placeholders.jsonl` wins at apply |
| N1: re-validate at apply | test_placeholder_revert.py | test_n1_revert_apply_should_skip_when_file_removed_from_folder_shrinks_ladder_below_three | Integration | Removal case, not only addition |
| N1: re-validate at apply | test_placeholder_revert.py | test_n1_revert_apply_should_leave_reclassified_files_byte_identical_and_journal_nothing_for_them_when_run | Integration | Hash before = after; no `write_journal` rows for skipped files |
| N1: re-validate at apply | test_placeholder_revert.py | test_n1_revert_apply_should_exit_1_and_change_nothing_when_snapshot_older_than_classification_version | Unit | Error path: stale selection file refused with `Regenerate:` hint |
| N2: per-album apply/summaries | test_placeholder_revert.py | test_n2_placeholders_summary_should_group_by_album_with_count_signals_and_five_sample_files_when_15000_rows | Unit | Synthetic 15,000-record pool; output line count bounded by albums x (header + 5) |
| N2: per-album apply/summaries | test_placeholder_revert.py | test_n2_revert_album_apply_should_write_only_that_albums_legacy_files_under_one_run_id_when_album_flag | Integration | Other albums byte-identical |
| N2: per-album apply/summaries | test_placeholder_revert.py | test_n2_revert_album_dry_run_should_end_with_exact_album_apply_command_when_no_apply | Unit | UX-10 / UX-29 |
| N2: per-album apply/summaries | test_placeholder_revert.py | test_n2_revert_should_require_include_weak_for_rule2_with_make_when_album_name_has_no_matching_date | Unit | Weak class excluded by default |
| N2: per-album apply/summaries | test_placeholder_revert.py | test_n2_revert_should_require_include_weak_for_uniform_5s_timelapse_shape_over_20_files_when_not_12_00 | Unit | Timelapse false-positive guard |
| N2: per-album apply/summaries | test_placeholder_revert.py | test_n2_undo_run_for_one_album_should_not_touch_other_albums_when_two_album_runs_exist | Integration | Per-album `run_id` isolation |
| N2: per-album apply/summaries | test_placeholder_revert.py | test_n2_revert_album_should_exit_1_unknown_album_with_list_command_when_id_missing | Unit | Error path |
| N3: video coverage | test_placeholder_detector.py | test_n3_scan_report_should_count_videos_as_not_classified_out_of_scope_when_mp4_present | Integration | Documented gap made visible |
| N3: video coverage | test_placeholder_revert.py | test_n3_revert_should_leave_mp4_with_quicktime_12_00_05_createdate_byte_identical_when_apply | Integration | Videos never reverted |
| N3: video coverage | test_plugin_exif_anchor.py | test_n3_exif_anchor_should_not_emit_anchor_for_video_quicktime_createdate_when_classification_unavailable | Unit | Videos never anchors |
| N3: video coverage | test_upload_gate_v1.py | test_n3_video_in_denied_album_should_block_upload_and_video_with_unresolved_decision_should_block_when_gate | Unit | Gate does not exempt video |
| N3: video coverage | test_placeholder_detector.py | test_n3_extension_quicktime_createdate_12_00_sig_should_classify_legacy_placeholder_when_owner_extends_scope | Unit | Flips the four rows above to coverage tests if the owner extends scope |
| N4: ladder sort/tolerance | test_placeholder_detector.py | test_n4_ladder_should_order_by_name_lower_matching_legacy_writer_when_mixed_case_filenames | Unit | `IMG_2.JPG`, `img_1.jpg`, `IMG_3.jpg` form a ladder only under `name.lower()` |
| N4: ladder sort/tolerance | test_placeholder_detector.py | test_n4_ladder_should_not_use_natural_sort_when_a10_sorts_before_a2_in_legacy_order | Unit | Pins the reviewer-proposal conflict to legacy order |
| N4: ladder sort/tolerance | test_placeholder_detector.py | test_n4_ladder_should_tolerate_one_gap_when_file_removed_from_run | Unit | Offsets 0,5,10,(15 missing),20,25 |
| N4: ladder sort/tolerance | test_placeholder_detector.py | test_n4_ladder_should_reject_two_gaps_when_sparse_run | Unit | Bound `max_gaps=1` (error path / false-positive control) |
| N4: ladder sort/tolerance | test_placeholder_detector.py | test_n4_im000014_im000022_fixture_should_classify_legacy_via_a_plus_e_when_later_additions_break_strict_ladder | Unit | The `2000-12-8 Tylers tooth` shape: 12:00:00 and 12:00:05 non-adjacent |
| N4: ladder sort/tolerance | test_placeholder_detector.py | test_n4_ladder_at_non_noon_time_with_make_should_stay_suspect_when_lone_signal_e | Unit | Genuine burst shots not promoted (rule 5) |
| N4: ladder sort/tolerance | test_placeholder_detector.py | test_n4_classification_counts_should_differ_between_case_sensitive_and_lower_sort_on_fixture_and_pin_lower_when_golden | Unit | Reproduces the 14,975 vs 15,004 sensitivity on a small fixture |
| Migration (Step 5) | test_migrations.py | test_migration_should_be_reversible | Migration | Apply all story-named migrations to empty `DATA/`; assert exact table sets per store (`pipeline.db`: `files, evidence, decisions, faces, clusters, uploads_observed, audit_runs, run_metrics, schema_version`; `state.db`: `write_journal, labels, constraints, anchor_pins, schema_version`) and applied-name set; seed `state.db`, journals, `review/decisions.jsonl`; then run the documented rollback (delete `pipeline.db`, restore `album_mapping.json.premigrate`) and assert `state.db`/journals/review log byte-identical, `Store.open()` + `index` rebuild succeed, and the legacy JSON equals its pre-migration bytes |
| Migration (Step 5) | test_migrations.py | test_ml_runtime_should_refuse_start_with_schema_mismatch_message_when_applied_set_differs | Integration | Error path: `Schema mismatch: pipeline.db is missing s0403_faces. Run: gphotos-organizer index (migrates). Nothing was changed.` |

## UX Acceptance Tests

Tools: **Scripted CLI** = Python test driving the Typer app with fake `exiftool`/`rclone` on the fixture corpus, asserting stdout and exit code (`G/tests/test_ux_*.py`, plain functions); **Static HTML** = parse the generated sheet in `G/tests/test_report_html.py`; **Playwright (file://)** = load the generated sheet offline, per the `ui-playwright` skill; **Manual** = human checklist run once per release on the real terminal (listed because the criterion is perceptual).

| UX Criterion | Test File | Test Name | Tool | Steps |
|---|---|---|---|---|
| UX-01: add person in 1 command + Next | test_ux_people.py | test_ux01_people_add_should_print_confirmation_row_and_next_line_when_one_command | Scripted CLI | `people add "Grandma Ruth" --born 1931-05-02 --died 2009-11-30`; assert one invocation, row, `Next:` line |
| UX-02: label cluster in <=2 steps | test_ux_people.py | test_ux02_cluster_label_should_take_one_command_after_sheet_exists_when_review_accept | Scripted CLI | Generate sheet (step 1), run `review accept C12 --name` (step 2); assert `labels` rows and 2 total invocations |
| UX-03: resolve file in 1 command | test_ux_review.py | test_ux03_review_next_screen_should_show_file_album_candidate_confidence_voters_guards_and_commands_when_item_shown | Scripted CLI | `review next` output contains all seven fields; one `accept` resolves with no lookup |
| UX-04: offset in 1 dry-run + 1 apply, >=5 preview rows | test_ux_review.py | test_ux04_album_offset_should_preview_five_before_after_rows_then_apply_in_second_command_when_offset_10y | Scripted CLI | `review set A7 --offset +10y` then `--apply`; assert first run writes nothing |
| UX-05: Next-only flow review->plan->apply->audit | test_e2e_smoke.py | test_ux05_chain_should_complete_following_only_printed_next_lines_when_driven_by_parsed_next | Scripted CLI | Test parses each `Next:` and executes it, no hard-coded commands, until `audit` |
| UX-06: 1 keystroke decide, 1 button + 1 import | test_ux_sheet.py | test_ux06_sheet_should_decide_on_one_keystroke_and_export_with_one_click_when_a_pressed | Playwright (file://) | Press `a` on focused card; click Export; run `review import FILE --apply` |
| UX-10: no write without `--apply`, dry-run ends with apply command | test_ux_safety.py | test_ux10_every_mutating_command_should_write_nothing_and_print_exact_apply_command_when_run_without_apply | Scripted CLI | Loop `fix-metadata`, `undo`, `review import`, `upload`, remediation, bulk `set`, `placeholders revert`; hash fixtures before/after; regex last line `--apply` |
| UX-11: typed file count | test_ux_safety.py | test_ux11_apply_should_write_nothing_when_enter_pressed_and_proceed_when_file_count_typed | Scripted CLI | Pipe empty line, a wrong number, then the file count on a pty; the prompt text does not contain the number; `--yes` honored only non-TTY |
| UX-12: undo command printed | test_ux_safety.py | test_ux12_apply_summary_should_print_undo_run_command_and_undo_should_restore_when_run | Scripted CLI | Assert `Undo: gphotos-organizer undo --run R<n>` and run it |
| UX-13: today/future refused | test_ux_review.py | test_ux13_review_set_should_refuse_today_and_future_with_named_reason_when_date_is_2026_10_16 | Scripted CLI | Assert message text and exit code; `review skip` is the exit path |
| UX-14: confidence + voters visible | test_ux_review.py | test_ux14_review_item_and_plan_rows_should_show_confidence_and_voters_when_rendered | Scripted CLI | Both surfaces asserted |
| UX-15: upload refusal names album, counts, `review next` | test_upload_gate_v1.py | test_ux15_upload_block_line_should_name_album_count_and_review_next_when_one_of_40_unresolved | Scripted CLI | |
| UX-16: `uploaded_unverified (not audited)` | test_status_screen.py | test_ux16_status_should_print_uploaded_unverified_not_audited_and_print_audit_clear_only_after_audit_when_604_grandfathered | Scripted CLI | Then run fake audit; `Audit-clear` appears only after; write state shows `Read-back OK` |
| UX-20: every error has what/why/next/changed | test_errors.py | test_ux20_all_fail_call_sites_should_have_nonempty_hint_and_nothing_changed_clause_when_linted | Scripted CLI | AST scan of all `fail()` calls in `G/`; also run 5 representative errors |
| UX-21: drive-unmounted first, non-zero | test_errors.py | test_ux21_drive_unmounted_should_exit_nonzero_before_touching_cache_when_root_missing | Scripted CLI | Assert exact `Source drive not mounted: /run/media/tstapler/EE5B-3D9B. Mount it and rerun` and no `DATA/` file mtime change |
| UX-22: exact stale-plan text | test_plan_apply.py | test_ux22_stale_plan_should_print_exact_regenerate_line_and_exit_1_when_plan_older_than_fuse | Scripted CLI | |
| UX-23: unknown ids named; others in import still apply | test_review_import.py | test_ux23_unknown_id_should_name_id_and_list_command_while_other_entries_apply_when_import | Scripted CLI | |
| UX-24: quota message + clean Ctrl-C | test_quota.py | test_ux24_quota_wait_should_show_albums_done_countdown_and_exit_0_with_rerun_command_when_sigint | Scripted CLI | Fake 429, injected clock, SIGINT |
| UX-25: failed model download disables only that plugin | test_ml_boundary.py | test_ux25_model_fetch_failure_should_disable_one_plugin_and_print_models_fetch_command_when_offline | Scripted CLI | Others in same run still analyzed |
| UX-26: cloud not-run message names provider + flag | test_cloud_vision.py | test_ux26_cloud_plugin_should_not_run_with_provider_and_flag_named_and_zero_requests_when_no_allow_cloud | Scripted CLI | Message: `Not run; pass --allow-cloud to enable.` |
| UX-27: torn decisions.jsonl tail | test_decisions.py | test_ux27_torn_tail_should_be_reported_and_prefix_kept_when_decisions_jsonl_truncated | Scripted CLI | Asserts message `Ignored 1 torn line ...` |
| UX-28: empty states specific | test_ux_empty_states.py | test_ux28_every_empty_state_should_print_specific_message_and_next_command_when_no_items | Scripted CLI | no clusters, nothing to review, nothing to plan, nothing to upload, empty remote, fresh DB |
| UX-29: every command ends with Next/Nothing to do | test_e2e_smoke.py | test_ux29_last_line_should_start_with_next_or_nothing_to_do_when_each_inventory_command_run | Scripted CLI | Loop S1-S10 command inventory on fixture corpus |
| UX-40: Ctrl-C saved count + rerun command | test_ux_interrupt.py | test_ux40_sigint_should_print_saved_count_and_rerun_command_and_lose_at_most_inflight_chunk_when_analyze_apply_upload_review | Scripted CLI | Four commands, injected KeyboardInterrupt |
| UX-41: cached/computed + ETA | test_runner.py | test_ux41_rerun_should_report_n_cached_m_computed_and_progress_should_show_eta_when_tty | Scripted CLI | pty for the bar |
| UX-42: `review next` resumes at first undecided | test_review.py | test_ux42_review_next_should_start_at_11th_when_10_decided_before_interrupt | Scripted CLI | |
| UX-43: per-file failures do not abort | test_runner.py | test_ux43_run_should_finish_with_failed_count_errors_jsonl_and_retry_failed_hint_when_one_file_raises | Scripted CLI | |
| UX-50: keyboard operable | test_ux_sheet.py | test_ux50_sheet_should_be_fully_operable_by_tab_and_enter_with_shortcuts_off_and_arrows_only_an_enhancement_when_keyboard_only | Playwright (file://) | Tab enters list, walks the card's buttons, leaves; `?` opens key map, Esc closes; no trap; page scrolls when unfocused |
| UX-51: native controls, visible focus | test_report_html.py | test_ux51_sheet_should_use_native_buttons_inputs_and_focus_visible_outline_when_parsed | Static HTML | Also computed focus ring contrast >= 3:1 |
| UX-52: alt text per sheet kind | test_report_html.py | test_ux52_every_img_should_have_alt_matching_its_sheet_kind_when_cluster_dategroup_and_placeholder_sheets_parsed | Static HTML | Three patterns; decorative = `alt=""` |
| UX-53: contrast light + dark | test_report_html.py | test_ux53_declared_color_pairs_should_meet_4_5_text_and_3_ui_in_light_and_dark_when_computed | Static HTML | From stylesheet pairs under `prefers-color-scheme` |
| UX-54: state by word + icon | test_report_html.py | test_ux54_card_state_should_render_accepted_rejected_skipped_undecided_words_when_decided | Static HTML | Plus Playwright greyscale screenshot check |
| UX-55: headings, landmarks, targets, reduced motion | test_report_html.py | test_ux55_sheet_should_have_one_h1_main_lang_en_title_aria_live_24px_targets_reduced_motion_when_parsed | Static HTML | Target size via Playwright bounding boxes |
| UX-56: offline, file://, noindex, under DATA | test_report_html.py | test_ux56_sheet_should_contain_no_http_urls_noindex_meta_and_load_from_file_scheme_when_opened | Playwright (file://) | Network blocked; assert zero requests |
| UX-57: no-JS shows terminal commands + banner | test_ux_sheet.py | test_ux57_sheet_should_show_terminal_command_per_card_and_banner_when_javascript_disabled | Playwright (file://) | Context with `javaScriptEnabled=false` |
| UX-58: missing thumbnails -> alt tile | test_ux_sheet.py | test_ux58_missing_thumbnail_should_render_fixed_size_alt_tile_while_page_works_when_drive_unmounted | Playwright (file://) | Remove thumbs; assert 256px box, no layout shift |
| UX-59: reload keeps decisions; storage-unavailable note | test_ux_sheet.py | test_ux59_reload_should_keep_decisions_and_show_note_when_localstorage_blocked | Playwright (file://) | Two contexts: normal and storage-denied |
| UX-60: no emoji, words not color, NO_COLOR, non-TTY plain | test_ux_language.py | test_ux60_output_should_contain_no_emoji_honor_no_color_and_print_plain_lines_when_non_tty | Scripted CLI | Regex over all captured outputs |
| UX-61: names not in logs or default report | test_people.py | test_ux61_names_should_be_absent_from_logs_and_default_report_when_labels_exist | Scripted CLI | Grep `DATA/logs/*.jsonl` and report |
| UX-62: consistent terminology | test_ux_language.py | test_ux62_status_words_should_match_labels_display_of_enums_in_terminal_and_html_when_compared | Static HTML | Compare against `labels.display()` of `DecisionStatus` (`Needs review`), `WriteState` (`Read-back OK`), review-state sets; `Held`/`Blocked` in plan/upload |
| UX-98: T3 token is not on argv | test_confirm.py | test_ux98_t3_commands_should_refuse_the_argv_album_id_as_answer_when_deny_release_and_i_verified_trash | Scripted CLI | pty; also `prewrite purge`, `undo --force` |
| UX-99: export fields and conflict rule | test_review_import.py | test_ux99_export_should_carry_decided_at_and_group_id_and_conflict_rule_should_be_evaluable_when_import | Scripted CLI | See mapping rows |
| UX-100: run guard | test_people.py | test_ux100_terminal_and_no_js_commands_should_refuse_stale_run_and_import_should_ignore_cluster_label_entries_but_apply_face_member_by_face_id_when_run_differs | Scripted CLI | Plus merged-cluster status after renumbering (`Accepted` / `Partly labeled` / `Mixed names`) |
| UX-101: fold, merge, split | test_people.py | test_ux101_face_reject_after_accept_should_remove_label_and_split_merge_shapes_should_hold_when_c12 | Scripted CLI | |
| UX-102: undo-last defined | test_review.py | test_ux102_undo_last_should_define_last_nonretracted_and_print_what_it_undoes_when_any_shell | Scripted CLI | |
| UX-103: group guard sample, histogram, except | test_review_groups.py | test_ux103_sample_should_scale_and_histogram_and_except_should_leave_suspect_when_group_decision | Scripted CLI | Plus Static HTML for the histogram |
| UX-104: per-source progress, leftovers, status rows | test_review.py | test_ux104_progress_should_be_per_source_and_parked_leftovers_should_resurface_with_plan_as_primary_next_and_only_placeholder_line_should_precede_all_decided_when_review_next | Scripted CLI | |
| UX-105: export names, --latest, index regen, --open, --all resume | test_sheet_pages.py | test_ux105_export_filename_latest_dry_run_should_pin_files_and_latest_apply_should_be_refused_and_index_regen_open_failure_and_all_resume_should_work_when_212_sheets | Scripted CLI | Plus `--archive` moves applied files and never deletes them |
| UX-106: Set date validation | test_ux_sheet.py | test_ux106_set_date_should_validate_format_today_future_and_birth_with_parsed_precision_and_aria_describedby_when_entered | Playwright (file://) | Plus import-side test above |
| UX-107: operable with shortcuts off | test_ux_sheet.py | test_ux107_ten_cards_should_be_decidable_with_tab_shift_tab_and_enter_only_in_exactly_five_tab_presses_per_card_and_next_undecided_card_should_skip_decided_cards_when_shortcuts_off_and_no_arrows | Playwright (file://) | 5 stops on cluster and placeholder sheets, 6 on date-group sheets; all 24 cards decidable without arrow keys |
| UX-108: aria-pressed, no composite role, counter vs live text | test_ux_sheet.py | test_ux108_buttons_should_expose_aria_pressed_and_live_region_should_be_separate_from_visible_counter_when_decided | Playwright (file://) | |
| UX-109: labels, describedby, closed select | test_report_html.py | test_ux109_fields_should_have_labels_describedby_and_name_should_be_closed_select_when_parsed | Static HTML | |
| UX-110: 200% zoom and text spacing | test_ux_sheet.py | test_ux110_sheet_should_not_clip_or_overlap_at_200_percent_zoom_and_wcag_1_4_12_spacing_when_scanned | Playwright (file://) | Also the manual legibility item |
| UX-111: status Next order | test_status_screen.py | test_ux111_next_should_follow_eight_rule_order_and_never_loop_when_failed_files_are_permanent_and_leftovers_are_parked | Scripted CLI | Follows only Next: lines from a fixture to `Nothing to do` in at most 10 steps |
| UX-112: fsck privilege routes | test_drive_backup.py | test_ux112_fsck_should_print_sudo_and_from_output_routes_and_never_prompt_for_a_password_when_unreadable | Scripted CLI | |
| UX-113: typed stable ids | test_decisions.py | test_ux113_aliases_should_be_allocated_once_per_stable_key_and_rebuilt_from_log_and_bare_number_should_be_refused_with_prefixes_when_re_fused | Unit | `F42` and `P42` are distinct; a line whose alias and key disagree is ignored; allocation resumes above the highest alias |
| UX-113: typed ids at the CLI and in exports | test_review.py | test_ux113_review_accept_should_dispatch_by_prefix_and_import_should_resolve_by_item_key_and_reject_alias_key_mismatch_when_f42_and_p42_exist | Scripted CLI | |
| UX-114: terminal versus hold reject | test_decisions.py | test_ux114_fold_should_mark_terminal_and_parked_per_kind_when_reject_on_placeholder_audit_cluster_face_versus_file_album_year_precision | Unit | `SOURCE_VERBS[kind].reject_terminal` |
| UX-114: one attribute read everywhere | test_review.py | test_ux114_state_filters_all_decided_line_status_upload_gate_and_import_conflict_should_agree_when_genuine_placeholder_and_rejected_file_exist | Scripted CLI | Genuine placeholder never parked or nagging; rejected file parked; a later skip never blocks a sheet entry |
| UX-115: group materialization | test_review_groups.py | test_ux115_group_apply_should_write_per_file_records_and_undo_should_restore_previous_records_and_later_files_should_not_inherit_when_album_grows | Integration | No read-time expansion |
| UX-115: exceptions union and overlap | test_review_groups.py | test_ux115_exceptions_should_be_united_across_same_group_id_exports_and_stale_ones_dropped_and_overlap_should_resolve_by_latest_record_when_two_seeds_exported | Integration | Plus single-page sheet cap: `--sample 300` refused |
| UX-116: control table | test_ux_sheet.py | test_ux116_every_control_should_map_to_one_export_kind_action_row_and_every_export_kind_should_have_a_producing_control_when_template_walked | Static HTML | Including the album block, `Offset`, year-precision and audit cards |
| UX-116: album offset import | test_review_import.py | test_ux116_album_offset_entry_should_preview_like_review_set_offset_and_require_apply_when_imported | Scripted CLI | |
| UX-117: recorded fsck preflight | test_plan_apply.py | test_ux117_preflight_should_read_recorded_fsck_result_never_run_fsck_or_sudo_and_reject_stale_record_when_older_than_24h_or_before_last_write | Scripted CLI | Periodic fsck pauses at the album boundary with a resume line (exit 0) |
| UX-118: upload gate wording | test_upload_gate.py | test_ux118_upload_apply_should_print_ready_would_upload_gate_lines_before_prompt_and_ok_uploaded_unverified_only_after_when_confirmed | Scripted CLI | Single album uses the file count as token |
| UX-118: import pin | test_review_import.py | test_ux118_latest_apply_should_be_refused_and_dry_run_should_print_pinned_apply_command_when_newer_export_lands_between | Scripted CLI | |
| UX-108 (revised): group semantics | test_report_html.py | test_ux108_li_should_have_no_role_and_contain_role_group_and_export_should_use_aria_disabled_with_described_by_when_empty | Static HTML | axe list/listitem rules pass |
| Story 7.3: typed-name dialog trigger | test_report_html.py | test_dialog_should_fire_only_below_25_percent_shown_when_60_and_120_face_clusters | Static HTML | `TYPED_NAME_SHOWN_FRACTION` |
| Story 2.5 / 10.3: permanent failure | test_runner.py | test_retry_failed_should_mark_second_failure_permanent_and_status_should_not_count_it_as_incomplete_when_same_error_class | Integration | |
| UX (manual): no dead ends, cold read | manual | Terminal walk-through on real data after 10.5 | Manual | Run the real-drive dry-run once; every screen leaves a stated way forward |
| UX (manual): usability pass | manual | Story 7.5 timed run on the fixture corpus | Manual | Seconds per cluster label, per file item and per placeholder album, switches and import runs per 10 labels, against 25 s / 15 s / 120 s / 2 / 3; recorded in ADR-009 |
| UX (manual): sheet legibility | manual | 100-card cluster sheet at 200% zoom and in high-contrast mode | Manual | No overlap; focus ring visible; keyboard-only labeling of 10 cards |

## Test Stack
- **Unit**: plain `test_*.py` functions, `assert` statements, `G/tests/_test_runner.py` (`run_tests(globals())`), run as `uv run test_x.py`; `make gphotos-test` loops over `G/tests/test_*.py` like `llm-sync-test` (`Makefile:40-41`) and is part of `make ready`. Golden files under `G/tests/golden/` regenerated only with `--update-golden`. No pytest.
- **Integration**: real SQLite (two stores), real exiftool 13.55 on generated fixture files, fake `exiftool`/`rclone` via `GPHOTOS_EXIFTOOL`/`GPHOTOS_RCLONE` (`G/tests/fakes/`), real subprocess for `ML_CMD` with a `noop` plugin, injected `sleep`/`now` for quota tests, synthetic embeddings (never real model weights).
- **E2E / UX**: scripted CLI runs over the 30-image fixture corpus (`make_corpus.py`); Playwright (`ui-playwright` skill) on `file://` sheets for UX-06, 50, 56-59; two manual checklist items. Model-dependent accuracy checks (real InsightFace, OCR engines) stay in spikes and the e2e smoke, as in plan.md Test Strategy.
- **Property checks**: fusion idempotence, monotonicity under abstain, Layer B result inside Layer A survivors.
- **Planning-artifact checks**: `python3 implementation/waves.py --check` (waves, same-wave file collisions, `Depends on` edges, per-task Files bound, header counts) and `--effort` (cost units from task classes) run at each wave boundary and before Phase 5; both must exit 0.

## Coverage Targets and How to Measure

| Stack | Coverage command | Target |
|---|---|---|
| Python (plain-function tests) | `cd stapler-scripts/gphotos-organizer && for t in tests/test_*.py; do uv run --with coverage coverage run -p --source=pipeline,plugins,ml_plugins "$t"; done && uv run --with coverage coverage combine && uv run --with coverage coverage report --fail-under=80` (INFERRED: coverage is not yet wired into `gphotos-test`; add as `make gphotos-coverage`, not part of `ready`) | >=80% line on `pipeline/`, `plugins/`, `ml_plugins/`; 100% of branches in the truth-table classifier, guards, journal state machine and `upload_gate` predicate |

- All public service methods: happy path + error paths covered (rows above).
- All external integrations (exiftool, rclone, ML subprocess, cloud HTTP): unit with fake + at least one integration test (rows tagged Integration).
- UX acceptance criteria: each of UX-01..UX-62 (40 IDs), UX-70..UX-97 (28 IDs) and UX-98..UX-112 (15 IDs) has a test above (UX-96 is the Story 7.5 pass, covered by the fixture test plus a manual item); three manual items cover perceptual criteria.
- Wall-clock-blocked checks (cannot be automated, recorded in the PR of the named story): real-drive `placeholders scan` counts vs the 2026-10-16 baseline (1.9), `recover --list` listing at least the two known leftovers (1.10), 200-image CPU timing (4.1), Google Photos capability spike outcomes (9.1), owner `ps` checklist (item 1).

## Triad repair pass 1 (2026-10-16): what changed in this plan's test surface
Added rows above (grouped before the SM3 block): cluster-sheet semantics and export schema `gpo-decisions/2` (the UX blocker), per-source verbs, review at scale (filters, `--open`, group decisions, placeholder sheets, pagination, index, show-more), sheet state and WCAG additions, name resolution, confirmation tiers (typed file count, not the plan id), reversal map and vocabulary, help panels, completion and alias notices, the wave gate, the B4 argfile pin, and the revised Success Metrics (SM1 numeric bound with the old SM5 folded in; SM2 baseline-first; new SM5 remediation and SM6 review burden). Story count in the header is recounted by grep, not estimated.

## Triad repair pass 2 (2026-10-16): what changed in this plan's test surface
Added rows for UX-98 to UX-112 and the matching mapping rows: the T3 count-token rule (the album id is no longer the token), the export fields `decided_at`, `group_id` and `outcome`, the cluster run guard on terminal and no-JS commands, fold order and the single merge/split definition, the defined `review undo-last`, the placeholder sample scaling and `--except`, per-source progress and leftovers, `status` Next order, export naming with `--latest`, sheet `Set date` validation, keyboard operability with shortcuts off, `aria-pressed`, labels, 200% zoom and text spacing, and the `backup fsck` privilege routes. Renamed rows: UX-26 (`Not run;`), UX-27 (`Ignored 1 torn line`), UX-50, UX-52, UX-62 and the stale-run import test. The vocabulary scan now has explicit rules V1 to V5 and an allow-list file, so the design's own sample output passes it. Test counts: the plan header now reads 203 tasks (8 added: 1.13c, 4.5e, 7.2f, 7.3f, 7.4e, 7.6e, 8.8d, 10.3c); `python3 implementation/waves.py --check` is the recount.

## Triad repair pass 3 (2026-10-16): what changed in this plan's test surface
Added rows for UX-113 to UX-118: typed stable item ids and `item_key` resolution, the terminal-or-hold reject attribute read by one fold, materialized group decisions with united exceptions, the sheet control table, the recorded-fsck preflight and the upload `Gate:` wording with the pinned import command. Revised rows: UX-85 and UX-107 (natural Tab order, 5/6 stops, `Next undecided card`, no arrow dependence), UX-100 (`face_member` applied by `face_id`), UX-104 (parked leftovers, `plan` primary), UX-105 (`--latest` previews only), UX-108 (`<li>` without role, `aria-disabled` Export), UX-111 (eight rules, no loop), the T3 token row (argv collision falls back or refuses, no raise), and the vocabulary scan (V3 lowercase outcomes, V4 on review screens, V5 `Pending`). Test counts: the plan now reads 209 tasks (6 added: 1.13d, 7.1c, 7.2g, 7.4f, 7.6f, 10.3d); `python3 implementation/waves.py --check` is the recount, and it now also fails when a story's `**Depends on**` line and `DEPS` differ in either direction.
