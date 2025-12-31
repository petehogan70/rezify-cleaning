import { useMemo, useState, useEffect } from 'react';
import StatGraphCard from '../objects/StatGraphCard';
import { useTheme } from '../hooks/ThemeContext';
import '../styles/AdminDashboard.css';
import { Pie } from 'react-chartjs-2';
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

export default function UsersDashboard({ admin, primaryColor }) {

    const [loadFails, setLoadFails] = useState([]);

    const [stats, setStats] = useState(null);
    const [loading, setLoading] = useState(true);
    const [errorMessage, setErrorMessage] = useState('');
    const [loadedData, setLoadedData] = useState([]);

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

        fetch('/api/get_superadmin_users_stats')
            .then(res => res.json())
            .then(data => {
                if (!isMounted) return;

                if (data.stats) {
                    setStats(data.stats);

                    // Set loadedData immediately from stats
                    if (data.stats.users_historical) {
                        const sorted = Object.keys(data.stats.users_historical)
                            .map(k => [k, data.stats.users_historical[k]])
                            .sort((a, b) => new Date(a[0]) - new Date(b[0]));
                        setLoadedData(sorted);
                    }
                }

                if (data.error_message) setErrorMessage(data.error_message);
            })
            .finally(() => isMounted && setLoading(false));

        return () => { isMounted = false; };
    }, []);

    const labels = useMemo(() => loadedData.map(([date]) => date), [loadedData]);

    const numUsersData = useMemo(() => ({
        labels,
        datasets: [{
          label: 'Number of Users',
          data: loadedData.map(([, v]) => v.number_of_users),
          ...baseDatasetStyle,
        }],
    }), [labels, loadedData, baseDatasetStyle]);

    const activeDailyUsersData = useMemo(() => ({
        labels,
        datasets: [{
          label: 'Active Daily Users',
          data: loadedData.map(([, v]) => v.active_users_today),
          ...baseDatasetStyle,
        }],
    }), [labels, loadedData, baseDatasetStyle]);

    const activeSessionsData = useMemo(() => ({
        labels,
        datasets: [{
          label: 'Active Sessions',
          data: loadedData.map(([, v]) => v.number_of_active_sessions),
          ...baseDatasetStyle,
        }],
    }), [labels, loadedData, baseDatasetStyle]);

    const numAdminsData = useMemo(() => ({
        labels,
        datasets: [{
          label: 'Number of Admins',
          data: loadedData.map(([, v]) => v.number_of_admins),
          ...baseDatasetStyle,
        }],
    }), [labels, loadedData, baseDatasetStyle]);

    const payingPremiumUsersData = useMemo(() => ({
        labels,
        datasets: [{
          label: 'Paying Premium Users',
          data: loadedData.map(([, v]) => v.paying_premium_users),
          ...baseDatasetStyle,
        }],
    }), [labels, loadedData, baseDatasetStyle]);

    const userBreakdownData = useMemo(() => {
        const basic = stats?.users_breakdown?.basic_users ?? 0;
        const paying = stats?.users_breakdown?.paying_premium_users ?? 0;
        const sponsored = stats?.users_breakdown?.sponsored_premium_users ?? 0;

        // Use primaryColor and two alpha variants for a cohesive palette
        return {
            labels: ['Basic', 'Paying Premium', 'Sponsored Premium'],
            datasets: [{
                data: [basic, paying, sponsored],
                backgroundColor: [
                    hexToRgba(primaryColor, 0.85),
                    hexToRgba(primaryColor, 0.55),
                    hexToRgba(primaryColor, 0.30)
                ],
                borderColor: [
                    hexToRgba(primaryColor, 1),
                    hexToRgba(primaryColor, 1),
                    hexToRgba(primaryColor, 1)
                ],
                borderWidth: 1
            }]
        };
    }, [stats, primaryColor]);

    const userBreakdownOptions = useMemo(() => ({
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
                <span style={{ color: 'black' }}>User Overview Dashboard:</span>{' '}
                <span style={{ color: 'var(--primary-color)' }}>
                  {admin.school_fullname}
                </span>
              </h1>

              <div className="grid">
                <StatCard
                  title={'Active Users Now'}
                  value={((stats?.active_users_now.logged_in ?? 0) + (stats?.active_users_now.unlogged_in ?? 0))}
                  subvalue={`Logged In: ${stats?.active_users_now.logged_in ?? 0}`}
                />
                <StatCard title="Users Registered" value={stats?.users_breakdown.total_users ?? 0} />
                <StatCard title="Admins Registered" value={stats?.admin_count ?? 0} />
                <StatCard title="Paying Premium Users" value={stats?.users_breakdown.paying_premium_users ?? 0} />
              </div>

              <div className="grid" style={{ padding: '0 0.2rem' }}>
                <StatGraphCard
                  title="Usage Trends"
                  initialKey="users"
                  defaultRangeKey="1y"
                  options={[
                    { key: 'users', label: 'Number of Users', data: numUsersData, description: 'Viewing the number of students who have successfully created an account.' },
                    { key: 'admins', label: 'Number of Admins', data: numAdminsData, description: 'Viewing the number of admins who have successfully created an account.' },
                    { key: 'active', label: 'Active Daily Users', data: activeDailyUsersData, description: 'Viewing the number of students who have an active daily session, meaning a logged in user who has been active on Rezify within the day.' },
                    { key: 'sessions', label: 'Active Sessions', data: activeSessionsData, description: 'Viewing the number active sessions by day. This means the number of people on Rezify (logged in or un logged in) within the past 5 days.' },
                    { key: 'paying_premium', label: 'Paying Premium Users', data: payingPremiumUsersData, description: 'Viewing the total number of paying premium users.' }
                  ]}
                />
              </div>

              <div className="grid">
                <StatListCard
                  title="Users By School"
                  values={(stats?.users_by_school ?? []).map(el => (
                    <span>
                      {el.school}{' '}
                      <span style={{ color: 'var(--primary-color)' }}>
                        <b>({el.count})</b>
                      </span>
                    </span>
                  ))}
                />
                <div className="stat-card" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                    <h3>User Breakdown</h3>
                    <div style={{ width: '90%', maxWidth: 420 }}>
                        <Pie data={userBreakdownData} options={userBreakdownOptions} />
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