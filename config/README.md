# Config

This directory contains shared configuration used by validation and scoring
logic.

- `fallback_assumptions.yaml` records fallback rules and assumptions used when
  source fields are missing, unreliable, or need consistent interpretation.

Configuration files should be non-secret and safe to commit. Do not store API
keys, endpoints, local credentials, or CGI data extracts here.
