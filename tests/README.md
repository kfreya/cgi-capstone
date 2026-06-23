# Tests

This directory contains automated tests for the CGI Capacity Analyzer
prototype.

The test suite covers opportunity cleaning, validation helpers, capacity
scoring, RFP processing, Azure helper behavior, and vector-store behavior.

Run all tests from the repository root:

```bash
python -m pytest
```

Tests should use synthetic or mocked data only. Do not commit local CGI data,
secrets, or generated private artifacts here.
