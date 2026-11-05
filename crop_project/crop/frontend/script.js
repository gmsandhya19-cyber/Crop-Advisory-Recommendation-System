const cropProfiles = {
  rice: {
    title: "Rice advisory",
    nutrient:
      "Maintain nitrogen in split doses and monitor zinc deficiency in younger leaves.",
    pest: "Scout for stem borer and leaf folder, especially after humid or cloudy weather.",
  },
  wheat: {
    title: "Wheat advisory",
    nutrient:
      "Prioritize balanced nitrogen and potassium during tillering and grain filling.",
    pest: "Check for rust symptoms and aphids on the underside of leaves.",
  },
  maize: {
    title: "Maize advisory",
    nutrient: "Apply nitrogen near the root zone and avoid late stress during tasseling.",
    pest:
      "Scout whorl leaves for fall armyworm damage and remove severely affected leaves.",
  },
  cotton: {
    title: "Cotton advisory",
    nutrient: "Support square and boll development with potassium-rich nutrition.",
    pest: "Use yellow sticky traps and inspect tender shoots for sucking pests.",
  },
  tomato: {
    title: "Tomato advisory",
    nutrient: "Keep calcium and potassium supply steady to reduce fruit disorders.",
    pest: "Watch for fruit borer, leaf miner, and early blight after humid spells.",
  },
};

const stageAdvice = {
  vegetative: "Encourage canopy growth, remove weeds early, and avoid crop stress.",
  flowering: "Keep moisture steady during flowering to protect yield formation.",
  fruiting: "Reduce water swings and support grain or fruit filling with balanced nutrition.",
  harvest: "Limit irrigation, avoid late sprays, and prepare for clean harvesting.",
};

const form = document.querySelector("#advisoryForm");
const list = document.querySelector("#advisoryList");
const title = document.querySelector("#recommendationTitle");
const score = document.querySelector("#readinessScore");
const meter = document.querySelector("#readinessMeter");
const modelStatus = document.querySelector("#modelStatus");
const imageInput = document.querySelector("#cropImage");
const dropZone = document.querySelector(".drop-zone");
const previewPanel = document.querySelector(".preview-panel");
const canvas = document.querySelector("#imageCanvas");
const resetImageButton = document.querySelector("#resetImage");
const downloadImageButton = document.querySelector("#downloadImage");
const imageStatus = document.querySelector("#imageStatus");
const imageMetrics = document.querySelector("#imageMetrics");
const imageAdvice = document.querySelector("#imageAdvice");
const imageControls = {
  brightness: document.querySelector("#brightness"),
  contrast: document.querySelector("#contrast"),
  sharpness: document.querySelector("#sharpness"),
  saturation: document.querySelector("#saturation"),
};

const defaultImageSettings = {
  brightness: 105,
  contrast: 115,
  sharpness: 35,
  saturation: 112,
};

let activeImage = null;

function getApiBaseUrl() {
  if (window.location.protocol === "file:") {
    return "http://localhost:3000";
  }

  return window.location.origin;
}

const API_BASE_URL = getApiBaseUrl();

function apiUrl(path) {
  return `${API_BASE_URL}${path}`;
}

function getVisionApiResult() {
  return document.querySelector("#visionApiResult");
}

function getIrrigationAdvice(moisture, rain, soil) {
  if (rain === "heavy") {
    return "Avoid irrigation and clear drainage channels before rainfall. Postpone fertilizer until runoff risk drops.";
  }

  if (moisture === "low") {
    return soil === "sandy"
      ? "Irrigate in shorter, more frequent cycles because sandy soil loses water quickly."
      : "Schedule irrigation within 24 hours and check root-zone moisture after watering.";
  }

  if (moisture === "high") {
    return "Hold irrigation, inspect for waterlogging, and improve field drainage where needed.";
  }

  return "Maintain the current irrigation interval and verify moisture before the next watering.";
}

