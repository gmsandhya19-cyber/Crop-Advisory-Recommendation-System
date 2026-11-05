# Database

This folder contains the database schema and generated SQLite database file.

## Files

- `schema.sql` creates the project tables.
- `crop_advisor.sqlite3` is generated automatically when the backend starts.

## Tables

### `advisories`

Stores numeric crop advisory predictions from Random Forest/SVM:

- crop
- stage
- soil
- moisture
- rain
- temperature
- prediction
- readiness
- model votes
- created timestamp

### `image_analyses`

Stores backend image API results:

- label
- confidence
- model
- advice
- created timestamp

## Reset Database

Stop the backend, delete `crop_advisor.sqlite3`, then run:

```powershell
cd ..\backend
python app.py
```

The backend recreates the database from `schema.sql`.
