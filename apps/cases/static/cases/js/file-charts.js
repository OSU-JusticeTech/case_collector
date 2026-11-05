const chartColors = {
    primary: "#2563EB",
    secondary: "#94A3B8",
    text: "#334155",
    grid: "#E2E8F0",
    background: "#FFFFFF"
};

Chart.register(ChartDataLabels);

const chartFont = {
    family: "'Inter', 'Segoe UI', Arial, sans-serif",
    size: 12
};

const chartDefaults = {
    responsive: true,
    maintainAspectRatio: false,
    font: chartFont,
    color: chartColors.text,
};

let dailyEventsPromise = null;

function loadDailyEvents() {
    if (!dailyEventsPromise) {
        dailyEventsPromise = fetch("/api/daily-events/")
            .then(response => {
                if (!response.ok) {
                    throw new Error(`API request failed: ${response.status}`);
                }

                return response.json();
            })
            .catch(error => {
                dailyEventsPromise = null;
                throw error;
            });
    }

    return dailyEventsPromise;
}

const formatNumber = value =>
    Number(value).toLocaleString("en-US");


const metrics = [
  "cases_filed",
  "writs_issued",
  "setouts_processed",
  "setouts_completed"
];

function getRollingComparison(data, endDate = new Date()) {
  const end = new Date(endDate);
  const currentStart = new Date(end);
  currentStart.setFullYear(currentStart.getFullYear() - 1);

  const previousEnd = new Date(currentStart);
  const previousStart = new Date(previousEnd);
  previousStart.setFullYear(previousStart.getFullYear() - 1);

	const formatDate = date => date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric"
  });

  document.getElementById("trend-label").textContent =
    `Current Period: ${formatDate(currentStart)} – ${formatDate(end)} | ` +
    `Previous Period: ${formatDate(previousStart)} – ${formatDate(previousEnd)}`;
  function aggregate(startDate, endDate) {
    const totals = Object.fromEntries(
      metrics.map(metric => [metric, 0])
    );

    data.forEach(item => {
      const date = item.date;

      const start = startDate.toISOString().slice(0, 10);
      const end = endDate.toISOString().slice(0, 10);

      if (date >= start && date < end) {
        metrics.forEach(metric => {
          totals[metric] += Number(item[metric] || 0);
        });
      }
    });

    return totals;
  }

  const current = aggregate(currentStart, end);
  const previous = aggregate(previousStart, currentStart);

  const comparison = {};

  metrics.forEach(metric => {
    const currentValue = current[metric];
    const previousValue = previous[metric];

    comparison[metric] = {
      current: currentValue,
      previous: previousValue,
      difference: currentValue - previousValue,
      percentChange: previousValue === 0
        ? null
        : ((currentValue - previousValue) / previousValue) * 100
    };
  });

  return {
    current_period: {
      start_date: currentStart.toISOString().slice(0, 10),
      end_date: end.toISOString().slice(0, 10),
      totals: current
    },
    previous_period: {
      start_date: previousStart.toISOString().slice(0, 10),
      end_date: previousEnd.toISOString().slice(0, 10),
      totals: previous
    },
    comparison
  };
}

 async function createRollingChart() {

    const data = await loadDailyEvents();

    const results = getRollingComparison(data);


    const metrics = [
        { key: "cases_filed", label: "Cases Filed" },
        { key: "writs_issued", label: "Writs Issued" },
        { key: "setouts_processed", label: "Setouts Processed" },
        { key: "setouts_completed", label: "Setouts Completed" }
    ];

    const previousData = metrics.map(
        m => results.comparison[m.key].previous
    );

    const currentData = metrics.map(
        m => results.comparison[m.key].current
    );

    const percentChanges = metrics.map(
        m => results.comparison[m.key].percentChange
    );

    const formatPercent = value => {
        if (value === null) return "N/A";

        return `${value > 0 ? "+" : ""}${value.toFixed(1)}%`;
    };

    const ctx = document
        .getElementById("comparisonChart")
        .getContext("2d");

    new Chart(ctx, {
        type: "bar",

        data: {
            labels: metrics.map(m => m.label),

            datasets: [
                {
                    label: "Previous 12 Months",
                    data: previousData,
                    backgroundColor: chartColors.secondary,
                    borderRadius: 4,
                    borderSkipped: false,
                    categoryPercentage: 0.7,
                    barPercentage: 0.85
                },
                {
                    label: "Current 12 Months",
                    data: currentData,
                    backgroundColor: chartColors.primary,
                    borderRadius: 4,
                    borderSkipped: false,
                    categoryPercentage: 0.7,
                    barPercentage: 0.85
                }
            ]
        },

        options: {
            ...chartDefaults,

            layout: {
                padding: {
                    top: 30
                }
            },

            plugins: {
    legend: {
        position: "top",
        labels: {
            font: chartFont,
            color: chartColors.text,
            usePointStyle: true,
            pointStyle: "rectRounded",
            padding: 16
        }
    },

    datalabels: {
        display: true,
        anchor: "end",
        align: "top",
        offset: 3,
        clamp: true,
        color: chartColors.text,

        font: {
            family: chartFont.family,
            weight: "600",
            size: 11
        },

        formatter: value => formatNumber(value)
    },

    tooltip: {
        callbacks: {
            afterBody: context => {
                const index = context[0].dataIndex;

                return `Year-over-year change: ${
                    formatPercent(percentChanges[index])
                }`;
            }
        }
    }
},

            scales: {

                x: {
                    title: {
                        display: false
                    }
                },

                y: {
                    title: {
                        display: true,
                        text: "Total Count",
                        font: {
                            ...chartFont,
                            weight: "600"
                        }
                    },
                    grace: "15%"
                }
            }
        }
    });

    const formatDate = date =>
        date.toLocaleDateString("en-US", {
            month: "short",
            day: "numeric",
            year: "numeric",
            timeZone: "UTC"
        });

    document.getElementById("trend-label").textContent =
        `Current: ${formatDate(new Date(results.current_period.start_date + "T00:00:00Z"))} – ${formatDate(new Date(results.current_period.end_date + "T00:00:00Z"))} | ` +
        `Previous: ${formatDate(new Date(results.previous_period.start_date + "T00:00:00Z"))} – ${formatDate(new Date(results.previous_period.end_date + "T00:00:00Z"))}`;
}

