
    // API endpoint returning the available years
    const YEARS_URL = "/api/hexgrids/";

    // Initialize map
    const map = L.map("hex-map").setView([40.08, -82.73], 11);

    L.tileLayer(
        "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
        {
            referrerPolicy: 'strict-origin-when-cross-origin',
            attribution: "&copy; OpenStreetMap contributors"
        }
    ).addTo(map);

    let hexLayer = null;


    function getOpacity(value, maxValue) {
				if (maxValue === 0) return 0;

				return Math.max(0, Math.min(1, value / maxValue));
		}

    // Create/update legend
    function updateLegend(minValue, maxValue) {
        const legend = L.control({ position: "bottomright" });

        legend.onAdd = function () {
            const div = L.DomUtil.create("div", "legend");

            div.innerHTML = `
                <div class="legend-title">Count</div>

                <div class="colorbar"></div>

                <div class="legend-labels">
                    <span>${minValue}</span>
                    <span>${maxValue}</span>
                </div>
            `;

            return div;
        };

        return legend;
    }

    let currentLegend = null;

    // Fetch GeoJSON for selected year
    async function loadYear(url) {
        const status = document.getElementById("status");

        status.textContent = "Loading hexgrid...";

        try {
            const response = await fetch(url);

            if (!response.ok) {
                throw new Error("Failed to load GeoJSON");
            }

            const geojson = await response.json();

            // Remove previous hexgrid
            if (hexLayer) {
                map.removeLayer(hexLayer);
            }

            if (currentLegend) {
                map.removeControl(currentLegend);
            }

            // Find count range
            const counts = geojson.features.map(
                feature => Number(feature.properties.count) || 0
            );

            const minCount = Math.min(...counts);
            const maxCount = Math.max(...counts);
            const totalCount = counts.reduce((sum, count) => sum + count, 0);

            // Render hexagons
            hexLayer = L.geoJSON(geojson, {

                style: function(feature) {
										const count = Number(feature.properties.count) || 0;

										return {
												fillColor: "#2166ac",
												fillOpacity: getOpacity(count, maxCount),
												color: "#555",
												weight: 0
										};
								},

                onEachFeature: function(feature, layer) {
                    const properties = feature.properties;

                    layer.bindPopup(`
                        <b>Count:</b> ${properties.count}<br>
                        <b>i:</b> ${properties.i}<br>
                        <b>j:</b> ${properties.j}
                    `);

                    layer.on({
                        mouseover: function(e) {
                            e.target.setStyle({
                                weight: 2,
                                color: "#222",
                                fillOpacity: 0.95
                            });
                        },

                        mouseout: function(e) {
                            hexLayer.resetStyle(e.target);
                        }
                    });
                }

            }).addTo(map);

            // Zoom to hexgrid
            if (hexLayer.getBounds().isValid()) {
                map.fitBounds(hexLayer.getBounds());
            }

            // Add updated legend
            currentLegend = updateLegend(minCount, maxCount);
            currentLegend.addTo(map);

            status.textContent =
                `${totalCount} cases loaded`;

        } catch (error) {
            console.error(error);
            status.textContent = "Error loading data";
        }
    }

    // Fetch available years
    async function loadYears() {
        try {
            const response = await fetch(YEARS_URL);

            if (!response.ok) {
                throw new Error("Failed to load years");
            }

            const data = await response.json();

            const select = document.getElementById("mapyearSelect");

            select.innerHTML = "";

            // Populate dropdown
            data.results.reverse().forEach(item => {
                const option = document.createElement("option");

                option.value = item.url;
                option.textContent = item.year;

                select.appendChild(option);
            });

            // Load first available year
            if (data.results.length > 0) {
                loadYear(data.results[0].url);
            }

            // Load selected year on dropdown change
            select.addEventListener("change", function() {
                loadYear(this.value);
            });

        } catch (error) {
            console.error(error);
            document.getElementById("status").textContent =
                "Could not load available years";
        }
    }

    // Start application
