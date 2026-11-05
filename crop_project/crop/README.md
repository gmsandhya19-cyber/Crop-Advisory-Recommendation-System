# Crop Advisory Recommendation System

A crop advisory web app with a browser frontend, Python ML backend, and SQLite database storage.

The system supports:

- Numeric crop-condition prediction using Random Forest and SVM.
- Image upload and enhancement in the browser.
- Backend image analysis through Gemini or Groq vision APIs.
- SQLite storage for numeric advisories and image analysis results.

## Project Structure

```text
viyu/
  frontend/
    index.html
    styles.css
    script.js
    README.md
  backend/
    app.py
    database.py
    requirements.txt
    .env.example
    README.md
  database/
    schema.sql
    README.md
```

## Requirements

- Python 3.10 or newer
- pip

Install backend dependencies:

```powershell
cd backend
pip install -r requirements.txt
```

## Environment

Copy the example environment file:

```powershell
cd backend
Copy-Item .env.example .env
```

Default values:

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

`NUMERIC_MODEL` can be:

- `ensemble`
- `random_forest`
- `svm`

## Run

From the backend folder:

```powershell
python app.py
```

Or from the project root on Windows:

```powershell
.\run_project.bat
```

Open:

```text
http://localhost:3000
```

The backend serves the files from `frontend/` and the frontend calls the backend API at the same host. If you open `frontend/index.html` directly, the frontend falls back to `http://localhost:3000` for API requests, so keep the backend running.

## API

### Status

```http
GET /api/status
```

Returns the Random Forest, SVM, and CNN loading status.

### Numeric Advisory

```http
POST /api/advisory
Content-Type: application/json
```

Example body:

```json
{
  "crop": "rice",
  "stage": "vegetative",
  "soil": "loamy",
  "moisture": "moderate",
  "rain": "none",
  "temperature": "normal"
}
```

This endpoint predicts with Random Forest/SVM and stores the result in SQLite.

### Image Analysis

```http
POST /api/image-analysis
Content-Type: application/json
```

Example body:

```json
{
  "image": "data:image/png;base64,..."
}
```

If `IMAGE_API_PROVIDER` is `gemini` or `groq` and the matching API key is configured, the endpoint runs vision analysis through that provider. Otherwise it returns a fallback response and still records the API call.

## Image API

Use Gemini:

```env
IMAGE_API_PROVIDER=gemini
GEMINI_API_KEY=your_key_here
```

Or use Groq:

```env
IMAGE_API_PROVIDER=groq
GROQ_API_KEY=your_key_here
```

## Database

The database schema lives in:

```text
database/schema.sql
```

When the backend starts, it creates:

```text
database/crop_advisor.sqlite3
```

Tables:

- `advisories`
- `image_analyses`

## Development Notes

- Keep frontend-only code in `frontend/`.
- Keep Python API and ML code in `backend/`.
- Keep schema, SQLite files, and future migrations in `database/`.
- Do not edit files inside `.venv/`; that folder contains installed dependencies.

## running commands

cd backend
python -m venv .venv
.\.venv\Scripts\Activate
pip install -r requirements.txt
python app.py