async function createCasesFiledChart() {

    const events = await loadDailyEvents();

    const monthlyTotals = {};

    events.forEach(event => {

        const date = new Date(event.date + "T00:00:00Z");

        if (date.getUTCFullYear() < 2000) return;

        const year = date.getUTCFullYear();
        const month = date.getUTCMonth();

        if (!monthlyTotals[year]) {
            monthlyTotals[year] = Array(12).fill(0);
        }

        monthlyTotals[year][month] += Number(event.cases_filed || 0);
    });

    const years = Object.keys(monthlyTotals)
        .map(Number)
        .sort((a, b) => b - a)
        .slice(0, 7);

    const yearColors = [
        "#2563EB",
        "#3B82F6",
        "#60A5FA",
        "#93C5FD",
        "#A5B4FC",
        "#CBD5E1",
        "#94A3B8"
    ];

    const datasets = years.map((year, index) => {

        return {
            label: String(year),

            data: monthlyTotals[year],

            backgroundColor: yearColors[index],
            borderColor: yearColors[index],

            borderWidth: 1,
            borderRadius: 3,
            borderSkipped: false,

            barPercentage: 0.9,
            categoryPercentage: 0.85
        };
    });

    const ctx = document
        .getElementById("casesFiledChart")
        .getContext("2d");

    new Chart(ctx, {

        type: "bar",

        data: {
            labels: [
                "Jan", "Feb", "Mar", "Apr",
                "May", "Jun", "Jul", "Aug",
                "Sep", "Oct", "Nov", "Dec"
            ],

            datasets
        },

        options: {

            ...chartDefaults,

            interaction: {
                mode: "index",
                intersect: false
            },

            plugins: {

								datalabels: {
        display: false
    },
                legend: {
                    position: "right",
                    reverse: true
                },

                tooltip: {
                    callbacks: {
                        label: context =>
                            `${context.dataset.label}: ${formatNumber(context.parsed.y)} cases`
                    }
                }
            },

            scales: {


                x: {
                    stacked: false,
                    title: {
                        display: true,
                        text: "Month"
                    }
                },

                y: {
                    title: {
                        display: true,
                        text: "Cases Filed"
                    }
                }
            }
        }
    });
}