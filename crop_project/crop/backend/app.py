import base64
import json
import mimetypes
import os
import urllib.error
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from database import initialize_database, save_advisory, save_image_analysis


BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"
DATABASE_DIR = PROJECT_ROOT / "database"
MODEL_DIR = BACKEND_DIR / "models"


def load_env_file():
    env_path = BACKEND_DIR / ".env"

    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.strip().startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


load_env_file()

PORT = int(os.environ.get("PORT", "3000"))
HOST = os.environ.get("HOST", "localhost")
NUMERIC_MODEL = os.environ.get("NUMERIC_MODEL", "ensemble").lower()
CNN_MODEL_PATH = Path(os.environ.get("CNN_MODEL_PATH", MODEL_DIR / "crop_cnn.keras"))
IMAGE_API_PROVIDER = os.environ.get("IMAGE_API_PROVIDER", "gemini").lower()
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct")

CROPS = ["rice", "wheat", "maize", "cotton", "tomato"]
STAGES = ["vegetative", "flowering", "fruiting", "harvest"]
SOILS = ["loamy", "clay", "sandy", "black", "red"]
MOISTURE = ["low", "moderate", "high"]
RAIN = ["none", "light", "heavy"]
TEMPERATURE = ["cool", "normal", "hot"]

RF_MODEL = None
SVM_MODEL = None
CNN_MODEL = None
ML_STATUS = {
    "random_forest": "not loaded",
    "svm": "not loaded",
    "image_api": "not configured",
}


def one_hot(value, choices):
    return [1 if value == choice else 0 for choice in choices]


def encode_numeric_features(inputs):
    return (
        one_hot(inputs.get("crop", "rice"), CROPS)
        + one_hot(inputs.get("stage", "vegetative"), STAGES)
        + one_hot(inputs.get("soil", "loamy"), SOILS)
        + one_hot(inputs.get("moisture", "moderate"), MOISTURE)
        + one_hot(inputs.get("rain", "none"), RAIN)
        + one_hot(inputs.get("temperature", "normal"), TEMPERATURE)
    )


def rule_label(inputs):
    readiness = 82

    if inputs.get("moisture") in {"low", "high"}:
        readiness -= 12
    if inputs.get("rain") == "heavy":
        readiness -= 18
    if inputs.get("temperature") == "hot":
        readiness -= 10
    if inputs.get("stage") in {"flowering", "fruiting"}:
        readiness += 5
    if inputs.get("rain") == "none" and inputs.get("moisture") == "moderate":
        readiness += 4

    readiness = max(35, min(96, readiness))

    if readiness >= 78:
        return "normal", readiness
    if inputs.get("moisture") == "low" or inputs.get("temperature") == "hot":
        return "dry_stress", readiness
    if inputs.get("rain") == "heavy" or inputs.get("moisture") == "high":
        return "water_risk", readiness

    return "crop_damage_risk", readiness


def build_synthetic_training_data():
    features = []
    labels = []

    for crop in CROPS:
        for stage in STAGES:
            for soil in SOILS:
                for moisture in MOISTURE:
                    for rain in RAIN:
                        for temperature in TEMPERATURE:
                            sample = {
                                "crop": crop,
                                "stage": stage,
                                "soil": soil,
                                "moisture": moisture,
                                "rain": rain,
                                "temperature": temperature,
                            }
                            label, _ = rule_label(sample)
                            features.append(encode_numeric_features(sample))
                            labels.append(label)

    return features, labels


def load_numeric_models():
    global RF_MODEL, SVM_MODEL

    try:
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.svm import SVC

        features, labels = build_synthetic_training_data()

        RF_MODEL = RandomForestClassifier(n_estimators=120, random_state=7)
        RF_MODEL.fit(features, labels)
        ML_STATUS["random_forest"] = "trained from local crop rules"

        SVM_MODEL = SVC(kernel="rbf", probability=True, random_state=7)
        SVM_MODEL.fit(features, labels)
        ML_STATUS["svm"] = "trained from local crop rules"
    except Exception as error:
        ML_STATUS["random_forest"] = f"unavailable: {error}"
        ML_STATUS["svm"] = f"unavailable: {error}"


def load_image_api():
    if IMAGE_API_PROVIDER == "gemini":
        ML_STATUS["image_api"] = f"ready: gemini/{GEMINI_MODEL}" if GEMINI_API_KEY else "missing GEMINI_API_KEY"
        return

    if IMAGE_API_PROVIDER == "groq":
        ML_STATUS["image_api"] = f"ready: groq/{GROQ_MODEL}" if GROQ_API_KEY else "missing GROQ_API_KEY"
        return

    ML_STATUS["image_api"] = "set IMAGE_API_PROVIDER to gemini or groq"


