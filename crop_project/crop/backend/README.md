# Backend

This folder contains the Python API server, ML prediction logic, and database helper.

## Files

- `app.py` starts the HTTP server, serves the frontend, and exposes API endpoints.
- `database.py` initializes SQLite and saves prediction results.
- `requirements.txt` lists Python dependencies.
- `.env.example` shows supported environment settings.

## Setup

```powershell
pip install -r requirements.txt
Copy-Item .env.example .env
```

## Run

```powershell
python app.py
```

The server starts at:

```text
http://localhost:3000
```

## Environment

```env
PORT=3000
HOST=localhost
NUMERIC_MODEL=ensemble
IMAGE_API_PROVIDER=gemini
GEMINI_API_KEY=
GEMINI_MODEL=gemini-3.5-flash
GROQ_API_KEY=
GROQ_MODEL=meta-llama/llama-4-scout-17b-16e-instruct
```

`NUMERIC_MODEL` supports:

- `ensemble`
- `random_forest`
- `svm`

## Endpoints

### `GET /api/status`

Returns backend model status for Random Forest, SVM, and the configured image API.

### `POST /api/advisory`

Runs numeric prediction and stores the result in SQLite.

Required JSON fields:

- `crop`
- `stage`
- `soil`
- `moisture`
- `rain`
- `temperature`

### `POST /api/image-analysis`

Accepts a base64 image data URL:

```json
{
  "image": "data:image/png;base64,..."
}
```

The backend sends the image to Gemini or Groq when the matching API key is configured. If no key is configured, it returns a local fallback response.

## Model Notes

The numeric Random Forest and SVM models are trained at startup from local rule-generated crop condition samples. For a production system, replace this synthetic training source with real labeled crop data.

For image analysis, choose one provider in `backend/.env`:

```env
IMAGE_API_PROVIDER=gemini
GEMINI_API_KEY=your_key_here
```

or:

```env
IMAGE_API_PROVIDER=groq
GROQ_API_KEY=your_key_here
```

The frontend sends an enhanced PNG data URL to `POST /api/image-analysis`, and the backend normalizes the provider response into `label`, `confidence`, `model`, and `advice`.

## Train Numeric Dataset

The trainer expects the crop recommendation CSV at:

```text
../numierc dataset/Crop_recommendation.csv
```

Train both Random Forest and SVM:

```powershell
python train_numeric_model.py --algorithm both
```

Train only one model:

```powershell
python train_numeric_model.py --algorithm random_forest
python train_numeric_model.py --algorithm svm
```

Outputs are saved in `backend/models/`:

- `crop_random_forest.joblib`
- `crop_random_forest_metrics.json`
- `crop_svm.joblib`
- `crop_svm_metrics.json`
