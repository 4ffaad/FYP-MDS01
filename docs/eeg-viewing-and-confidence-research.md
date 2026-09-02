# EEG waveform, seizure-detection, and confidence display for the MDS01 research prototype

Date: 2026-08-31

## Scope and safety statement

This report recommends how MDS01 should present research EEG waveforms, temporal model detections, and model confidence or uncertainty. It does **not** establish clinical validity, diagnostic performance, regulatory clearance, or suitability for patient care. The interface should say **research use only**, describe model outputs as hypotheses for review, and never use wording such as “confirmed seizure.”

The central recommendation is a linked three-layer view:

1. an overview timeline for the entire recording;
2. a detailed, navigable 18-channel EEG viewport;
3. a window-score track aligned to the same time axis, with the decision threshold and model-positive intervals clearly distinguished from the waveform.

The model in this repository operates on 4-second windows with a 2-second stride. Every displayed score and detection must preserve that temporal resolution instead of implying sample-level seizure localization.

## 1. A sigmoid or softmax output is not automatically a calibrated probability

A sigmoid or softmax converts model outputs to values in `[0, 1]`, but that bounded range alone does not establish a frequency interpretation. A value can rank windows correctly while still being systematically overconfident or underconfident. Calibration requires that, among comparable predictions assigned probability `p`, the event occur approximately a proportion `p` of the time. Original calibration research demonstrates both the distinction between ranking scores and probability estimates and the miscalibration of modern neural networks ([Zadrozny and Elkan, 2002](https://doi.org/10.1145/775047.775151); [Guo et al., 2017](https://proceedings.mlr.press/v70/guo17a.html)).

MDS01 should therefore use these display labels:

| Runtime output | Permitted UI label | Prohibited interpretation |
| --- | --- | --- |
| Development stub | `Development score` | Probability, confidence, accuracy, or clinical evidence |
| Real model without validated calibration | `Model score (uncalibrated)` | “72% chance of seizure” |
| Real model with frozen, documented calibration | `Estimated window probability` | Recording-level probability or clinical certainty |

For a calibrated value, the precise unit should be visible: **“Estimated probability that this 4-second window meets the research seizure label definition.”** It is not the probability that the patient has epilepsy, that the recording contains any seizure, or that a clinician will confirm an event.

Do not introduce arbitrary “low / medium / high confidence” bands. Such categories add new thresholds that themselves require validation. Continue to show the numeric score, the reviewed threshold, and whether the threshold was crossed.

## 2. Calibration methods and evaluation

### Recommended data split

Calibration data must be separate from model-training data, and final test data must remain untouched. Because adjacent EEG windows overlap and windows from one patient are correlated, splitting individual windows would leak information. Subject-independent seizure detection should preserve subject independence between training and test sets, as specified by the original SzCORE framework ([Dan et al., 2025](https://doi.org/10.1111/epi.18113); [official SzCORE framework](https://epilepsybenchmarks.com/framework/)).

Use three patient-disjoint partitions:

- **training:** fit the seizure detector;
- **calibration/development:** fit the calibrator and select the alert threshold and event post-processing rule;
- **test:** report the locked detector, calibrator, threshold, and event rule once.

If cross-validation is necessary, grouping must remain at patient level. Confidence intervals should use patient-cluster bootstrap resampling, not independent resampling of overlapping windows.

### Candidate calibrators

**Temperature scaling is the preferred first candidate for the neural-network runtime.** It learns one positive temperature `T` on held-out data by minimizing negative log-likelihood, then applies sigmoid/softmax to logits divided by `T`. It preserves ranking and therefore does not change which example has the largest class score. Guo et al. found this single-parameter method effective across the neural-network tasks they studied, although that evidence is not EEG-specific and must be re-evaluated here ([Guo et al., 2017](https://proceedings.mlr.press/v70/guo17a.html)).

For this binary model:

```text
p_calibrated = sigmoid(logit / T)
```

Prefer retaining the model logit directly. Recovering a logit from an already rounded or clipped sigmoid output is mathematically possible but can lose information near 0 and 1.

**Platt scaling** fits both a slope and intercept in a sigmoid mapping. It is appropriate when the available model output is an arbitrary one-dimensional decision score or when a two-parameter correction is justified. It should be compared against temperature scaling on the same patient-disjoint calibration data, not selected from test performance. The original method maps classifier scores through a learned sigmoid ([Platt, 1999](https://www.cs.colorado.edu/~mozer/Teaching/syllabi/6622/papers/Platt1999.pdf)); official scikit-learn documentation gives the current implementation and fitting contract ([scikit-learn probability calibration](https://scikit-learn.org/stable/modules/calibration.html)).

**Isotonic regression** learns a non-decreasing stepwise mapping and can correct more general monotonic distortions. It is more flexible but more prone to overfitting on small calibration sets; official scikit-learn guidance notes that it generally needs substantially more calibration data than sigmoid calibration ([scikit-learn probability calibration](https://scikit-learn.org/stable/modules/calibration.html)). Use it only as a prespecified comparison when the calibration partition contains enough independent patients and seizure events. A large count of overlapping windows is not equivalent to a large independent sample.

### Metrics to report

Report calibration and discrimination separately. At minimum:

- reliability diagram with the identity line, bin counts, and both mean predicted probability and empirical seizure-window rate per bin;
- Expected Calibration Error (ECE), including the exact binning rule and number of bins;
- Brier score;
- negative log-likelihood;
- precision-recall performance, sensitivity, precision, and F1;
- event sensitivity, false detections, and false alarms per 24 hours;
- patient-clustered 95% confidence intervals where feasible.

ECE is a weighted average of binned gaps and depends on the binning scheme; it should not appear without the reliability diagram and bin counts. Guo et al. define the standard binned ECE and explain why a reliability diagram alone does not show how many examples occupy each bin ([Guo et al., 2017](https://proceedings.mlr.press/v70/guo17a/guo17a.pdf)).

The binary Brier score is the mean squared difference between predicted probabilities and binary outcomes, originating with Brier's probability-score formulation ([Brier, 1950](https://doi.org/10.1175/1520-0493(1950)078%3C0001:VOFEIT%3E2.0.CO;2)). It is a proper scoring rule, but it combines calibration, discrimination, and outcome uncertainty; a lower Brier score does not by itself prove better calibration. The reliability diagram, ECE, Brier score, and negative log-likelihood should be interpreted together ([scikit-learn probability calibration](https://scikit-learn.org/stable/modules/calibration.html)).

Calibration must be checked again on external or later-site data. Post-hoc calibration can degrade under dataset shift, so an in-distribution calibrated probability is not a guarantee of trustworthy uncertainty for a new hospital, acquisition system, montage, population, or artifact pattern ([Ovadia et al., 2019](https://proceedings.neurips.cc/paper_files/paper/2019/hash/8558cb408c1d76621371888657d2eb1d-Abstract.html)).

### What “uncertainty” should mean in this prototype

A calibrated probability is a point estimate with a tested frequency interpretation; it is not automatically an estimate of epistemic uncertainty, an out-of-distribution detector, or a confidence interval for one window. Temperature scaling changes calibration but does not add a distribution over model parameters.

Therefore:

- show `Calibration: not validated` or the locked calibration method and evaluation version;
- show input-quality or unsupported-input warnings separately from the seizure score;
- do not invent per-window uncertainty intervals unless the model is extended with a separately evaluated uncertainty method;
- show confidence intervals for aggregate evaluation results in a research report, not as if they were uncertainty bounds around an individual patient's window score.

## 3. Window-level, event-level, and recording-level outputs

These are different prediction targets and must not share one label.

### Window level

The native output is one score for each interval `[start, start + 4 s)`, emitted every 2 seconds. Display each score at its window centre (`start + 2 s`) in the score track, while the tooltip and selected-state overlay show the full 4-second support. Connecting points can help visual tracking, but the UI must state that scores are discrete overlapping-window outputs rather than continuous sample-level probabilities.

Do not average overlapping window scores into a “per-second probability” unless that new quantity is defined and calibrated separately. At most two windows cover an interior time point, but their dependence means a noisy-OR calculation is also unjustified.

### Temporal detections and event hypotheses

Threshold each window using the locked development threshold. For display, take the union of threshold-positive 4-second intervals and merge intervals that overlap or directly touch. This produces a transparent, deterministic **model-positive interval** overlay:

```text
window 10: 20–24 s, positive
window 11: 22–26 s, positive
display interval: 20–26 s
```

This union is a visualization and review-navigation rule, not a clinically validated seizure onset or offset. A detected boundary can only be localized to the windowing scheme, and the earliest positive interval start may precede the score's centre by 2 seconds. Tooltips should expose the first and last contributing windows, peak window score, threshold, and duration.

For formal evaluation, keep both sample/window-based and event-based results. SzCORE proposes complementary 1 Hz sample-based scoring and event-based scoring, because the former gives fine-grained agreement while the latter answers how many seizures were detected or missed and how many false alarms occurred. Its event rules include explicit overlap and temporal-tolerance parameters that must be declared rather than hidden ([Dan et al., 2025](https://doi.org/10.1111/epi.18113); [official SzCORE scoring specification](https://epilepsybenchmarks.com/framework/)).

**Implementation inference:** convert the merged hypothesis intervals to 1 Hz labels for SzCORE-compatible sample evaluation, using the framework's overlap rule. Keep window-level calibration evaluation on the original 4-second labels. Do not silently apply SzCORE's suggested 30-second pre-ictal, 60-second post-ictal, and 90-second event-merging tolerances to the interactive waveform overlay; those are evaluation parameters and would visually enlarge model output beyond its native support.

### Recording level

“At least one window crossed the threshold” is a recording-level decision rule, not a recording-level probability. Longer recordings create more opportunities for one window to cross a threshold. Neither the maximum window score, arithmetic mean, flagged-window fraction, nor `1 - product(1 - p_window)` should be called the probability that the recording contains a seizure without separate recording-level development and calibration.

For the current prototype, report:

- `Model-positive recording` or `No window crossed threshold`;
- peak **window** score and its interval;
- number and fraction of threshold-positive windows;
- number and duration of merged model-positive intervals;
- model version, score type, threshold, and calibration status.

If a recording-level probability is later required, predefine an aggregation function or train a recording-level model, calibrate that output against recording-level reference labels on patient-disjoint data, and evaluate it separately. Until then, return `recording_probability_available: false`.

## 4. EEG waveform and temporal-overlay UI

The American Clinical Neurophysiology Society's digital EEG display guidance calls for adequate temporal and spatial resolution, indicated horizontal and vertical scales, channel/montage labels, gain and filter settings, event markers, timestamps, and easy access to EEG data even when automated detections or trends are shown. It identifies a conventional 10-second page and supports expanded or compressed time scales ([ACNS Guideline 4](https://www.acns.org/UserFiles/file/EEGGuideline4Digital.pdf)). ACNS minimum technical requirements also warn that filters can remove or distort clinically relevant activity and require setting changes to be identified ([ACNS Guideline 1](https://www.acns.org/pdf/guidelines/Guideline-1.pdf)).

MDS01 should implement the following research viewer.

### A. Recording overview

- Full-duration horizontal navigator.
- Separate lanes for model score, threshold, merged model-positive intervals, and reference annotations when available for offline research.
- Never use the same colour or label for model hypotheses and expert reference annotations.
- Clicking a model-positive interval centres the detail viewport on that interval.
- Summary text such as `3 model-positive intervals · 11/928 windows above 0.62`.

### B. Detailed EEG viewport

- Show all 18 configured bipolar channels in their reviewed order.
- Default to a 10-second viewport; offer 5, 10, 20, and 30 seconds without changing the underlying data.
- Show channel labels, seconds from recording start, sampling rate, montage, amplitude unit, sensitivity/gain, and active filter settings.
- Provide vertical gain and horizontal time-scale controls, reset to reviewed defaults, and identify every post-hoc display filter. Never imply that display filtering changes the stored model input or past predictions.
- Use one subtle translucent background band for a model-positive interval so the waveform remains visible. Add stronger boundary lines for the selected 4-second window.
- Keep the score track directly below the waveform with the same x-axis, a labelled threshold line, and points at 2-second intervals.
- Tooltip example: `Window 184 · 368–372 s · uncalibrated model score 0.71 · threshold 0.62 · model-positive`.
- Label the representation honestly: `metadata-scrubbed EEG` or `signal-obfuscated research representation`. Do not label an obfuscated representation as raw EEG.

### C. Confidence and limitations panel

Show a compact technical disclosure near the plot:

```text
Output unit       4-second window, 2-second stride
Score type        Uncalibrated model score
Threshold         0.62 (locked development threshold)
Calibration       Not validated
Model             name / version
Use               Research review only; not a diagnosis
```

When calibration is validated, replace the score-type and calibration rows, but retain the window unit and limitation. Do not place a large “72% confident” badge above the EEG; it hides the prediction target and invites automation bias.

### D. Review actions

- `Previous detection` and `Next detection` controls.
- `Jump to peak window` control.
- Optional reviewer annotation stored separately from model output.
- Exported research annotations should include onset, duration, event type, and an explicitly defined confidence field or `n/a`, consistent with the SzCORE event format. For merged events, store `peak_window_score` as a descriptive field rather than mislabelling it as event probability ([official SzCORE framework](https://epilepsybenchmarks.com/framework/)).

## 5. Clinical and research UI cautions

Automated seizure detection should support expert review, not replace it. The ILAE/IFCN clinical-practice guideline uses expert-interpreted video-EEG or video as the reference and treats sensitivity, false-alarm rate, adverse events, and usability as important outcomes; it also notes uncertainty about meaningful clinical outcomes even for better-studied wearable detection use cases ([Beniczky et al., 2021](https://www.ilae.org/files/ilaeGuideline/Automjated-seizure-detection-using-wearable-devices---epi.16818.pdf)). This prototype is not evidence that those results transfer to MDS01.

The UI should always expose:

- intended research use and intended user;
- model and dataset version;
- prediction target and time unit;
- score type and calibration status;
- fixed threshold and post-processing rule;
- known input exclusions and failure modes;
- aggregate performance with confidence intervals on an independent test set;
- whether current data differ from the development population or acquisition setup.

This aligns with FDA/Health Canada/MHRA transparency principles, which emphasize the human-AI team, clear essential information, known limitations, data gaps, performance uncertainty, and circumstances where inputs differ from development data ([FDA, Health Canada, and MHRA, 2024](https://www.fda.gov/medical-devices/software-medical-device-samd/transparency-machine-learning-enabled-medical-devices-guiding-principles)).

Analytical correctness is not the same as clinical validation. IMDRF separates valid clinical association, analytical/technical validation, and clinical validation; a technically correct waveform viewer and calibrated research model do not demonstrate a clinically meaningful benefit ([IMDRF SaMD Clinical Evaluation, 2017](https://www.imdrf.org/sites/default/files/docs/imdrf/final/technical/imdrf-tech-170921-samd-n41-clinical-evaluation_1.pdf)). Any later live clinical evaluation should also assess human factors and the interaction between users and the AI system, consistent with the original DECIDE-AI consensus guidance ([Vasey et al., 2022](https://doi.org/10.1038/s41591-022-01772-9)).

## 6. Implementation-ready recommendation for this repository

### Phase 1 — make the existing prototype semantically correct

1. Display the available de-identified or obfuscated EEG in a 10-second, 18-channel viewport, linked to the existing score timeline.
2. Keep the overview timeline at recording scale and the waveform viewport at review scale.
3. Render one score point per existing 4-second window at `start + 2 s`; preserve `start_seconds` and `end_seconds` in tooltips and selection state.
4. Merge overlapping or touching threshold-positive window intervals only for the visible model-positive overlay and navigation.
5. For the development stub, show `Development score — not a probability` everywhere.
6. For an uncalibrated H5 output, show `Uncalibrated model score`; retain the raw score and threshold.
7. Keep the recording summary descriptive. Do not expose a recording probability.
8. Display waveform representation, montage, sampling rate, channel order, amplitude units, gain, filters, and timestamps.
9. Preserve the repository's privacy boundary: only return the explicitly enabled retained representation, never original patient metadata or original files.

### Phase 2 — validate confidence

1. Freeze the model artifact and preprocessing contract.
2. Preserve raw logits if the model architecture permits them.
3. Create a patient-disjoint calibration/development partition distinct from the final test partition.
4. Fit temperature scaling by held-out negative log-likelihood. Prespecify Platt scaling as a comparison; include isotonic only if there are enough independent calibration patients/events.
5. Select the alert threshold and temporal post-processing rule on development data according to a declared trade-off involving event sensitivity and false alarms per 24 hours. Do not default to `0.5` merely because the output is bounded.
6. Lock model, calibrator, threshold, and event rule before test evaluation.
7. Report window reliability diagram, bin counts, ECE, Brier, NLL, precision-recall metrics, and patient-clustered confidence intervals.
8. Report SzCORE-compatible sample- and event-level metrics, including event sensitivity and false alarms per 24 hours.
9. Compare calibration and event performance by privacy representation if both metadata-scrubbed and signal-obfuscated inputs are supported; do not assume one calibrator transfers between them.
10. Only then change the UI label from `Model score` to `Estimated window probability`.

### Phase 3 — research validation beyond the prototype

1. Evaluate on an external patient-disjoint dataset or site without refitting.
2. Test waveform readability, detection navigation, threshold comprehension, and automation-bias risks with intended research users.
3. Document model failure modes, unsupported recordings, acquisition differences, and data-quality warnings.
4. Keep the interface and report labelled non-clinical until valid clinical association, analytical validation, clinical validation, and applicable regulatory requirements have been addressed.

## Decision summary

- **EEG viewing:** yes, show the retained privacy-approved representation with conventional EEG controls and visible technical settings.
- **Seizure location:** show threshold-positive 4-second windows and their merged visual union; call these model-positive intervals, not confirmed seizure onset/offset.
- **Confidence today:** display a development or uncalibrated score unless a patient-disjoint calibration study has been completed.
- **Calibration method:** temperature scaling first; compare Platt scaling; use isotonic only with sufficient independent calibration data.
- **Calibration evidence:** reliability diagram plus bin counts, ECE, Brier, and NLL, with patient-clustered uncertainty.
- **Recording confidence:** do not derive it from maximum, mean, flagged fraction, or noisy-OR of overlapping windows. Keep recording-level output descriptive until separately developed and calibrated.
- **Clinical claim:** none. This remains a research review prototype.