function getWeatherAdvice(rain, temperature) {
  if (temperature === "hot") {
    return "Plan field operations for early morning and avoid spraying during peak heat.";
  }

  if (temperature === "cool") {
    return "Expect slower crop growth and delay fertilizer if uptake conditions are poor.";
  }

  if (rain === "light") {
    return "Use the light rain window to reduce irrigation, but avoid spraying before showers.";
  }

  return "Weather conditions are suitable for routine field work and crop monitoring.";
}

function calculateReadiness({ moisture, rain, temperature, stage }) {
  let value = 82;

  if (moisture === "low" || moisture === "high") value -= 12;
  if (rain === "heavy") value -= 18;
  if (temperature === "hot") value -= 10;
  if (stage === "flowering" || stage === "fruiting") value += 5;
  if (rain === "none" && moisture === "moderate") value += 4;

  return Math.max(35, Math.min(96, value));
}

function buildLocalAdvisory(data) {
  const crop = cropProfiles[data.crop];
  const readiness = calculateReadiness(data);

  return {
    title: crop.title,
    readiness,
    recommendations: [
    ["Water", getIrrigationAdvice(data.moisture, data.rain, data.soil)],
    ["Nutrients", crop.nutrient],
    ["Stage", stageAdvice[data.stage]],
    ["Pest", crop.pest],
    ["Weather", getWeatherAdvice(data.rain, data.temperature)],
    ],
  };
}

function renderAdvisory(advisory = buildLocalAdvisory(getFormData())) {
  title.textContent = advisory.title;
  score.textContent = `${advisory.readiness}%`;
  meter.value = advisory.readiness;
  meter.textContent = `${advisory.readiness}%`;

  list.innerHTML = advisory.recommendations
    .map(
      ([heading, text]) => `
        <article class="advisory-item">
          <span class="advisory-icon">${heading.slice(0, 1)}</span>
          <div>
            <h3>${heading}</h3>
            <p>${text}</p>
          </div>
        </article>
      `
    )
    .join("");
}

function getFormData() {
  return Object.fromEntries(new FormData(form).entries());
}

async function requestModelAdvisory(data) {
  const response = await fetch(apiUrl("/api/advisory"), {
    method: "POST",
    body: JSON.stringify(data),
  });

  const result = await response.json();

  if (!response.ok) {
    throw new Error(result.error || "ML model request failed.");
  }

  return result.advisory;
}

async function requestVisionImageAnalysis() {
  if (!activeImage) return null;

  const response = await fetch(apiUrl("/api/image-analysis"), {
    method: "POST",
    body: JSON.stringify({
      image: canvas.toDataURL("image/png"),
    }),
  });

  const result = await response.json();

  if (!response.ok) {
    throw new Error(result.error || "Vision API image request failed.");
  }

  return result.image;
}

async function syncBackendStatus() {
  try {
    const response = await fetch(apiUrl("/api/status"));
    const result = await response.json();

    if (!response.ok) {
      throw new Error(result.error || "Backend status unavailable.");
    }

    const status = result.status || {};
    modelStatus.textContent = `Backend connected. RF: ${status.random_forest}. SVM: ${status.svm}.`;

    const visionApiResult = getVisionApiResult();
    if (visionApiResult && status.image_api) {
      visionApiResult.textContent = status.image_api;
    }
  } catch (error) {
    modelStatus.textContent =
      "Backend offline. Start backend/app.py and open http://localhost:3000.";
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = getFormData();
  const submitButton = form.querySelector('button[type="submit"]');

  submitButton.disabled = true;
  submitButton.textContent = "Predicting...";
  modelStatus.textContent = "Running Random Forest and SVM numeric models...";

  try {
    const advisory = await requestModelAdvisory(data);
    renderAdvisory(advisory);
    const votes = advisory.modelVotes
      ? advisory.modelVotes.map((vote) => `${vote.model}: ${vote.prediction}`).join(", ")
      : "model prediction complete";
    modelStatus.textContent = `ML recommendation generated (${votes}).`;
  } catch (error) {
    renderAdvisory(buildLocalAdvisory(data));
    modelStatus.textContent = `${error.message} Showing local rule-based advice.`;
  } finally {
    submitButton.disabled = false;
    submitButton.textContent = "Get recommendation";
  }
});

