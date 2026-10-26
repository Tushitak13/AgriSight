# AgriSight Tomato Disease Model Evaluation

**Owner:** Person 1 — Inference and Model Evaluation

**Status:** Exploratory evaluation completed; field validation pending

**Model:** `neghani/plantvillage-mobilenetv2`

**Pinned revision:** `v1.0`

## 1. Objective

Evaluate the tomato disease classifier on PlantVillage images and investigate its behavior on an independent field-image dataset.
## 2. PlantVillage Evaluation

Dataset: `D:\Archive\plantvillage dataset\color`

Model: `neghani/plantvillage-mobilenetv2`, pinned revision `v1.0`.

### Initial exploratory result — not an independent test

The initial evaluation sampled up to 20 images from each of 10 tomato classes, using random seed `42`.

| Metric | Result |
|---|---:|
| Images evaluated | 200 |
| Initially reported top-1 accuracy | 100% |
| Non-tomato top predictions | 0 |
| Sampled images overlapping the recorded training split | 157 |

The initial 100% result is contaminated by training-image overlap and must not be presented as independent held-out accuracy.

### Recorded PlantVillage tomato test split

A corrected evaluation used the tomato-class images listed in the model revision's recorded test split.

| Metric | Result |
|---|---:|
| Test images listed in the manifest | 1,816 |
| Successful inferences | 1,816 |
| Inference errors | 0 |
| Correct top-1 predictions | 1,792 |
| Top-1 accuracy | 98.68% |
| Non-tomato top predictions | 3 |

The result is \(1792 / 1816 = 98.68\%\). It should be described as accuracy on the model's recorded PlantVillage tomato test split, not as accuracy on real-world farm images. The split manifest was used to select test images, but the model's training process has not been independently audited to rule out all possible leakage.

## 3. Field Dataset Exploratory Evaluation

**Dataset:** Tomato Leaf Dataset — Annotated

**Test image directory:** `TomatoLeafMulticlass (Annotated)\test\images`

| Metric | Result |
|---|---:|
| Images processed | 31 |
| Successful inferences | 31 |
| Inference errors | 0 |
| Top-1 tomato predictions | 6/31 (19.4%) |
| Top-1 non-tomato predictions | 25/31 (80.6%) |
| Top five contained a tomato class | 28/31 (90.3%) |
| Mean top-1 softmax score | 0.7639 |
| Median top-1 softmax score | 0.8605 |

### Top-1 prediction distribution

| Predicted class | Image count |
|---|---:|
| `Grape___Black_rot` | 20 |
| `Tomato___Late_blight` | 5 |
| `Grape___Esca_(Black_Measles)` | 2 |
| `Pepper,_bell___Bacterial_spot` | 2 |
| `Blueberry___healthy` | 1 |
| `Tomato___Early_blight` | 1 |

### Interpretation

The model frequently assigns field images to non-tomato classes. This suggests a possible domain-shift problem between PlantVillage images and field images.

The softmax scores are uncalibrated and must not be interpreted as probabilities of correctness. The field dataset's numeric annotation mapping has not been verified, so disease-class accuracy is not reported.

## 4. Limitations

- The extracted field dataset does not contain an obvious class-mapping file such as `data.yaml`, `classes.txt`, or a README defining the numeric IDs.
- The 31-image field evaluation is exploratory.
- The field test split must remain held out and must not be used for training, fine-tuning, threshold tuning, or model selection.
- The PlantVillage result does not establish field generalization.

## 5. AgriSight Integration Status

- Tomato disease model adapter implemented.
- Adapter tests cover confident tomato predictions, non-tomato top predictions, low confidence, and inference errors.
- Integration tests cover confident and uncertain results through the existing vision service.
- The full backend suite passed: 181 tests, with one non-fatal Starlette/AnyIO deprecation warning.
- The heuristic remains the default model.
- API response and database schema remain unchanged.

## 6. Recommendations

1. Seek authoritative documentation mapping the field dataset's annotation IDs to disease categories.
2. Preserve the field test split.
3. Conduct a properly labeled field evaluation once the mapping and protocol are verified.
4. Investigate potential domain shift and uncertainty behavior without tuning against the held-out test split.
5. Review integration requirements with the team before changing the default model, API contract, or database schema.

## 7. Conclusion

The classifier performs strongly on the sampled PlantVillage images but shows a substantial change in prediction behavior on the 31 field images evaluated. Inference execution was successful, but field disease-class accuracy remains unknown.

**Recommendation:** retain the heuristic as AgriSight's default vision model until field evaluation, uncertainty handling, and integration requirements have been reviewed and agreed upon by the team.
