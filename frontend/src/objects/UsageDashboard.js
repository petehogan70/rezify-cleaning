import { useMemo, useState, useEffect } from 'react';
import StatGraphCard from '../objects/StatGraphCard';
import { useTheme } from '../hooks/ThemeContext';
import '../styles/AdminDashboard.css';
import { Chart, ArcElement, Tooltip, Legend } from 'chart.js';
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


export default function UsageDashboard({ admin, primaryColor }) {

    const [loadFails, setLoadFails] = useState([]);

    const [stats, setStats] = useState(null);
    const [loading, setLoading] = useState(true);
    const [errorMessage, setErrorMessage] = useState('');
    const [loadedData, setLoadedData] = useState([]);
    const [searchesObj, setSearchesObj] = useState({});

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

        fetch('/api/get_superadmin_usage_stats')
            .then(res => res.json())
            .then(data => {
                if (!isMounted) return;

                if (data.stats) {
                    setStats(data.stats);

                    // Set loadedData immediately from stats
                    if (data.stats.usage_historical) {
                        const sorted = Object.keys(data.stats.usage_historical)
                            .map(k => [k, data.stats.usage_historical[k]])
                            .sort((a, b) => new Date(a[0]) - new Date(b[0]));
                        setLoadedData(sorted);
                        setSearchesObj(data.stats.usage_historical);
                    }
                }

                if (data.error_message) setErrorMessage(data.error_message);
            })
            .finally(() => isMounted && setLoading(false));

        return () => { isMounted = false; };
    }, []);

    const labels = useMemo(() => loadedData.map(([date]) => date), [loadedData]);

    const numLinkedInClicksDaily = useMemo(() => ({
        labels,
        datasets: [{
          label: 'LinkedIn Clicks Daily',
          data: loadedData.map(([, v]) => v.linkedin_clicks),
          ...baseDatasetStyle,
        }],
    }), [labels, loadedData, baseDatasetStyle]);

    const numFavoritesData = useMemo(() => ({
        labels,
        datasets: [{
          label: 'Number of Favorites',
          data: loadedData.map(([, v]) => v.total_favorites),
          ...baseDatasetStyle,
        }],
    }), [labels, loadedData, baseDatasetStyle]);

    const numAppliedData = useMemo(() => ({
        labels,
        datasets: [{
          label: 'Number of Applications',
          data: loadedData.map(([, v]) => v.total_applications),
          ...baseDatasetStyle,
        }],
    }), [labels, loadedData, baseDatasetStyle]);

    const numMessagesData = useMemo(() => ({
        labels,
        datasets: [{
          label: 'Number of Messages Generated',
          data: loadedData.map(([, v]) => v.total_li_messages),
          ...baseDatasetStyle,
        }],
    }), [labels, loadedData, baseDatasetStyle]);

    const numAcceptedData = useMemo(() => ({
        labels,
        datasets: [{
          label: 'Number of Positions Accepted',
          data: loadedData.map(([, v]) => v.total_accepted),
          ...baseDatasetStyle,
        }],
    }), [labels, loadedData, baseDatasetStyle]);

    const avgParseExpTimeData = useMemo(() => ({
        labels,
        datasets: [{
          label: 'Parse Exp Runtime',
          data: loadedData.map(([, v]) => v.parse_exp_searchtime),
          ...baseDatasetStyle,
        }],
    }), [labels, loadedData, baseDatasetStyle]);

    const dailyPairs = useMemo(() => toSortedPairs(searchesObj), [searchesObj]);

    // A) Stacked "Searches" by reason
    const searchesKeys = [
      'homepage_searches',
      'add_title_searches',
      'refresh_searches'
    ];

    const searchesLabelMap = {
      homepage_searches: 'Homepage Full',
      add_title_searches: 'Add Title',
      refresh_searches: 'Refresh Jobs'
    };

    const searchesData = useMemo(() => buildStackedFromDaily({
      pairs: dailyPairs,
      keys: searchesKeys,
      primaryColor,
      addOverlayTotal: true,
      stackId: 'searches',
      labelMap: searchesLabelMap,
    }), [dailyPairs, primaryColor]);

    // B) Stacked "Homepage Searchtime"
    const homepageKeys = [
        'h_job_0_parse_resume',
        'h_job_1_gen_embeddings',
        'h_job_2_knn_title',
        'h_job_3_knn_description',
        'h_job_4_get_jobs',
        'h_job_5_compute_sort'
    ];

    const homepageLabelMap = {
      h_job_0_parse_resume: 'Parse Resume For Skills',
      h_job_1_gen_embeddings: 'Generate Embeddings (OpenAI API) For Matching',
      h_job_2_knn_title: 'KNN Title Matching (Elasticsearch)',
      h_job_3_knn_description: 'KNN Description-SKills Matching (Elasticsearch)',
      h_job_4_get_jobs: 'Get Job Info From Database',
      h_job_5_compute_sort: 'Compute Final Match Score & Sort'
    };

    const homepageSearchesData = useMemo(() => buildStackedFromDaily({
      pairs: dailyPairs,
      keys: homepageKeys,
      primaryColor,
      addOverlayTotal: true,
      stackId: 'homepage_searches',
      labelMap: homepageLabelMap,
    }), [dailyPairs, primaryColor]);

    // C) Stacked "Add/Refresh Searchtime"
    const arKeys = [
        'ar_job_1_gen_embeddings',
        'ar_job_2_knn_title',
        'ar_job_3_knn_description',
        'ar_job_4_get_jobs',
        'ar_job_5_compute_sort'
    ];

    const arLabelMap = {
      ar_job_1_gen_embeddings: 'Generate Embeddings (OpenAI API) For Matching',
      ar_job_2_knn_title: 'KNN Title Matching (Elasticsearch)',
      ar_job_3_knn_description: 'KNN Description-SKills Matching (Elasticsearch)',
      ar_job_4_get_jobs: 'Get Job Info From Database',
      ar_job_5_compute_sort: 'Compute Final Match Score & Sort'
    };

    const arSearchesData = useMemo(() => buildStackedFromDaily({
      pairs: dailyPairs,
      keys: arKeys,
      primaryColor,
      addOverlayTotal: true,
      stackId: 'ar_searches',
      labelMap: arLabelMap,
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
                <span style={{ color: 'black' }}>Usage Overview Dashboard:</span>{' '}
                <span style={{ color: 'var(--primary-color)' }}>
                  {admin.school_fullname}
                </span>
              </h1>

              <div className="grid">
                <StatCard title="Searches (Last 24 hrs)" value={stats?.day_search_data?.total_searches ?? 0} />
                <StatCard title="Avg Search Time (24 hrs)" value={`${stats?.day_search_data?.average_runtime ?? 0} sec`} />
                <StatCard title="Unique Email Searches (24 hrs)" value={stats?.day_search_data?.unique_emails_count ?? 0} />
              </div>

              <div className="grid">
                <StatCard title="Total Favorites" value={stats?.total_favorites ?? 0} />
                <StatCard title="Total Applications" value={stats?.total_applied ?? 0} />
                <StatCard title="Total Messages Generated" value={stats?.total_messages_generated ?? 0} />
                <StatCard title="Total Jobs Accepted" value={stats?.total_accepted ?? 0} />
              </div>

              <div className="grid" style={{ padding: '0 0.2rem' }}>
                <StatGraphCard
                  title="Usage Trends"
                  initialKey="users"
                  defaultRangeKey="1y"
                  options={[
                    {
                      key: 'searches', label: 'Searches (By Type)',
                      description:
                        'Daily number of searches broken down by type. Homepage searches come when a user either searches for the first time or changes their resume. ' +
                        'A homepage search is a full search that parses the resume. Add Title searches come from when a user adds a search title to their results. It does not have to parse the resume. ' +
                        'A Refresh search comes from when the user refreshes their results. It does not have to parse the resume',
                      stacked: true, overlayTotal: true,
                      data: searchesData,
                    },
                    { key: 'total_favorites', label: 'Total Favorites', data: numFavoritesData, description: 'Viewing the number jobs marked as favorites by users.' },
                    { key: 'total_applications', label: 'Total Applications', data: numAppliedData, description: 'Viewing the number jobs marked as applied_to by users.' },
                    { key: 'total_li_messages', label: 'Total Messages Generated', data: numMessagesData, description: 'Viewing the number LinkedIn outreach messages generated by users.' },
                    { key: 'total_accepted', label: 'Total Acceptances', data: numAcceptedData, description: 'Viewing the number jobs marked as accepted by users.' },
                    { key: 'linkedin_clicks_daily', label: 'LinkedIn Clicks Daily', data: numLinkedInClicksDaily, description: 'The number of times users clicked Find Alumni on LinkedIn button, by day.'},
                    {
                      key: 'homepage_searches', label: 'Homepage Searchtime',
                      description:
                        'Daily average searchtime of full searches from the homepage, broken down by the part of the algorithm. Job 0 involves parsing the resume with the OpenAI api, extracting skills to match the user to job descriptions. ' +
                        'Job 1 uses the OpenAI API to generate vector embeddings for the users skills and search titles, used for matching. Job 2 uses KNN in Elasticsearch to match search title embeddings to job title embeddings stored in Elasticsearch. ' +
                        'Job 3 uses KNN in Elasticsearch to match the users skills embedding vector to job description embeddings in Elasticsearch. Job 4 gets the full job information for the matches found in steps 2-3. ' +
                        'Job 5 computes the final match scores and sorts the results.',
                      stacked: true, overlayTotal: true,
                      data: homepageSearchesData,
                    },
                    {
                      key: 'ar_searches', label: 'Add Title / Refresh Searchtime',
                      description:
                        'Daily average searchtime of either add title or refresh searches from the results page, broken down by the part of the algorithm. ' +
                        'Job 1 uses the OpenAI API to generate vector embeddings for the users skills and search titles, used for matching. Job 2 uses KNN in Elasticsearch to match search title embeddings to job title embeddings stored in Elasticsearch. ' +
                        'Job 3 uses KNN in Elasticsearch to match the users skills embedding vector to job description embeddings in Elasticsearch. Job 4 gets the full job information for the matches found in steps 2-3. ' +
                        'Job 5 computes the final match scores and sorts the results.',
                      stacked: true, overlayTotal: true,
                      data: arSearchesData,
                    },
                    { key: 'parse_exp_searchtime', label: 'Parse Experience Runtime', data: avgParseExpTimeData,
                        description: 'The daily average runtime of the parse experience part of our algorithm, using the OpenAI API. This is to get the full list of experiences used in the message generation feature. This runs separately from our main search algorithm' },
                  ]}
                />
              </div>

              <div className="grid">
                <StatListCard
                  title="Top Searches"
                  values={(stats?.top_searches ?? []).map(el => (
                    <span>
                      {el.term}{' '}
                      <span style={{ color: 'var(--primary-color)' }}>
                        <b>({el.count})</b>
                      </span>
                    </span>
                  ))}
                />
                <StatListCard
                  title="Top Companies"
                  values={(stats?.top_companies_applied ?? []).map(el => (
                    <span>
                      <ImageWithFailsafe logo={el.company_logo} letter={el.company?.[0]} />
                      {el.company}{' '}
                      <span style={{ color: 'var(--primary-color)' }}>
                        <b>({el.count})</b>
                      </span>
                    </span>
                  ))}
                />
                <StatListCard
                  title="Top Jobs"
                  values={(stats?.top_jobs_applied ?? []).map(el => (
                    <span>
                      <ImageWithFailsafe logo={el.company_logo} letter={el.company?.[0]} />
                      {el.title}{' '}
                      <span style={{ color: 'var(--primary-color)' }}>
                        <b>({el.count})</b>
                      </span>
                    </span>
                  ))}
                />
              </div>

              <div className="grid">
                  <StatListCard
                        title="Top Users"
                        values={(stats?.top_users ?? []).map((el) => (
                            <span>
                                <span style={{ fontWeight: 600 }}>{el.User}</span>
                                {'  |  '}
                                <span>
                                    Favorites:{' '}
                                    <span style={{ color: 'var(--primary-color)' }}>
                                        <b>({el.favorites_count ?? 0})</b>
                                    </span>
                                </span>
                                {'  |  '}
                                <span>
                                    Applied To:{' '}
                                    <span style={{ color: 'var(--primary-color)' }}>
                                        <b>({el.applied_to_count ?? 0})</b>
                                    </span>
                                </span>
                                {'  |  '}
                                <span>
                                    Messages Generated:{' '}
                                    <span style={{ color: 'var(--primary-color)' }}>
                                        <b>({el.messages_generated_count ?? 0})</b>
                                    </span>
                                </span>
                            </span>
                        ))}
                  />
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

function StatListCard({ title, values }) {
    return (
        <div className="stat-card">
            <h3>{title}</h3>
            <ol style={{ textAlign: 'left' }}>
                {values.map((element, idx) => (
                <li key={idx}>{element}</li>
                ))}
            </ol>
        </div>
    );
}