form.addEventListener("change", () => {
  renderAdvisory();
  modelStatus.textContent = "Inputs changed. Submit again for Random Forest/SVM prediction.";
});
renderAdvisory();
syncBackendStatus();

function getImageSettings() {
  return Object.fromEntries(
    Object.entries(imageControls).map(([name, control]) => [
      name,
      Number(control.value),
    ])
  );
}

function fitImageToCanvas(image) {
  const maxWidth = 960;
  const maxHeight = 640;
  const scale = Math.min(
    maxWidth / image.naturalWidth,
    maxHeight / image.naturalHeight,
    1
  );

  canvas.width = Math.max(1, Math.round(image.naturalWidth * scale));
  canvas.height = Math.max(1, Math.round(image.naturalHeight * scale));
}

function drawActiveImage() {
  if (!activeImage) return;

  const context = canvas.getContext("2d", { willReadFrequently: true });
  const settings = getImageSettings();

  fitImageToCanvas(activeImage);
  context.clearRect(0, 0, canvas.width, canvas.height);
  context.filter = `brightness(${settings.brightness}%) contrast(${settings.contrast}%) saturate(${settings.saturation}%)`;
  context.drawImage(activeImage, 0, 0, canvas.width, canvas.height);
  context.filter = "none";

  if (settings.sharpness > 0) {
    applySharpness(context, canvas.width, canvas.height, settings.sharpness / 100);
  }

  updateImageAnalysis(context);
}

async function syncVisionImageAnalysis() {
  if (!activeImage) return;

  const visionApiResult = getVisionApiResult();
  visionApiResult.textContent = "Checking...";

  try {
    const result = await requestVisionImageAnalysis();
    if (!result) return;

    if (result.model !== "local-fallback") {
      imageStatus.textContent = `Vision API: ${result.label}`;
      visionApiResult.textContent = `${result.label} ${Math.round(result.confidence * 100)}%`;
      imageAdvice.textContent = `${result.advice} Confidence: ${Math.round(result.confidence * 100)}%.`;
    } else {
      visionApiResult.textContent = "Fallback";
      imageAdvice.textContent = result.advice;
    }
  } catch (error) {
    visionApiResult.textContent = "Offline";
    imageAdvice.textContent = `${error.message} Showing browser image metrics.`;
  }
}

function applySharpness(context, width, height, amount) {
  const source = context.getImageData(0, 0, width, height);
  const output = context.createImageData(width, height);
  const input = source.data;
  const result = output.data;
  const center = 1 + 4 * amount;
  const side = -amount;

  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      const index = (y * width + x) * 4;

      for (let channel = 0; channel < 3; channel += 1) {
        const current = input[index + channel] * center;
        const left = x > 0 ? input[index - 4 + channel] * side : 0;
        const right = x < width - 1 ? input[index + 4 + channel] * side : 0;
        const top = y > 0 ? input[index - width * 4 + channel] * side : 0;
        const bottom =
          y < height - 1 ? input[index + width * 4 + channel] * side : 0;

        result[index + channel] = Math.max(
          0,
          Math.min(255, current + left + right + top + bottom)
        );
      }

      result[index + 3] = input[index + 3];
    }
  }

  context.putImageData(output, 0, 0);
}

