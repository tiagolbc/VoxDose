# Validation records

Current regression suite: **53 tests**. Install `.[dev]` and run `python -m pytest -q`.

`release_2.0.2/three_runs.json` retains three isolated runs of the same Windows EXE: 53 source tests and 45 application checks per round, covering English defaults, languages, hover-entry events, palettes, plot editors, synthetic voice/silence, exports and sessions. Native pointer hover and the installer welcome were also inspected through the Windows desktop. Local user paths are omitted from public summaries; outcomes, counts and artifact hashes are retained.

`release_2.0.2/installer_three_runs.json` records three actual NSIS install/launch/uninstall cycles, including paths with spaces, with 13 installer checks and all application checks per round. Data and unknown user files survived uninstall. Validation registry/shortcut names were isolated from normal installations.

Python remains installed on the development computer; tests removed its PATH/environment and checked the embedded runtime. This is not a clean-VM claim. Mac binaries have not been built or verified for this revision.

`synthetic_ground_truth` retains the independent numerical study: **142/144 acceptance criteria**, with two F0 precision failures at SNR 10 dB. SPL is an assigned numerical contract, not a physical calibration; CPPS/HNR have no assigned analytical ground truth. Run `python tools/validate_synthetic.py` to regenerate signals/results; its nonzero exit exposes unmet criteria. Generated waveforms are not tracked. Absolute paths in the public ground-truth specification are converted to relative paths; numerical values are unchanged.
