import { useMemo, useEffect, useState, useRef } from 'react';
import '../styles/AdminDashboard.css'; // Optional: for styling
import { Line } from 'react-chartjs-2';
import { Chart, registerables } from 'chart.js';
Chart.register(...registerables);

const RANGE_OPTS = [
  { key: '7d',   label: 'Last 7 Days',   days: 7 },
  { key: '30d',  label: 'Last 30 Days',  days: 30 },
  { key: '90d',  label: 'Last 90 Days',  days: 90 },
  { key: '1y',   label: 'Last Year',     days: 365 },
];


// Parse "YYYY-MM-DD" (or Date) as a LOCAL date (no TZ shift)
function parseYMDLocal(val) {
  if (val instanceof Date) return new Date(val.getFullYear(), val.getMonth(), val.getDate());
  if (typeof val === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(val)) {
    const [y, m, d] = val.split('-').map(Number);
    return new Date(y, m - 1, d); // local
  }
  // Fallback: try Date then normalize to local start of day
  const d = new Date(val);
  return new Date(d.getFullYear(), d.getMonth(), d.getDate());
}

function startOfDayLocal(d) {
  const dd = parseYMDLocal(d);
  dd.setHours(0, 0, 0, 0);
  return dd;
}

function dayDiff(a, b) {
  const A = startOfDayLocal(a);
  const B = startOfDayLocal(b);
  const msPerDay = 24 * 60 * 60 * 1000;
  return Math.round((A - B) / msPerDay);
}



function filterChartDataByRange(chartData, rangeKey) {
  if (!chartData || !chartData.labels?.length) return chartData;

  const range = RANGE_OPTS.find(r => r.key === rangeKey) ?? RANGE_OPTS[RANGE_OPTS.length - 1];

  const labelsAsDates = chartData.labels.map(l => parseYMDLocal(l));
  const latest = labelsAsDates.reduce((a, b) => (a > b ? a : b), labelsAsDates[0] || new Date());
  const cutoff = new Date(latest);
  cutoff.setDate(cutoff.getDate() - range.days + 1);

  const keepIdx = labelsAsDates.map((d, i) => (d >= cutoff ? i : -1)).filter(i => i !== -1);

  return {
    ...chartData,
    labels: keepIdx.map(i => chartData.labels[i]),
    datasets: (chartData.datasets || []).map(ds => ({
      ...ds,
      data: keepIdx.map(i => ds.data[i]),
    })),
  };
}



export default function StatGraphCard({ title, options = [], initialKey, defaultRangeKey = '1y', yStepSmall = false}) {
  const [selectedKey, setSelectedKey] = useState(initialKey ?? (options[0]?.key ?? ''));
  const [rangeKey, setRangeKey] = useState(defaultRangeKey);

    const [tipOpen, setTipOpen] = useState(false);
    const tipRef = useRef(null);
    const tipBtnRef = useRef(null);

    useEffect(() => {
        function onDocClick(e) {
            if (!tipOpen) return;
            if (
                tipRef.current &&
                !tipRef.current.contains(e.target) &&
                tipBtnRef.current &&
                !tipBtnRef.current.contains(e.target)
            ) {
                setTipOpen(false);
            }
        }
        function onEsc(e) {
            if (e.key === 'Escape') setTipOpen(false);
        }
        document.addEventListener('mousedown', onDocClick);
        document.addEventListener('keydown', onEsc);
        return () => {
            document.removeEventListener('mousedown', onDocClick);
            document.removeEventListener('keydown', onEsc);
        };
    }, [tipOpen]);

  const selected = useMemo(
    () => options.find(o => o.key === selectedKey) ?? options[0],
    [options, selectedKey]
  );

  // Detect if a y_total axis is present (only when you add an overlay total dataset)
    const hasTotalAxis = useMemo(
      () => (selected?.overlayTotal && (selected?.data?.datasets ?? []).some(ds => ds.yAxisID === 'y_total')),
      [selected]
    );

    const statDescription =
        selected?.description ||
        'This stat shows time-series values for the selected metric.';


  const rangedData = useMemo(
    () => filterChartDataByRange(selected?.data, rangeKey),
    [selected, rangeKey]
  );

  const yTicks = yStepSmall
  ? {
      stepSize: 0.01,
      // Optional: avoid too many ticks; tweak as needed
      maxTicksLimit: 100,
      // Format to 2 decimals
      callback: (v) => Number(v).toFixed(8),
    }
  : {
      precision: 0,
      stepSize: 1,
    };

  const chartOptions = useMemo(() => {
      const firstLabel = rangedData?.labels?.[0];

      return {
        maintainAspectRatio: false,
        scales: {
          x: {
            stacked: !!selected?.stacked,   // ← turn on stacking when the option requests it
            ticks: {
              autoSkip: false,
              maxRotation: 0,
              callback: (val, idx) => {
                const raw = rangedData?.labels?.[idx];
                if (!raw) return '';
                const d = parseYMDLocal(raw);

                if (rangeKey === '7d') {
                  return new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric' }).format(d);
                }
                const diff = dayDiff(d, parseYMDLocal(firstLabel));
                return diff % 7 === 0
                  ? new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric' }).format(d)
                  : '';
              }
            }
          },
          y: {
            stacked: !!selected?.stacked,   // ← stack y for stacked views
            ticks: yTicks,
          },
          ...(hasTotalAxis ? {
            y_total: {
              position: 'right',
              stacked: false,
              grid: { drawOnChartArea: false },
              ticks: yTicks,
            }
          } : {})
        },
        plugins: {
          legend: { display: true },
          tooltip: {
            mode: 'index',
            intersect: false,
          }
        }
      };
    }, [rangeKey, rangedData, selected, hasTotalAxis]);




    return (
        <div className="stat-card-graph">
          <div className="statgraph-header">
            <h3 className="statgraph-title">{title}</h3>

            <div className="statgraph-controls">
              <div className="statgraph-control">
                <div className="statgraph-control statgraph-control--with-tip">
                    <label htmlFor="stat-select">Viewing Stat:</label>
                    <select
                        id="stat-select"
                        value={selectedKey}
                        onChange={e => setSelectedKey(e.target.value)}
                    >
                        {options.map(o => (
                            <option key={o.key} value={o.key}>{o.label}</option>
                        ))}
                    </select>

                    <div
                        className={`rz-tooltip ${tipOpen ? 'rz-tooltip--open' : ''}`}
                        onMouseEnter={() => setTipOpen(true)}
                        onMouseLeave={() => setTipOpen(false)}
                    >
                        <button
                            type="button"
                            className="rz-tooltip__icon"
                            aria-label="Stat description"
                            aria-expanded={tipOpen}
                            aria-controls="stat-desc-tooltip"
                            onClick={() => setTipOpen(prev => !prev)}
                            ref={tipBtnRef}
                        >
                            ?
                        </button>

                        <div
                            id="stat-desc-tooltip"
                            role="tooltip"
                            className="rz-tooltip__panel"
                            ref={tipRef}
                        >
                            <div className="rz-tooltip__content">
                                {statDescription}
                            </div>
                            <div className="rz-tooltip__arrow" />
                        </div>
                    </div>
                </div>

              </div>

              <div className="statgraph-control">
                <label htmlFor="range-select">Range:</label>
                <select
                  id="range-select"
                  value={rangeKey}
                  onChange={e => setRangeKey(e.target.value)}
                >
                  {RANGE_OPTS.map(r => (
                    <option key={r.key} value={r.key}>{r.label}</option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          <div className="chart-container">
              <Line data={rangedData ?? { labels: [], datasets: [] }} options={chartOptions} />
          </div>
        </div>
      );
}
