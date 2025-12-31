import { useEffect, useMemo, useState, Suspense, lazy } from 'react';
import '../styles/AdminDashboard.css';
import { Chart, registerables } from 'chart.js';
import { useTheme } from '../hooks/ThemeContext';
import { useNavigate } from 'react-router-dom';
import { IndexFooter } from './IndexFooter';
import { AdminHeader } from './AdminHeader';
import UniversityMainDashboard from './UniversityMainDashboard';
import UsersDashboard from './UsersDashboard';
import JobsDashboard from './JobsDashboard';
import UsageDashboard from './UsageDashboard';
import OpenAIAPIDashboard from './OpenAIAPIDashboard';

Chart.register(...registerables);

// Lazy-load the views you'll build
const StudentView = lazy(() => import('./StudentView'));
const AdminAccountManagement = lazy(() => import('./AdminAccountManagement'));

export function AdminDashboard() {
  const navigate = useNavigate();
  const { theme } = useTheme(); // expected: { primary_color, logo, ... } for current school

    // Detect rezifyadmin subdomain
    const isRezifyAdmin = useMemo(() => {
        const host = window?.location?.hostname || '';
        return host === 'rezifyadmin' || host.startsWith('rezifyadmin.');
    }, []);

  const [admin, setAdmin] = useState(null);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState('');
  const [loadedData, setLoadedData] = useState([]);
  const [selectedView, setSelectedView] = useState('main');
  const [passChanged, setPassChanged] = useState(false);

  // 1) Primary color state, initialized from theme (fallback to Rezify orange)
  const [primaryColor, setPrimaryColor] = useState(theme?.primary_color || '#DB3A00');

  // Redirect if not admin after loading finishes
  useEffect(() => {
    if (!loading && admin === null) {
      const t = setTimeout(() => navigate('/'), 3000);
      return () => clearTimeout(t);
    }
  }, [loading, admin, navigate]);

    const handleLogout = async () => {
        try {
          setLoading(true);
          await fetch('/api/logout', { method: 'POST' });
          setAdmin(null);
          setStats(null);
        } catch (e) {
          console.error('Logout failed', e);
        } finally {
          setLoading(false);
        }
      };

      const handleDeleteAccount = async () => {
        if (!window.confirm('Are you sure you want to delete this admin account? This cannot be undone.')) return;

        try {
            setLoading(true);

            // Try DELETE first; fall back to POST if not allowed
            let res = await fetch('/api/delete_account', { method: 'DELETE' });
            if (res.status === 405) {
                res = await fetch('/api/delete_account', { method: 'POST' });
            }

            if (!res.ok) {
                const txt = await res.text().catch(() => '');
                throw new Error(txt || `Delete failed (${res.status})`);
            }

            // Clear client state
            setAdmin(null);
            setStats(null);

            // Redirect home
            navigate('/');
        } catch (e) {
            console.error('Delete account failed', e);
            alert(e.message || 'Failed to delete account.');
        } finally {
            setLoading(false);
        }
    };


  // Fetch admin + stats
      useEffect(() => {
        let isMounted = true;

        if (isRezifyAdmin) {
            setSelectedView('users_dashboard');

            fetch('/api/get_admin')
            .then(res => res.json())
            .then(data => {
                if (!isMounted) return;

                if (data.admin) setAdmin(data.admin);

                if (data.change) {
                    setPassChanged(true);
                    setTimeout(() => setPassChanged(false), 4000);
                }

                if (data.error_message) setErrorMessage(data.error_message);
            })
            .finally(() => isMounted && setLoading(false));
            return () => { isMounted = false; };
        }

        fetch('/api/admin')
            .then(res => res.json())
            .then(data => {
                if (!isMounted) return;

                if (data.admin) setAdmin(data.admin);

                if (data.stats) {
                    setStats(data.stats);

                    // Set loadedData immediately from stats
                    if (data.stats.historical) {
                        const sorted = Object.keys(data.stats.historical)
                            .map(k => [k, data.stats.historical[k]])
                            .sort((a, b) => new Date(a[0]) - new Date(b[0]));
                        setLoadedData(sorted);
                    }
                }

                if (data.change) {
                    setPassChanged(true);
                    setTimeout(() => setPassChanged(false), 4000);
                }

                if (data.error_message) setErrorMessage(data.error_message);
            })
            .finally(() => isMounted && setLoading(false));

        return () => { isMounted = false; };
    }, [isRezifyAdmin]);

    useEffect(() => {
        // primaryColor from theme (or CSS var fallback)
        const fromTheme = theme?.primary_color;
        if (fromTheme) {
            setPrimaryColor(fromTheme);
        } else {
            const cssVar = getComputedStyle(document.documentElement)
                .getPropertyValue('--primary-color')
                .trim();
            if (cssVar) setPrimaryColor(cssVar);
        }

        // Recompute loadedData when stats update
        if (stats?.historical) {
            const sorted = Object.keys(stats.historical)
                .map(k => [k, stats.historical[k]])
                .sort((a, b) => new Date(a[0]) - new Date(b[0]));
            setLoadedData(sorted);
        }
    }, [theme, stats]);

  // CSV helpers
  const getCSVcontent = () => {
    let str = 'Date,Number of Users,Active Sessions,Total Positions Accepted\r\n';
    for (let i = 0; i < loadedData.length; i++) {
      const [date, row] = loadedData[i];
      const line = `${date},${row.number_of_users},${row.number_of_active_sessions},${row.total_accepted}`;
      str += line + '\r\n';
    }
    return str;
  };

  const downloadCSV = () => {
    const csvData = new Blob([getCSVcontent()], { type: 'text/csv' });
    const csvURL = URL.createObjectURL(csvData);
    const link = document.createElement('a');
    link.href = csvURL;
    link.download = `admin_data_${new Date().toISOString()}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  if (loading) {
    return (
        <div className="page-shell">
          <AdminHeader onLogout={handleLogout} loading={loading} />
          <div className="sidebar">
            <h1 style={{ fontFamily: "'Orbitron', sans-serif" }}>
              <img
                src={theme?.logo}
                alt="Logo"
                style={{ verticalAlign: 'middle', height: '43px', marginRight: '10px' }}
              />
              {' '}
              Admin
            </h1>

            {!isRezifyAdmin && (
            <>
                <SidebarItem
                  label="Main Dashboard"
                  isActive={selectedView === 'main'}
                  onClick={() => setSelectedView('main')}
                />
                <SidebarItem
                  label="Student View"
                  isActive={selectedView === 'student'}
                  onClick={() => setSelectedView('student')}
                />
                <SidebarItem
                  label="Manage Account"
                  isActive={selectedView === 'account'}
                  onClick={() => setSelectedView('account')}
                />
            </>
            )}

            {isRezifyAdmin && (
            <>
                <SidebarItem
                  label="Users Dashboard"
                  isActive={selectedView === 'users_dashboard'}
                  onClick={() => setSelectedView('users_dashboard')}
                />
                <SidebarItem
                  label="Jobs Dashboard"
                  isActive={selectedView === 'jobs_dashboard'}
                  onClick={() => setSelectedView('jobs_dashboard')}
                />
                <SidebarItem
                  label="Usage Dashboard"
                  isActive={selectedView === 'usage_dashboard'}
                  onClick={() => setSelectedView('usage_dashboard')}
                />
                <SidebarItem
                  label="OpenAI API Dashboard"
                  isActive={selectedView === 'openai_dashboard'}
                  onClick={() => setSelectedView('openai_dashboard')}
                />
            </>
            )}

          </div>

          <div className="content">
            <div className="spinner-container">
                <div className="spinner-aw" />
              </div>
          </div>

          <IndexFooter />
        </div>
    );
  }

  return (
    <>
      {admin != null ? (
        <div className="page-shell">
            { passChanged &&
                <div id="success-popup" class="success-popup">Password successfully changed</div>
            }
          <AdminHeader onLogout={handleLogout} loading={loading} onExport={downloadCSV} />
          <div className="sidebar">
            <h1 style={{ fontFamily: "'Orbitron', sans-serif" }}>
              <img
                src={theme?.logo}
                alt="Logo"
                style={{ verticalAlign: 'middle', height: '43px', marginRight: '10px' }}
              />
              {' '}
              Admin
            </h1>

            {!isRezifyAdmin && (
            <>
                <SidebarItem
                  label="Main Dashboard"
                  isActive={selectedView === 'main'}
                  onClick={() => setSelectedView('main')}
                />
                <SidebarItem
                  label="Student View"
                  isActive={selectedView === 'student'}
                  onClick={() => setSelectedView('student')}
                />
                <SidebarItem
                  label="Manage Account"
                  isActive={selectedView === 'account'}
                  onClick={() => setSelectedView('account')}
                />
            </>
            )}

            {isRezifyAdmin && (
            <>
                <SidebarItem
                  label="Users Dashboard"
                  isActive={selectedView === 'users_dashboard'}
                  onClick={() => setSelectedView('users_dashboard')}
                />
                <SidebarItem
                  label="Jobs Dashboard"
                  isActive={selectedView === 'jobs_dashboard'}
                  onClick={() => setSelectedView('jobs_dashboard')}
                />
                <SidebarItem
                  label="Usage Dashboard"
                  isActive={selectedView === 'usage_dashboard'}
                  onClick={() => setSelectedView('usage_dashboard')}
                />
                <SidebarItem
                  label="OpenAI API Dashboard"
                  isActive={selectedView === 'openai_dashboard'}
                  onClick={() => setSelectedView('openai_dashboard')}
                />
            </>
            )}

          </div>

          <div className="content">
            <Suspense fallback={
              <div className="spinner-container">
                <div className="spinner-aw" />
              </div>
            }>
              {!isRezifyAdmin && (
                <>
                    {selectedView === 'main' && (
                        <UniversityMainDashboard
                          admin={admin}
                          stats={stats}
                          loadedData={loadedData}
                          primaryColor={primaryColor}
                        />
                    )}
                    {selectedView === 'student' && (
                        <StudentView admin={admin}
                         stats={stats}/>
                    )}
                    {selectedView === 'account' && (
                        <AdminAccountManagement
                            admin={admin}
                            setAdmin={setAdmin}
                            setStats={setStats}
                            onLogout={handleLogout}
                            onDelete={handleDeleteAccount}
                            loading={loading}
                        />
                    )}
                </>
              )}

              {isRezifyAdmin && (
                <>
                    {selectedView === 'users_dashboard' && (
                        <UsersDashboard
                          admin={admin}
                          loadedData={loadedData}
                          primaryColor={primaryColor}
                        />
                    )}
                    {selectedView === 'jobs_dashboard' && (
                        <JobsDashboard
                          admin={admin}
                          loadedData={loadedData}
                          primaryColor={primaryColor}
                        />
                    )}
                    {selectedView === 'usage_dashboard' && (
                        <UsageDashboard
                          admin={admin}
                          loadedData={loadedData}
                          primaryColor={primaryColor}
                        />
                    )}
                    {selectedView === 'openai_dashboard' && (
                        <OpenAIAPIDashboard
                          admin={admin}
                          loadedData={loadedData}
                          primaryColor={primaryColor}
                        />
                    )}
                </>
              )}
            </Suspense>
          </div>

          <IndexFooter />
        </div>
      ) : (
        <div className="admin-unauthorized">
          <h1>You do not have permission…</h1>
          <p>Redirecting to the home page…</p>
        </div>
      )}
    </>
  );
}

function SidebarItem({ label, isActive, onClick }) {
  return (
    <button
      type="button"
      className={`sidebar-item ${isActive ? 'active' : ''}`}
      onClick={onClick}
      aria-current={isActive ? 'page' : undefined}
    >
      {label}
    </button>
  );
}

