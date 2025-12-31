import { useMemo, useState, useEffect } from 'react';
import StatGraphCard from '../objects/StatGraphCard';
import { useTheme } from '../hooks/ThemeContext';
import '../styles/AdminDashboard.css';
import { Chart, ArcElement, Tooltip, Legend } from 'chart.js';
import RemovedJobsList from './RemovedJobsList';
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
  if (key === 'link_html_deleted') {
    return {
      bg: hexToRgba(primaryColor, 0.45),
      border: primaryColor,
    };
  }

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


export default function JobsDashboard({ admin, primaryColor }) {

    const [loadFails, setLoadFails] = useState([]);

    const [stats, setStats] = useState(null);
    const [loading, setLoading] = useState(true);
    const [errorMessage, setErrorMessage] = useState('');
    const [loadedData, setLoadedData] = useState([]);
    const [deletionsObj, setDeletionsObj] = useState({});

    const baseDatasetStyle = useMemo(() => ({
        fill: true,
        borderColor: primaryColor,
        backgroundColor: hexToRgba(primaryColor, 0.6),
        pointBackgroundColor: hexToRgba(primaryColor, 0.6),
        pointBorderColor: primaryColor,
        borderWidth: 2,
        tension: 0.1,
    }), [primaryColor]);

    // Fetch admin + stats
      useEffect(() => {
        let isMounted = true;
        setLoading(true);

        fetch('/api/get_superadmin_jobs_stats')
            .then(res => res.json())
            .then(data => {
                if (!isMounted) return;

                if (data.stats) {
                    setStats(data.stats);

                    // Set loadedData immediately from stats
                    if (data.stats.jobs_historical) {
                        const sorted = Object.keys(data.stats.jobs_historical)
                            .map(k => [k, data.stats.jobs_historical[k]])
                            .sort((a, b) => new Date(a[0]) - new Date(b[0]));
                        setLoadedData(sorted);
                        setDeletionsObj(data.stats.jobs_historical);
                    }
                }

                if (data.error_message) setErrorMessage(data.error_message);
            })
            .finally(() => isMounted && setLoading(false));

        return () => { isMounted = false; };
    }, []);

    const labels = useMemo(() => loadedData.map(([date]) => date), [loadedData]);

    const numInternshipsData = useMemo(() => ({
        labels,
        datasets: [{
          label: 'Number of Internships',
          data: loadedData.map(([, v]) => v.internships_total),
          ...baseDatasetStyle,
        }],
    }), [labels, loadedData, baseDatasetStyle]);

    const dailyPairs = useMemo(() => toSortedPairs(deletionsObj), [deletionsObj]);

    // A) Stacked "Deleted Jobs" by reason
    const deletedKeys = [
      'age_deleted',
      'deduplicate_deleted',
      'deletion_condition_deleted',
      'link_html_deleted',
      'linkedin_deleted',
      'indeed_deleted',
    ];

    const deletedLabelMap = {
      age_deleted: 'Age > 60 days',
      deduplicate_deleted: 'Duplicates',
      deletion_condition_deleted: 'Other Condition',
      link_html_deleted: 'Link/HTML Expired',
      linkedin_deleted: 'Deleted from LinkedIn',
      indeed_deleted: 'Deleted from Indeed',
    };

    const jobsDeletedData = useMemo(() => buildStackedFromDaily({
      pairs: dailyPairs,
      keys: deletedKeys,
      primaryColor,
      addOverlayTotal: true,
      stackId: 'deleted',
      labelMap: deletedLabelMap,
    }), [dailyPairs, primaryColor]);

    // B) Stacked "Credits Used Today" (internships vs fulltime)
    const cutKeys = ['cut_internships', 'cut_fulltime'];

    const cutLabelMap = {
      cut_internships: 'Credits From Internships',
      cut_fulltime: 'Credits From Full-Time Jobs',
    };

    const creditsUsedData = useMemo(() => buildStackedFromDaily({
      pairs: dailyPairs,
      keys: cutKeys,
      primaryColor,
      addOverlayTotal: true,
      stackId: 'credits',
      labelMap: cutLabelMap,
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
                <span style={{ color: 'black' }}>Jobs Overview Dashboard:</span>{' '}
                <span style={{ color: 'var(--primary-color)' }}>
                  {admin.school_fullname}
                </span>
              </h1>

              <div className="grid">
                <StatCard title="Number of Internships" value={stats?.internships_in_table ?? 0} />
                <StatCard title="Title Embeddings" value={stats?.internships_title_embeddings ?? 0} />
                <StatCard title="Description Embeddings" value={stats?.internships_description_embeddings ?? 0} />
                <StatCard title="% of TS Credits Used"
                    value={`${stats?.ts_credits_percentage?.ts_credits_percentage ?? 0}%`}
                    subvalue={`Credits Used: ${stats?.ts_credits_percentage?.ts_credits_used ?? 0}`}
                />
              </div>

              <div className="grid" style={{ padding: '0 0.2rem' }}>
                <StatGraphCard
                  title="Usage Trends"
                  initialKey="users"
                  defaultRangeKey="1y"
                  options={[
                    { key: 'internships', label: 'Number of Internships', data: numInternshipsData, description: 'Viewing the number of internships in our database.' },
                    {
                      key: 'jobs_deleted', label: 'Jobs Deleted',
                      description: 'Daily deletions split by reason (age, duplicates, link_html, etc.) with a total overlay.',
                      stacked: true, overlayTotal: true,
                      data: jobsDeletedData,
                    },
                    {
                      key: 'credits_used', label: 'Credits Used Daily',
                      description: 'Daily credits used split by internships vs fulltime, with a total overlay.',
                      stacked: true, overlayTotal: true,
                      data: creditsUsedData
                    }
                  ]}
                />
              </div>

              <div className="grid">
                <StatCard title="30 Day Credits AVG" value={stats?.thirty_day_credits_avg ?? 0} />
                <StatCard title="Last TheirStack Purchase"
                    value={`${stats?.latest_purchase?.date ?? 'Unknown'} (${stats?.latest_purchase?.days_since_purchase ?? '0'}d)`}
                    subvalue={
                        <>
                          Credits Bought: {stats?.latest_purchase?.credits_purchased ?? 0}
                          <br />
                          Amount Spent: {stats?.latest_purchase?.amount_spent ?? 0}$
                        </>
                      } />
                <StatCard title="Estimated Next Credit Purchase" value={`${stats?.estimated_next_credit_purchase?.estimated_next_purchase ?? 'Unknown'} (${stats?.estimated_next_credit_purchase?.days_remaining ?? '0'}d)`} />
              </div>

              <div className="grid">
                <div className="stat-card">
                    <h3>Jobs Removed By Users</h3>
                    <RemovedJobsList
                        jobs={stats?.removed_jobs}
                    />
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
