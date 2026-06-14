Test: Tolerate the presence of pytest's LogCaptureHandler on our loggers. Pytest
9.1.0 started setting that up even when invoked with -s.