def predict_numeric(inputs):
    features = [encode_numeric_features(inputs)]
    fallback_label, fallback_readiness = rule_label(inputs)
    votes = []

    if RF_MODEL is not None and NUMERIC_MODEL in {"random_forest", "ensemble"}:
        votes.append(("random_forest", str(RF_MODEL.predict(features)[0])))

    if SVM_MODEL is not None and NUMERIC_MODEL in {"svm", "ensemble"}:
        votes.append(("svm", str(SVM_MODEL.predict(features)[0])))

    if not votes:
        return fallback_label, fallback_readiness, [{"model": "rules", "prediction": fallback_label}]

    counts = {}
    for _, label in votes:
        counts[label] = counts.get(label, 0) + 1

    label = max(counts, key=counts.get)
    return label, fallback_readiness, [
        {"model": model_name, "prediction": prediction} for model_name, prediction in votes
    ]


def advisory_for_prediction(inputs, label, readiness, model_votes):
    crop = inputs.get("crop", "rice").title()
    title_map = {
        "normal": f"{crop} advisory: normal conditions",
        "dry_stress": f"{crop} advisory: dry stress risk",
        "water_risk": f"{crop} advisory: waterlogging risk",
        "crop_damage_risk": f"{crop} advisory: crop damage risk",
    }
    recommendation_map = {
        "normal": [
            ["Water", "Maintain the current irrigation interval and verify soil moisture before the next watering."],
            ["Nutrients", "Continue balanced nutrition according to the crop stage and avoid heavy unscheduled doses."],
            ["Scouting", "Inspect leaves twice a week and record any pest or disease changes."],
            ["Weather", "Routine field work can continue if rain and heat conditions stay stable."],
            ["Model", f"Numeric prediction used {', '.join(v['model'] for v in model_votes)}."],
        ],
        "dry_stress": [
            ["Water", "Check root-zone moisture and irrigate within 24 hours if the field is dry."],
            ["Heat", "Move spraying and fertilizer work to cooler morning hours."],
            ["Soil", "Use shorter, more frequent irrigation on sandy soil to reduce water loss."],
            ["Scouting", "Look for leaf curling, yellowing, and edge drying before symptoms spread."],
            ["Model", f"Numeric prediction used {', '.join(v['model'] for v in model_votes)}."],
        ],
        "water_risk": [
            ["Drainage", "Hold irrigation and clear drainage channels before adding fertilizer."],
            ["Roots", "Inspect low field areas for waterlogging and root stress."],
            ["Disease", "Increase scouting after humid or heavy-rain periods."],
            ["Nutrients", "Postpone fertilizer if runoff risk is high."],
            ["Model", f"Numeric prediction used {', '.join(v['model'] for v in model_votes)}."],
        ],
        "crop_damage_risk": [
            ["Scouting", "Inspect tender shoots and leaf undersides for pests or disease marks."],
            ["Photo", "Capture close leaf images if symptoms are visible and compare with recent field records."],
            ["Water", "Avoid sudden moisture swings while the crop is stressed."],
            ["Nutrients", "Keep potassium and micronutrients steady during flowering or fruiting."],
            ["Model", f"Numeric prediction used {', '.join(v['model'] for v in model_votes)}."],
        ],
    }

    return {
        "title": title_map[label],
        "readiness": readiness,
        "prediction": label,
        "modelVotes": model_votes,
        "recommendations": recommendation_map[label],
    }


def parse_data_url(value):
    if "," in value:
        _, value = value.split(",", 1)
    return base64.b64decode(value)


def split_data_url(value):
    if "," not in value:
        return "image/png", value

    header, data = value.split(",", 1)
    mime_type = header.removeprefix("data:").split(";", 1)[0] or "image/png"
    return mime_type, data


def image_prompt():
    return (
        "Analyze this crop or plant field image for agricultural advisory use. "
        "Return only JSON with keys: label, confidence, advice. "
        "label must be one of normal, dry_stress, water_risk, pest_or_disease_risk, "
        "crop_damage_risk, image_needs_review. confidence must be a number from 0 to 1. "
        "advice must be one practical sentence for a farmer."
    )


def post_json(url, payload, headers, timeout=45):
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Vision API request failed ({error.code}): {detail}") from error


def extract_json_object(text):
    text = text.strip()

    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].strip()

    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1 or end < start:
        raise ValueError(f"Vision API returned non-JSON text: {text[:160]}")

    return json.loads(text[start : end + 1])