function updateImageAnalysis(context) {
  const data = context.getImageData(0, 0, canvas.width, canvas.height).data;
  let brightnessTotal = 0;
  let greenDominance = 0;
  let yellowDryness = 0;
  let edgeTotal = 0;
  let sampleCount = 0;

  for (let index = 0; index < data.length; index += 16) {
    const red = data[index];
    const green = data[index + 1];
    const blue = data[index + 2];
    const brightness = (red + green + blue) / 3;

    brightnessTotal += brightness;
    greenDominance += Math.max(0, green - Math.max(red, blue));
    yellowDryness += Math.max(0, red + green - blue * 2);

    if (index + 20 < data.length) {
      edgeTotal += Math.abs(
        brightness -
          (data[index + 16] + data[index + 17] + data[index + 18]) / 3
      );
    }

    sampleCount += 1;
  }

  const exposure = Math.round((brightnessTotal / sampleCount / 255) * 100);
  const vegetation = Math.round(Math.min(100, (greenDominance / sampleCount / 70) * 100));
  const clarity = Math.round(Math.min(100, (edgeTotal / sampleCount / 28) * 100));
  const dryness = Math.round(Math.min(100, (yellowDryness / sampleCount / 170) * 100));
  const status = getPhotoStatus({ clarity, exposure, vegetation, dryness });
  const currentVisionResult = getVisionApiResult()?.textContent || "Waiting";

  imageStatus.textContent = status.title;
  imageAdvice.textContent = status.advice;
  imageMetrics.innerHTML = `
    <div><span>Clarity</span><strong>${clarity}%</strong></div>
    <div><span>Exposure</span><strong>${exposure}%</strong></div>
    <div><span>Vegetation signal</span><strong>${vegetation}%</strong></div>
    <div><span>Vision API</span><strong id="visionApiResult">${currentVisionResult}</strong></div>
  `;
}

function getPhotoStatus({ clarity, exposure, vegetation, dryness }) {
  if (dryness > 62 && vegetation < 45) {
    return {
      title: "Dry stress visible",
      advice:
        "Leaves or soil look dry. Check root-zone moisture before irrigation and retake a closer leaf photo if symptoms continue.",
    };
  }

  if (clarity < 22 || exposure < 24 || exposure > 82) {
    return {
      title: "Image needs review",
      advice:
        "The photo may be blurry or poorly exposed. Use natural light and keep the camera steady for better crop inspection.",
    };
  }

  if (vegetation < 28) {
    return {
      title: "Possible crop damage",
      advice:
        "The image has a weak green signal. Capture affected leaves close up and inspect for drying, pest damage, or disease marks.",
    };
  }

  return {
    title: "Normal crop photo",
    advice:
      "The photo is clear enough for sharing. Keep affected leaves centered when asking for pest or disease review.",
  };
}

function loadImageFile(file) {
  if (!file || !file.type.startsWith("image/")) return;

  const image = new Image();
  image.addEventListener("load", () => {
    activeImage = image;
    previewPanel.classList.add("has-image");
    downloadImageButton.disabled = false;
    drawActiveImage();
    syncVisionImageAnalysis();
    URL.revokeObjectURL(image.src);
  });
  image.src = URL.createObjectURL(file);
}

function resetImageSettings() {
  Object.entries(defaultImageSettings).forEach(([name, value]) => {
    imageControls[name].value = value;
  });
  drawActiveImage();
}

imageInput.addEventListener("change", (event) => {
  loadImageFile(event.target.files[0]);
});

dropZone.addEventListener("dragover", (event) => {
  event.preventDefault();
  dropZone.classList.add("is-dragging");
});

dropZone.addEventListener("dragleave", () => {
  dropZone.classList.remove("is-dragging");
});

dropZone.addEventListener("drop", (event) => {
  event.preventDefault();
  dropZone.classList.remove("is-dragging");
  loadImageFile(event.dataTransfer.files[0]);
});

Object.values(imageControls).forEach((control) => {
  control.addEventListener("input", drawActiveImage);
});

resetImageButton.addEventListener("click", resetImageSettings);

downloadImageButton.addEventListener("click", () => {
  if (!activeImage) return;

  const link = document.createElement("a");
  link.download = "enhanced-crop-image.png";
  link.href = canvas.toDataURL("image/png");
  link.click();
});
