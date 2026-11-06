
const API_URL = "/api/zip-counts/";

let reportData = [];
let historyChart = null;

const MONTHS = [
    "January", "February", "March", "April",
    "May", "June", "July", "August",
    "September", "October", "November", "December"
];

async function loadReport() {

    try {

        const response = await fetch(API_URL);

        if (!response.ok) {
            throw new Error(`HTTP error: ${response.status}`);
        }

        reportData = await response.json();

        initializeReport();


    } catch (error) {
        console.error(error);
    }
}

// Initialize report

function initializeReport() {
    const currentYear = new Date().getFullYear();

    // Render the three annual ranking tables
    renderTopZips(currentYear);

    initializeZipMap(reportData);

    // Populate ZIP dropdown, sorted by total cases
    populateZipFilter();

    document.getElementById("zip-filter")
        .addEventListener("change", renderZipHistory);
}


// Get the latest three calendar years

function renderTopZips(currentYear) {
    const container = document.getElementById("year-tables");

    container.innerHTML = "";

    const targetYears = [
        currentYear - 2,
        currentYear - 1,
        currentYear
    ];

    container.className = "year-grid";

    targetYears.forEach(year => {
        const yearData = reportData.find(
            item => item.year === year
        );

        const section = document.createElement("div");
        section.className = "year-column";

        const heading = document.createElement("h3");
        heading.textContent = year;

        section.appendChild(heading);

        const wrapper = document.createElement("div");
        wrapper.className = "table-wrapper";

        const table = document.createElement("table");

        table.innerHTML = `
            <thead>
                <tr>
                    <th>#</th>
                    <th>ZIP</th>
                    <th>Cases</th>
                </tr>
            </thead>
            <tbody></tbody>
        `;

        const tbody = table.querySelector("tbody");

        if (yearData) {
            const topZips = [...yearData.zips]
                .sort((a, b) => b.total - a.total)
                .slice(0, 20);

            topZips.forEach((zip, index) => {
                const row = document.createElement("tr");

                [
                    index + 1,
                    zip.zip_code,
                    zip.total.toLocaleString()
                ].forEach((value, cellIndex) => {
                    const cell = document.createElement("td");
                    cell.textContent = value;

                    if (cellIndex === 2) {
                        cell.classList.add("case-count");
                    }

                    row.appendChild(cell);
                });

                tbody.appendChild(row);
            });
        } else {
            const row = document.createElement("tr");
            const cell = document.createElement("td");

            cell.colSpan = 3;
            cell.textContent = "No data available";

            row.appendChild(cell);
            tbody.appendChild(row);
        }

        wrapper.appendChild(table);
        section.appendChild(wrapper);
        container.appendChild(section);
    });
}


// Populate ZIP codes


function populateZipFilter() {
    const select = document.getElementById("zip-filter");

    const totals = {};

    reportData.forEach(yearData => {
        yearData.zips.forEach(zip => {
            totals[zip.zip_code] =
                (totals[zip.zip_code] || 0) + zip.total;
        });
    });

    const sortedZips = Object.entries(totals)
        .sort((a, b) => b[1] - a[1]);

    select.innerHTML = "";

    sortedZips.forEach(([zip, total]) => {
        select.add(new Option(
            `${zip} — ${total.toLocaleString()} cases`,
            zip
        ));
    });

    // Automatically select the ZIP with the most cases
    if (sortedZips.length > 0) {
        select.value = sortedZips[0][0];
        renderZipHistory();
    }
}



// Populate available years
function populateYearFilter() {
    const select = document.getElementById("history-year");

    const years = reportData
        .map(item => item.year)
        .sort((a, b) => a - b);

    years.forEach(year => {
        select.add(new Option(year, year));
    });
}

// Retrieve monthly data for a ZIP code
function getZipMonthlyHistory(zipCode) {
    const yearMap = {};

    reportData.forEach(yearData => {
        const zip = yearData.zips.find(
            item => item.zip_code === zipCode
        );

        yearMap[yearData.year] = zip
            ? zip.months
            : Array(12).fill(0);
    });

    const years = reportData
        .map(item => item.year)
        .sort((a, b) => a - b);

    if (!years.length) return [];

    const history = [];

    // Generate every month between the first and last year
    const currentYear = new Date().getFullYear();

		const firstYear = Math.max(2000, years[0]);
		const lastYear = Math.min(currentYear, years[years.length - 1]);

		for (let year = firstYear; year <= lastYear; year++) {
				const months = yearMap[year] || Array(12).fill(0);

				for (let month = 0; month < 12; month++) {
						history.push({
								year,
								month,
								label: `${MONTHS[month]} ${year}`,
								cases: months[month] ?? 0
						});
				}
		}

    return history;
}

// Render monthly chart and statistics


function renderZipHistory() {
    const zipCode = document.getElementById("zip-filter").value;

    if (!zipCode) return;

    const history = getZipMonthlyHistory(zipCode);

    // History is now a flat array of monthly records
    const allMonthlyValues = history.map(item =>
        Number(item.cases) || 0
    );

    const total = allMonthlyValues.reduce(
        (sum, value) => sum + value, 0
    );

    const peak = allMonthlyValues.length
        ? Math.max(...allMonthlyValues)
        : 0;

    const average = allMonthlyValues.length
        ? total / allMonthlyValues.length
        : 0;

    document.getElementById("zip-total").textContent =
        total.toLocaleString();

    document.getElementById("zip-peak").textContent =
        peak.toLocaleString();

    document.getElementById("zip-average").textContent =
        average.toFixed(1);

    renderMonthlyChart(zipCode, history);
}



// Draw monthly chart
function renderMonthlyChart(zipCode, history) {
    const ctx = document.getElementById("zip-history-chart");

    document.getElementById("reset-zoom")
    .onclick = () => historyChart.resetZoom();

    if (historyChart) {
        historyChart.destroy();
    }

    const labels = history.map(item => item.label);
    const values = history.map(item => item.cases);

    historyChart = new Chart(ctx, {
        type: "line",

        data: {
            labels: labels,

            datasets: [{
                label: `ZIP ${zipCode} - Monthly Cases`,
                data: values,
                borderColor: "#245b85",
                backgroundColor: "rgba(36, 91, 133, 0.10)",
                borderWidth: 2,
                pointRadius: 1.5,
                pointHoverRadius: 5,
                fill: true,
                tension: 0.2
            }]
        },

        options: {
            responsive: true,
            maintainAspectRatio: false,

            interaction: {
                mode: "index",
                intersect: false
            },

            plugins: {
            		datalabels: {
										display: false
								},
                title: {
                    display: true,
                    text: `Monthly Case History - ZIP ${zipCode}`
                },

                legend: {
                    display: false
                },

                zoom: {
										pan: {
												enabled: true,
												mode: "x"
										},
										zoom: {
												wheel: {
														enabled: true
												},
												pinch: {
														enabled: true
												},
												drag: {
														enabled: true
												},
												mode: "x"
										}
								},

                tooltip: {
                    callbacks: {
                        label: context =>
                            `${context.parsed.y} cases`
                    }
                }
            },

            scales: {
                x: {
                    type: "category",

                    ticks: {
                        autoSkip: true,
                        maxTicksLimit: 20,
                        maxRotation: 45,
                        minRotation: 0
                    },

                    title: {
                        display: true,
                        text: "Month and Year"
                    }
                },

                y: {
                    beginAtZero: true,

                    ticks: {
                        precision: 0
                    },

                    title: {
                        display: true,
                        text: "Number of Cases"
                    }
                }
            }
        }
    });
}
