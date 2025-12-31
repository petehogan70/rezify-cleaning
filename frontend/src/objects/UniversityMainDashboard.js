import { useMemo, useState } from 'react';
import StatGraphCard from '../objects/StatGraphCard';
import { useTheme } from '../hooks/ThemeContext';

function hexToRgba(hex, alpha = 1) {
  if (!hex) return `rgba(219, 58, 0, ${alpha})`; // Rezify orange fallback
  const c = hex.replace('#', '');
  const n = parseInt(c, 16);
  const r = (n >> 16) & 255;
  const g = (n >> 8) & 255;
  const b = n & 255;
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

export default function UniversityMainDashboard({ admin, stats, loadedData, primaryColor }) {

    const [loadFails, setLoadFails] = useState([]);

    const { theme } = useTheme();

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

    const labels = useMemo(() => loadedData.map(([date]) => date), [loadedData]);

    const numUsersData = useMemo(() => ({
        labels,
        datasets: [{
          label: 'Number of Users',
          data: loadedData.map(([, v]) => v.number_of_users),
          ...baseDatasetStyle,
        }],
    }), [labels, loadedData, baseDatasetStyle]);

    const activeSessionData = useMemo(() => ({
        labels,
        datasets: [{
          label: 'Active Sessions',
          data: loadedData.map(([, v]) => v.number_of_active_sessions),
          ...baseDatasetStyle,
        }],
    }), [labels, loadedData, baseDatasetStyle]);

    const applicationData = useMemo(() => ({
        labels,
        datasets: [{
          label: 'Applications Sent',
          data: loadedData.map(([, v]) => v.total_applications),
          ...baseDatasetStyle,
        }],
    }), [labels, loadedData, baseDatasetStyle]);

    const favoritesData = useMemo(() => ({
        labels,
        datasets: [{
          label: 'Favorites',
          data: loadedData.map(([, v]) => v.total_favorites),
          ...baseDatasetStyle,
        }],
    }), [labels, loadedData, baseDatasetStyle]);

    return (
        <div className="main-dashboard">
              <h1 style={{ fontFamily: "'Orbitron', sans-serif", marginTop: 0 }}>
                <span style={{ color: 'black' }}>Main Dashboard:</span>{' '}
                <span style={{ color: 'var(--primary-color)' }}>
                  {admin.school_fullname}
                </span>
              </h1>

              <div className="grid">
                <StatCard title="Students Registered" value={stats?.num_users ?? 0} />
                <StatCard
                  title={'Matches Per User'}
                  value={((stats?.total_jobs_seen ?? 0) / (stats?.num_users || 1)).toFixed(2)}
                  subvalue={`Total: ${stats?.total_jobs_seen ?? 0}`}
                />
                <StatCard
                  title="Applications Sent"
                  value={stats?.total_applications ?? 0}
                  subvalue={`Average Per User: ${((stats?.total_applications ?? 0) / (stats?.num_users || 1)).toFixed(2)}`}
                />
                <StatCard
                  title="Total Favorites"
                  value={stats?.total_favorites ?? 0}
                  subvalue={`Average Per User: ${((stats?.total_favorites ?? 0) / (stats?.num_users || 1)).toFixed(2)}`}
                />
                <StatCard title="Total Acceptances" value={stats?.total_accepted ?? 0} />
              </div>

              <div className="grid" style={{ padding: '0 0.2rem' }}>
                <StatGraphCard
                  title="Usage Trends"
                  initialKey="users"
                  defaultRangeKey="1y"
                  options={[
                    { key: 'users', label: 'Users Registered', data: numUsersData, description: 'Viewing the number of students who have successfully created an account.' },
                    { key: 'active', label: 'Active Users', data: activeSessionData, description: 'Viewing the number of students who have active sessions, meaning a user who has been active on Rezify within the past 5 days.' },
                    { key: 'applications', label: 'Applications Sent', data: applicationData, description: 'Viewing the total number of applications sent for all students.' },
                    { key: 'favorites', label: 'Marked Favorites', data: favoritesData, description: 'Viewing the total number of positions marked as favorites for all students.'}
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