import argparse
import csv
from collections import Counter
from pathlib import Path


def safe_divide(numerator, denominator):
    return numerator / denominator if denominator else 0.0


def evaluate(rows):
    labels = sorted({
        label
        for row in rows
        for label in (row["true_label"], row["predicted_label"])
    })

    matrix = {actual: {pred: 0 for pred in labels} for actual in labels}

    for row in rows:
        matrix[row["true_label"]][row["predicted_label"]] += 1

    total = len(rows)
    correct = sum(
        row["true_label"] == row["predicted_label"] for row in rows
    )

    results = []
    for label in labels:
        tp = matrix[label][label]
        actual_count = sum(matrix[label].values())
        predicted_count = sum(matrix[actual].get(label, 0) for actual in labels)

        precision = safe_divide(tp, predicted_count)
        recall = safe_divide(tp, actual_count)
        f1 = safe_divide(2 * precision * recall, precision + recall)

        results.append({
            "class": label,
            "support": actual_count,
            "precision": precision,
            "recall": recall,
            "f1_score": f1,
        })

    macro_f1 = safe_divide(
        sum(item["f1_score"] for item in results), len(results)
    )

    return labels, matrix, results, safe_divide(correct, total), macro_f1


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate labeled tomato disease predictions from a CSV."
    )
    parser.add_argument(
        "--input",
        required=True,
        help="CSV with true_label and predicted_label columns",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    report_dir = Path(__file__).parent / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)

    with input_path.open("r", newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)

        required = {"true_label", "predicted_label"}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise SystemExit(
                "CSV must contain columns: true_label,predicted_label"
            )

        rows = []
        for line_number, row in enumerate(reader, start=2):
            true_label = (row.get("true_label") or "").strip()
            predicted_label = (row.get("predicted_label") or "").strip()

            if not true_label or not predicted_label:
                raise SystemExit(
                    f"Missing label on CSV line {line_number}"
                )

            rows.append({
                "true_label": true_label,
                "predicted_label": predicted_label,
            })

    if not rows:
        raise SystemExit("The input CSV has no prediction rows.")

    labels, matrix, results, accuracy, macro_f1 = evaluate(rows)

    report_lines = [
        "AgriSight Tomato Disease Classifier Evaluation",
        f"Samples evaluated: {len(rows)}",
        f"Accuracy: {accuracy:.4f}",
        f"Macro F1-score: {macro_f1:.4f}",
        "",
        "Per-class metrics:",
        "Class | Support | Precision | Recall | F1-score",
    ]

    for item in results:
        report_lines.append(
            f'{item["class"]} | {item["support"]} | '
            f'{item["precision"]:.4f} | {item["recall"]:.4f} | '
            f'{item["f1_score"]:.4f}'
        )

    report_lines.extend([
        "",
        "Confusion matrix (rows = actual, columns = predicted):",
        "Actual/Predicted | " + " | ".join(labels),
    ])

    for actual in labels:
        report_lines.append(
            actual + " | " + " | ".join(
                str(matrix[actual][predicted]) for predicted in labels
            )
        )

    report_path = report_dir / "evaluation_report.txt"
    report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    matrix_path = report_dir / "confusion_matrix.csv"
    with matrix_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["actual/predicted"] + labels)
        for actual in labels:
            writer.writerow(
                [actual] + [matrix[actual][predicted] for predicted in labels]
            )

    print("\n".join(report_lines))
    print(f"\nReport saved to: {report_path}")
    print(f"Confusion matrix saved to: {matrix_path}")


if __name__ == "__main__":
    main()
