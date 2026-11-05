# Frontend

This folder contains the browser interface for the crop advisory system.

## Files

- `index.html` defines the page structure.
- `styles.css` contains the responsive UI styling.
- `script.js` handles form input, local image enhancement, API calls, and rendering results.

## Features

- Crop-condition input form.
- Random Forest/SVM advisory request through `POST /api/advisory`.
- Image upload with brightness, contrast, sharpness, and saturation controls.
- CNN image API request through `POST /api/image-analysis`.
- Download button for the enhanced crop image.

## Run

Do not open `index.html` directly if you want backend API features. Start the Python server instead:

```powershell
cd ..\backend
python app.py
```

Then open:

```text
http://localhost:3000
```

The backend serves this folder automatically.

If you open `index.html` directly from the filesystem, keep the backend running at `http://localhost:3000`; `script.js` uses that address for API calls in file mode.
