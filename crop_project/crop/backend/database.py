import json
import sqlite3
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATABASE_DIR = PROJECT_ROOT / "database"
SCHEMA_PATH = DATABASE_DIR / "schema.sql"
DB_PATH = DATABASE_DIR / "crop_advisor.sqlite3"


def get_connection():
    DATABASE_DIR.mkdir(exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    with get_connection() as connection:
        connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))


def save_advisory(inputs, advisory):
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO advisories (
              crop, stage, soil, moisture, rain, temperature,
              prediction, readiness, model_votes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                inputs.get("crop", "rice"),
                inputs.get("stage", "vegetative"),
                inputs.get("soil", "loamy"),
                inputs.get("moisture", "moderate"),
                inputs.get("rain", "none"),
                inputs.get("temperature", "normal"),
                advisory["prediction"],
                advisory["readiness"],
                json.dumps(advisory.get("modelVotes", [])),
            ),
        )


def save_image_analysis(result):
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO image_analyses (label, confidence, model, advice)
            VALUES (?, ?, ?, ?)
            """,
            (
                result["label"],
                result["confidence"],
                result["model"],
                result["advice"],
            ),
        )
