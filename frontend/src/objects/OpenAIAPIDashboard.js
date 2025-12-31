import { useMemo, useState, useEffect } from 'react';
import StatGraphCard from '../objects/StatGraphCard';
import { useTheme } from '../hooks/ThemeContext';
import '../styles/AdminDashboard.css';
import { Chart, ArcElement, Tooltip, Legend } from 'chart.js';
import { Pie } from 'react-chartjs-2';
Chart.register(ArcElement, Tooltip, Legend);

function hexToRgba(hex, alpha = 1) {
  if (!hex) return `rgba(219, 58, 0, ${alpha})`; // Rezify orange fallback
  const c = hex.replace('#', '');
  const n = parseInt(c, 16);
  const r = (n >> 16) & 255;
  const g = (n >> 8) & 255;
  const b = n & 255;
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

function toSortedPairs(dailyObj) {
  return Object.keys(dailyObj)
    .sort((a, b) => new Date(a) - new Date(b))
    .map(d => [d, dailyObj[d]]);
}

function labelsFromPairs(pairs) {
  return pairs.map(([d]) => d);
}

// ========================= COLORFUL STACK HELPER (with labelMap) =========================

const COLOR_POOL = [
  '#FF6B6B', // coral red
  '#FFD93D', // golden yellow
  '#6BCB77', // green
  '#4D96FF', // blue
  '#9D4EDD', // purple
  '#FF914D', // orange
  '#00C49A', // teal
  '#FF66C4', // pink
  '#C77DFF', // lavender
  '#6E44FF', // deep violet
];

function pickColorForKey(key, primaryColor, idx) {

  const base = COLOR_POOL[idx % COLOR_POOL.length];
  return {
    bg: hexToRgba(base, 0.5),
    border: base,
  };
}

function buildStackedFromDaily({
  pairs,
  keys,
  primaryColor,
  addOverlayTotal = true,
  stackId = 'stack1',
  labelPrefix = '',
  labelMap = {},
}) {
  const labels = labelsFromPairs(pairs);

  const seriesDatasets = keys.map((key, i) => {
    const c = pickColorForKey(key, primaryColor, i);

    // Use friendly label if available, else fallback
    const displayName =
      labelMap[key] || `${labelPrefix}${key.replace(/_/g, ' ')}`;

    return {
      label: displayName,
      data: pairs.map(([, row]) => Number(row?.[key] ?? 0)),
      stack: stackId,
      fill: true,
      tension: 0.25,
      backgroundColor: c.bg,
      borderColor: c.border,
      pointBackgroundColor: c.bg,
      pointBorderColor: c.border,
      borderWidth: 2,
    };
  });

  const datasets = [...seriesDatasets];

  if (addOverlayTotal) {
    const total = labels.map((_, idx) =>
      keys.reduce((sum, key) => sum + Number(pairs[idx][1]?.[key] ?? 0), 0)
    );
    datasets.push({
      label: 'Total',
      data: total,
      type: 'line',
      yAxisID: 'y_total',
      fill: false,
      tension: 0.25,
      borderWidth: 2,
      borderColor: '#222',
      pointBackgroundColor: '#222',
      pointBorderColor: '#222',
    });
  }

  return { labels, datasets };
}


export default function OpenAIAPIDashboard({ admin, primaryColor }) {

    const [loadFails, setLoadFails] = useState([]);

    const [stats, setStats] = useState(null);
    const [loading, setLoading] = useState(true);
    const [errorMessage, setErrorMessage] = useState('');
    const [loadedData, setLoadedData] = useState([]);
    const [costObj, setCostObj] = useState({});

    const baseDatasetStyle = useMemo(() => ({
        fill: true,
        borderColor: primaryColor,
        backgroundColor: hexToRgba(primaryColor, 0.6),
        pointBackgroundColor: hexToRgba(primaryColor, 0.6),
        pointBorderColor: primaryColor,
        borderWidth: 2,
        tension: 0.1,
    }), [primaryColor]);

    // Image fallback component
    const ImageWithFailsafe = ({ logo, letter }) => {
        if (logo) {
          return (
            loadFails.includes(logo)
              ? <div className="list-fallback-logo">{letter}</div>
              : (
                <img
                  src={logo}
                  alt="Company Logo"
                  className="list-company-logo"
                  onLoad={() => {}}
                  onError={() => setLoadFails(prev => [...prev, logo])}
                />
              )
          );
        }
        return <div className="list-fallback-logo">{letter}</div>;
    };

    // Fetch admin + stats
      useEffect(() => {
        let isMounted = true;
        setLoading(true);

        fetch('/api/get_superadmin_openai_stats')
            .then(res => res.json())
            .then(data => {
                if (!isMounted) return;

                if (data.stats) {
                    setStats(data.stats);

                    // Set loadedData immediately from stats
                    if (data.stats.openai_historical) {
                        const sorted = Object.keys(data.stats.openai_historical)
                            .map(k => [k, data.stats.openai_historical[k]])
                            .sort((a, b) => new Date(a[0]) - new Date(b[0]));
                        setLoadedData(sorted);
                        setCostObj(data.stats.openai_historical);
                    }
                }

                if (data.error_message) setErrorMessage(data.error_message);
            })
            .finally(() => isMounted && setLoading(false));

        return () => { isMounted = false; };
    }, []);

    const labels = useMemo(() => loadedData.map(([date]) => date), [loadedData]);

    const avgMainSearchData = useMemo(() => ({
        labels,
        datasets: [{
          label: 'Avg Full Search Cost Per',
          data: loadedData.map(([, v]) => v.main_search_cost_pr),
          ...baseDatasetStyle,
        }],
    }), [labels, loadedData, baseDatasetStyle]);

    const avgMessageGenerationData = useMemo(() => ({
        labels,
        datasets: [{
          label: 'Avg Message Gen Cost Per',
          data: loadedData.map(([, v]) => v.message_generation_cost_pr),
          ...baseDatasetStyle,
        }],
    }), [labels, loadedData, baseDatasetStyle]);

    const avgAddTitleData = useMemo(() => ({
        labels,
        datasets: [{
          label: 'Avg Add Title Cost Per',
          data: loadedData.map(([, v]) => v.add_title_cost_pr),
          ...baseDatasetStyle,
        }],
    }), [labels, loadedData, baseDatasetStyle]);

    const avgRefreshData = useMemo(() => ({
        labels,
        datasets: [{
          label: 'Avg Refresh Cost Per',
          data: loadedData.map(([, v]) => v.refresh_cost_pr),
          ...baseDatasetStyle,
        }],
    }), [labels, loadedData, baseDatasetStyle]);

    const spendBreakdown = useMemo(() => {
        const elasticsearch_embeddings_cost = stats?.thirtyd_spend_breakdown?.elasticsearch_embeddings_cost ?? 0;
        const main_search_cost = stats?.thirtyd_spend_breakdown?.main_search_cost ?? 0;
        const message_generation_cost = stats?.thirtyd_spend_breakdown?.message_generation_cost ?? 0;
        const add_title_cost = stats?.thirtyd_spend_breakdown?.add_title_cost ?? 0;
        const refresh_cost = stats?.thirtyd_spend_breakdown?.refresh_cost ?? 0;

        // Use primaryColor and two alpha variants for a cohesive palette
        return {
            labels: ['Elasticsearch Embeddings', 'Full Search', 'Message Generation', 'Add Title', 'Refresh'],
            datasets: [{
                data: [elasticsearch_embeddings_cost, main_search_cost, message_generation_cost, add_title_cost, refresh_cost],
                backgroundColor: [
                    hexToRgba(primaryColor, 0.95),
                    hexToRgba(primaryColor, 0.75),
                    hexToRgba(primaryColor, 0.55),
                    hexToRgba(primaryColor, 0.35),
                    hexToRgba(primaryColor, 0.15)
                ],
                borderColor: [
                    hexToRgba(primaryColor, 1),
                    hexToRgba(primaryColor, 1),
                    hexToRgba(primaryColor, 1),
                    hexToRgba(primaryColor, 1),
                    hexToRgba(primaryColor, 1)
                ],
                borderWidth: 1
            }]
        };
    }, [stats, primaryColor]);

    const spendBreakdownOptions = useMemo(() => ({
        responsive: true,
        plugins: {
            legend: {
                position: 'bottom'
            },
            tooltip: {
                callbacks: {
                    label: (ctx) => {
                        const label = ctx.label || '';
                        const value = ctx.parsed || 0;
                        const total = ctx.dataset.data.reduce((a, b) => a + b, 0) || 1;
                        const pct = ((value / total) * 100).toFixed(1);
                        return `${label}: ${value} (${pct}%)`;
                    }
                }
            }
        }
    }), []);

    const dailyPairs = useMemo(() => toSortedPairs(costObj), [costObj]);

    const costKeys = [
      'elasticsearch_embeddings_cost',
      'main_search_cost',
      'message_generation_cost',
      'add_title_cost',
      'refresh_cost'
    ];

    const costLabelMap = {
      elasticsearch_embeddings_cost: 'Elasticsearch Embeddings',
      main_search_cost: 'Full Search',
      message_generation_cost: 'Linkedin Message Gen',
      add_title_cost: 'Add Title',
      refresh_cost: 'Refresh Jobs'
    };

    const costData = useMemo(() => buildStackedFromDaily({
      pairs: dailyPairs,
      keys: costKeys,
      primaryColor,
      addOverlayTotal: true,
      stackId: 'cost',
      labelMap: costLabelMap,
    }), [dailyPairs, primaryColor]);


    if (loading) {
        return (

            <div className="spinner-container">
                <div className="spinner-aw" />
            </div>

        );
      }


    return (
        <div className="main-dashboard">
              <h1 style={{ fontFamily: "'Orbitron', sans-serif", marginTop: 0 }}>
                <span style={{ color: 'black' }}>OpenAI API Cost Overview Dashboard:</span>{' '}
                <span style={{ color: 'var(--primary-color)' }}>
                  {admin.school_fullname}
                </span>
              </h1>

              <div className="grid">
                <StatCard title="Average Daily Spend (30d)" value={`$${(stats?.thirtyd_total_avg_spend ?? 0).toFixed(6)}`}
                    subvalue={`Total: $${((stats?.thirtyd_total_avg_spend ?? 0) * 30).toFixed(4)}`}/>
                <StatCard title="YTD Total Spend" value={`$${(stats?.ytd_total_spend ?? 0).toFixed(6)}`}/>
                <StatCard title="MTD Total Spend" value={`$${(stats?.mtd_total_spend ?? 0).toFixed(6)}`}/>
                <StatCard title="Last Month Total Spend" value={`$${(stats?.last_month_total_spend ?? 0).toFixed(6)}`}/>
              </div>

              <div className="grid">
                <StatCard title="Avg Daily Embedding Generation Cost (30d)" value={`$${(stats?.thirtyd_cost_prs?.elasticsearch_embeddings_cost_per_day ?? 0).toFixed(6)}`}/>
                <StatCard title="Full Search Function Avg Cost Per (30d)" value={`$${(stats?.thirtyd_cost_prs?.main_search_cost_pr ?? 0).toFixed(6)}`}
                    subvalue={`$${((stats?.thirtyd_cost_prs?.main_search_cost_pr ?? 0) * 1000).toFixed(4)} per 1000 `}/>
                <StatCard title="LinkedIn Message Generation Avg Cost Per (30d)" value={`$${(stats?.thirtyd_cost_prs?.message_generation_cost_pr ?? 0).toFixed(6)}`}
                subvalue={`$${((stats?.thirtyd_cost_prs?.message_generation_cost_pr ?? 0) * 1000).toFixed(4)} per 1000 `}/>
                <StatCard title="Add Title Function Avg Cost Per (30d)" value={`$${(stats?.thirtyd_cost_prs?.add_title_cost_pr ?? 0).toFixed(8)}`}
                    subvalue={`$${((stats?.thirtyd_cost_prs?.add_title_cost_pr ?? 0) * 1000).toFixed(4)} per 1000 `}/>
                <StatCard title="Refresh Jobs Function Avg Cost Per (30d)" value={`$${(stats?.thirtyd_cost_prs?.refresh_cost_pr ?? 0).toFixed(8)}`}
                subvalue={`$${((stats?.thirtyd_cost_prs?.refresh_cost_pr ?? 0) * 1000).toFixed(4)} per 1000 `}/>
              </div>

              <div className="grid" style={{ padding: '0 0.2rem' }}>
                <StatGraphCard
                  title="Cost Trends"
                  initialKey="cost"
                  defaultRangeKey="1y"
                  yStepSmall={true}
                  options={[
                    {
                      key: 'cost', label: 'API Cost (By Function)',
                      description:
                        'Daily Open AI API cost, broken down by function',
                      stacked: true, overlayTotal: true,
                      data: costData,
                    },
                    { key: 'main_search_cost_pr', label: 'Avg Full Search Cost Per', data: avgMainSearchData, description: 'The average cost per full search' },
                    { key: 'message_generation_cost_pr', label: 'Avg Message Gen Cost Per', data: avgMessageGenerationData, description: 'The average cost per linkedin message generation' },
                    { key: 'add_title_cost_pr', label: 'Avg Add Title Cost Per', data: avgAddTitleData, description: 'The average cost of the add title function' },
                    { key: 'refresh_cost_pr', label: 'Avg Refresh Cost Per', data: avgRefreshData, description: 'The average cost of refreshing jobs' }
                  ]}
                />
              </div>

              <div className="grid">
                  <div className="stat-card" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                        <h3>API Cost Breakdown (30 d)</h3>
                        <div style={{ width: '90%', maxWidth: 420 }}>
                            <Pie data={spendBreakdown} options={spendBreakdownOptions} />
                        </div>
                  </div>
              </div>

        </div>
    );
}




function StatCard({ title, value, subvalue }) {
    return (
        <div className="stat-card">
            <h3>{title}</h3>
            <p>{value}</p>
            {subvalue && <p style={{ fontSize: '12px', color: 'gray' }}>{subvalue}</p>}
        </div>
    );
}