def normalize_image_result(raw, model_name):
    label = str(raw.get("label", "image_needs_review")).strip().lower()
    confidence = raw.get("confidence", 0.0)
    advice = str(raw.get("advice", "Review the crop photo manually before acting.")).strip()

    try:
        confidence = max(0.0, min(1.0, float(confidence)))
    except (TypeError, ValueError):
        confidence = 0.0

    return {
        "label": label,
        "confidence": round(confidence, 4),
        "model": model_name,
        "advice": advice,
    }


def gemini_image_analysis(image_data):
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not set in backend/.env.")

    mime_type, base64_image = split_data_url(image_data)
    payload = {
        "model": GEMINI_MODEL,
        "input": [
            {"type": "text", "text": image_prompt()},
            {"type": "image", "data": base64_image, "mime_type": mime_type},
        ],
    }
    response = post_json(
        "https://generativelanguage.googleapis.com/v1beta/interactions",
        payload,
        {"x-goog-api-key": GEMINI_API_KEY},
    )
    text = response.get("output_text", "")

    if not text:
        candidates = response.get("candidates", [])
        parts = candidates[0].get("content", {}).get("parts", []) if candidates else []
        text = "".join(part.get("text", "") for part in parts)

    return normalize_image_result(extract_json_object(text), f"gemini/{GEMINI_MODEL}")


def groq_image_analysis(image_data):
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not set in backend/.env.")

    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": image_prompt()},
                    {"type": "image_url", "image_url": {"url": image_data}},
                ],
            }
        ],
        "temperature": 0.2,
        "max_completion_tokens": 500,
        "response_format": {"type": "json_object"},
    }
    response = post_json(
        "https://api.groq.com/openai/v1/chat/completions",
        payload,
        {"Authorization": f"Bearer {GROQ_API_KEY}"},
    )
    text = response["choices"][0]["message"]["content"]
    return normalize_image_result(extract_json_object(text), f"groq/{GROQ_MODEL}")


def fallback_image_analysis(image_data):
    size_kb = len(parse_data_url(image_data)) / 1024
    label = "image_received" if size_kb > 5 else "image_too_small"
    return {
        "label": label,
        "confidence": 0.0,
        "model": "local-fallback",
        "advice": "Vision API key is not configured. Add GEMINI_API_KEY or GROQ_API_KEY in backend/.env.",
    }


def predict_image(payload):
    image_data = payload.get("image")

    if not image_data:
        raise ValueError("image is required as a base64 data URL.")

    if IMAGE_API_PROVIDER == "gemini" and GEMINI_API_KEY:
        return gemini_image_analysis(image_data)

    if IMAGE_API_PROVIDER == "groq" and GROQ_API_KEY:
        return groq_image_analysis(image_data)

    return fallback_image_analysis(image_data)


class CropAdvisorHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(FRONTEND_DIR), **kwargs)

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()

    def send_json(self, status_code, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_json(self):
        content_length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(content_length).decode("utf-8")
        return json.loads(body or "{}")

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()

    def do_GET(self):
        if self.path == "/api/status":
            self.send_json(200, {"status": ML_STATUS, "numericModel": NUMERIC_MODEL})
            return

        super().do_GET()

    def do_POST(self):
        try:
            if self.path == "/api/advisory":
                inputs = self.read_json()
                label, readiness, model_votes = predict_numeric(inputs)
                advisory = advisory_for_prediction(inputs, label, readiness, model_votes)
                save_advisory(inputs, advisory)
                self.send_json(200, {"advisory": advisory})
                return

            if self.path == "/api/image-analysis":
                result = predict_image(self.read_json())
                save_image_analysis(result)
                self.send_json(200, {"image": result})
                return

            self.send_error(404)
        except Exception as error:
            self.send_json(500, {"error": str(error)})

    def guess_type(self, path):
        if path.endswith(".js"):
            return "text/javascript; charset=utf-8"

        return mimetypes.guess_type(path)[0] or "application/octet-stream"


if __name__ == "__main__":
    MODEL_DIR.mkdir(exist_ok=True)
    DATABASE_DIR.mkdir(exist_ok=True)
    initialize_database()
    load_numeric_models()
    load_image_api()

    server = ThreadingHTTPServer((HOST, PORT), CropAdvisorHandler)
    print(f"CropAdvisor ML backend running at http://{HOST}:{PORT}")
    print(json.dumps(ML_STATUS, indent=2))
    server.serve_forever()
