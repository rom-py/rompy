# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
and [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Return-schema contract (#3)

- Defined typed success/failure contracts for generation, execution, pipeline,
  and postprocessing.  The approved execution API is
  `ModelRun.run(...) -> ModelRunResult`.
- Defined strict current sidecar kind/version handling and actionable rejection
  of legacy or ambiguous core-v1 and flat WW3-v1 documents.  No migration reader
  is included.
- Defined UTC timing, `end_time >= start_time`, and numeric-seconds wire values
  for durations and intervals; human-readable formatting is presentation-only.
- Defined typed local staging-relative and explicit remote URI artifact
  identities, with observed artifacts separate from expected and missing output
  evidence.
- Defined one validated processor construction/input/output boundary and strict
  pipeline successful-prefix semantics.
- Defined observable canonical-sidecar persistence failure diagnostics that
  retain any primary operation error.
- Added syntactically valid bounded success, failure, and malformed JSON
  examples plus falsifiable round-trip/rejection requirements.  Executable
  validation and frozen fixture hashes remain follow-up work for #4/#5/#6.

### Follow-up ownership

- **#4** implements schema coherence, strict serialization/versioning, and
  canonical persistence.
- **#5** implements processor, pipeline, CLI, and fresh-process handoff parity.
- **#6** validates executable fixtures, fresh-process replay, adversarial cases,
  and frozen hashes after #4/#5 implement the contract.

This entry documents the issue #3 contract; it does not claim runtime behavior,
plugin adaptation, or a release/version bump.
