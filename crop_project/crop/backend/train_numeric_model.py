import argparse
import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC


BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent
DEFAULT_DATASET = PROJECT_ROOT / "numierc dataset" / "Crop_recommendation.csv"
MODEL_DIR = BACKEND_DIR / "models"
FEATURE_COLUMNS = ["N", "P", "K", "temperature", "humidity", "ph", "rainfall"]
TARGET_COLUMN = "label"


def load_dataset(path):
    dataset = pd.read_csv(path)
    missing_columns = [column for column in FEATURE_COLUMNS + [TARGET_COLUMN] if column not in dataset.columns]

    if missing_columns:
        raise ValueError(f"Dataset is missing columns: {', '.join(missing_columns)}")

    return dataset.dropna(subset=FEATURE_COLUMNS + [TARGET_COLUMN])


def build_model(algorithm):
    if algorithm == "random_forest":
        return RandomForestClassifier(
            n_estimators=250,
            max_depth=None,
            min_samples_split=2,
            random_state=42,
            n_jobs=1,
        )

    if algorithm == "svm":
        return Pipeline(
            steps=[
                ("scaler", StandardScaler()),
                ("classifier", SVC(kernel="rbf", C=10, gamma="scale", probability=True, random_state=42)),
            ]
        )

    raise ValueError("algorithm must be random_forest or svm")


def train_model(dataset, algorithm):
    features = dataset[FEATURE_COLUMNS]
    target = dataset[TARGET_COLUMN]

    x_train, x_test, y_train, y_test = train_test_split(
        features,
        target,
        test_size=0.2,
        random_state=42,
        stratify=target,
    )

    model = build_model(algorithm)
    model.fit(x_train, y_train)

    predictions = model.predict(x_test)
    accuracy = accuracy_score(y_test, predictions)
    report = classification_report(y_test, predictions, output_dict=True)

    return model, {
        "algorithm": algorithm,
        "datasetRows": int(len(dataset)),
        "trainRows": int(len(x_train)),
        "testRows": int(len(x_test)),
        "features": FEATURE_COLUMNS,
        "target": TARGET_COLUMN,
        "accuracy": round(float(accuracy), 4),
        "classificationReport": report,
    }


def save_artifacts(model, metrics, algorithm):
    MODEL_DIR.mkdir(exist_ok=True)
    model_path = MODEL_DIR / f"crop_{algorithm}.joblib"
    metrics_path = MODEL_DIR / f"crop_{algorithm}_metrics.json"

    joblib.dump(
        {
            "model": model,
            "features": FEATURE_COLUMNS,
            "target": TARGET_COLUMN,
            "algorithm": algorithm,
        },
        model_path,
    )
    metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    return model_path, metrics_path


def parse_args():
    parser = argparse.ArgumentParser(description="Train crop recommendation numeric models.")
    parser.add_argument("--dataset", default=str(DEFAULT_DATASET), help="Path to Crop_recommendation.csv")
    parser.add_argument(
        "--algorithm",
        choices=["random_forest", "svm", "both"],
        default="both",
        help="Model algorithm to train.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    dataset_path = Path(args.dataset)
    dataset = load_dataset(dataset_path)
    algorithms = ["random_forest", "svm"] if args.algorithm == "both" else [args.algorithm]

    print(f"Loaded dataset: {dataset_path}")
    print(f"Rows: {len(dataset)}")

    for algorithm in algorithms:
        model, metrics = train_model(dataset, algorithm)
        model_path, metrics_path = save_artifacts(model, metrics, algorithm)
        print(f"{algorithm}: accuracy={metrics['accuracy']}")
        print(f"Saved model: {model_path}")
        print(f"Saved metrics: {metrics_path}")


if __name__ == "__main__":
    main()
