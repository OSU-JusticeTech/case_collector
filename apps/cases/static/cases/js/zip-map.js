const ZIP_GEOJSON_URL = "/static/cases/ZipCodes_FC.geojson";
const ZIP_COLORS = ["#deebf7", "#9ecae1", "#6baed6", "#3182bd", "#08519c"];
const ZIP_NO_CASES_COLOR = "#f1f5f9";

let zipMap;
let zipGeoJson;
let zipLayer;
let zipLegend;
let zipMapData = [];

function normalizeZipCode(value) {
    const digits = String(value ?? "").replace(/\D/g, "");
    return digits.length >= 5 ? digits.slice(0, 5) : digits.padStart(5, "0");
}

function initializeZipMap(data) {
    const select = document.getElementById("zip-map-year");
    const status = document.getElementById("zip-map-status");

    zipMapData = data;
    select.replaceChildren();

    if (!data.length) {
        select.add(new Option("No data available", ""));
        select.disabled = true;
        status.textContent = "No ZIP code case data is available.";
        return;
    }

    [...data].reverse().forEach(yearData => {
        select.add(new Option(yearData.year, yearData.year));
    });

    select.value = String(data[data.length - 1].year);
    select.disabled = false;
    select.addEventListener("change", renderZipMap);

    zipMap = L.map("zip-map").setView([40.08, -82.73], 10);

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        referrerPolicy: "strict-origin-when-cross-origin",
        attribution: "&copy; OpenStreetMap contributors"
    }).addTo(zipMap);

    status.textContent = "Loading ZIP code boundaries...";
    fetch(ZIP_GEOJSON_URL)
        .then(response => {
            if (!response.ok) {
                throw new Error(`Failed to load ZIP code boundaries: HTTP ${response.status}`);
            }
            return response.json();
        })
        .then(geojson => {
            if (!geojson || !Array.isArray(geojson.features)) {
                throw new Error("ZIP code boundary data is not a valid GeoJSON feature collection.");
            }

            zipGeoJson = geojson;
            renderZipMap();
        })
        .catch(error => {
            console.error(error);
            status.textContent = "Could not load ZIP code boundaries.";
        });
}

function renderZipMap() {
    if (!zipMap || !zipGeoJson) return;

    const year = Number(document.getElementById("zip-map-year").value);
    const yearData = zipMapData.find(item => item.year === year);
    const counts = new Map(
        (yearData?.zips ?? []).map(item => [
            normalizeZipCode(item.zip_code),
            Number(item.total) || 0
        ])
    );
    const maxCount = Math.max(0, ...counts.values());

    if (zipLayer) zipMap.removeLayer(zipLayer);
    if (zipLegend) zipMap.removeControl(zipLegend);

    zipLayer = L.geoJSON(zipGeoJson, {
        style: feature => {
            const count = counts.get(normalizeZipCode(feature.properties["Zip Code"])) ?? 0;
            const colorIndex = maxCount > 0 && count > 0
                ? Math.min(ZIP_COLORS.length - 1, Math.ceil(count / maxCount * ZIP_COLORS.length) - 1)
                : -1;

            return {
                fillColor: colorIndex < 0 ? ZIP_NO_CASES_COLOR : ZIP_COLORS[colorIndex],
                fillOpacity: 0.8,
                color: "#475569",
                weight: 1
            };
        },
        onEachFeature: (feature, layer) => {
            const properties = feature.properties;
            const zipCode = properties["Zip Code"];
            const count = counts.get(normalizeZipCode(zipCode)) ?? 0;
            const popup = document.createElement("div");
            const title = document.createElement("strong");
            const detail = document.createElement("div");

            title.textContent = `ZIP ${zipCode}`;
            detail.textContent = `${count.toLocaleString()} cases in ${year}`;
            popup.append(title, detail);
            layer.bindPopup(popup);
        }
    }).addTo(zipMap);

    zipLegend = L.control({ position: "bottomright" });
    zipLegend.onAdd = () => {
        const container = L.DomUtil.create("div", "zip-map-legend");
        const title = document.createElement("div");
        const zeroCases = document.createElement("div");
        const zeroSwatch = document.createElement("span");
        const zeroLabel = document.createElement("span");
        const scale = document.createElement("div");
        const labels = document.createElement("div");
        const low = document.createElement("span");
        const high = document.createElement("span");

        title.textContent = `Cases in ${year}`;
        zeroCases.className = "zero-cases";
        zeroSwatch.className = "zero-swatch";
        zeroLabel.textContent = "No cases";
        zeroCases.append(zeroSwatch, zeroLabel);
        scale.className = "color-scale";
        labels.className = "scale-labels";
        low.textContent = maxCount > 0 ? "1" : "0";
        high.textContent = maxCount.toLocaleString();
        labels.append(low, high);
        container.append(title, zeroCases, scale, labels);
        return container;
    };
    zipLegend.addTo(zipMap);

    if (zipLayer.getBounds().isValid()) {
        zipMap.fitBounds(zipLayer.getBounds());
    }

    document.getElementById("zip-map-status").textContent =
        `${counts.size.toLocaleString()} ZIP codes with case data`;
}
