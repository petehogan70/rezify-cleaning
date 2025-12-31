import { useEffect, useMemo, useRef, useState } from 'react';
import AdminJobsList from './AdminJobsList';

export default function StudentView({ admin, stats }) {
    const [query, setQuery] = useState('');
    const [isOpen, setIsOpen] = useState(false);
    const [highlighted, setHighlighted] = useState(0);
    const [selectedEmail, setSelectedEmail] = useState(null);
    const [userDataLoading, setUserDataLoading] = useState(false);
    const [userData, setUserData] = useState(null);
    const [userDataError, setUserDataError] = useState('');
    const [jobsTab, setJobsTab] = useState('applied'); // 'applied' | 'favorites'


    const rootRef = useRef(null);

    const users = useMemo(() => {
        const raw = stats?.users_list ?? [];
        return raw
            .map((u) => {
                if (typeof u === 'string') return { email: u, name: '' };
                const email = u.email || u.user_email || '';
                const name =
                    u.name ||
                    [u.first_name, u.last_name].filter(Boolean).join(' ') ||
                    '';
                return { email, name };
            })
            .filter((u) => u.email);
    }, [stats]);

    const filtered = useMemo(() => {
        const q = query.trim().toLowerCase();
        if (!q) return users.slice(0, 8);
        return users
            .filter(
                (u) =>
                    u.email.toLowerCase().includes(q) ||
                    (u.name && u.name.toLowerCase().includes(q))
            )
            .slice(0, 8);
    }, [users, query]);

    useEffect(() => {
        function onDocClick(e) {
            if (!rootRef.current) return;
            if (!rootRef.current.contains(e.target)) setIsOpen(false);
        }
        document.addEventListener('mousedown', onDocClick);
        return () => document.removeEventListener('mousedown', onDocClick);
    }, []);

    function onKeyDown(e) {
        if (!isOpen && (e.key === 'ArrowDown' || e.key === 'ArrowUp')) {
            setIsOpen(true);
            return;
        }
        if (!isOpen) return;

        if (e.key === 'ArrowDown') {
            e.preventDefault();
            setHighlighted((i) => Math.min(i + 1, filtered.length - 1));
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            setHighlighted((i) => Math.max(i - 1, 0));
        } else if (e.key === 'Enter') {
            e.preventDefault();
            const pick = filtered[highlighted];
            if (pick) {
                handleSelectEmail(pick.email);
            }
        } else if (e.key === 'Escape') {
            setIsOpen(false);
        }
    }

    function handleSelectEmail(email) {
        setSelectedEmail(email);
        setIsOpen(false);
        setUserData(null);
        setUserDataError('');
    }

    useEffect(() => {
        if (!selectedEmail) return;

        const ctrl = new AbortController();
        (async () => {
            try {
                setUserDataLoading(true);
                setUserDataError('');
                setUserData(null);

                const res = await fetch('/api/get_user_from_admin', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email: selectedEmail }),
                    signal: ctrl.signal,
                });
                if (!res.ok) {
                    const text = await res.text().catch(() => '');
                    throw new Error(text || `Request failed (${res.status})`);
                }
                const data = await res.json();
                setUserData(data);
            } catch (err) {
                if (err.name !== 'AbortError') {
                    setUserDataError(err.message || 'Failed to fetch user data.');
                }
            } finally {
                setUserDataLoading(false);
            }
        })();

        return () => ctrl.abort();
    }, [selectedEmail]);

    const currentUser = userData?.user;

    return (
        <div className="student-view">
            <h1 className="student-view-title">
                <span style={{ color: 'black' }}>Student View:</span>{' '}
                <span style={{ color: 'var(--primary-color)' }}>
                    {admin?.school_fullname}
                </span>
            </h1>

            <div ref={rootRef} className="student-view-container">
                {/* Search area */}
                <div className="student-search-box">
                    <label htmlFor="student-search" className="student-label">
                        Search For Student:
                    </label>

                    {/* NEW: positioned wrapper */}
                    <div className="student-combobox">
                        <input
                            id="student-search"
                            type="text"
                            value={query}
                            onChange={(e) => {
                                setQuery(e.target.value);
                                setIsOpen(true);
                                setHighlighted(0);
                            }}
                            onFocus={() => setIsOpen(true)}
                            onKeyDown={onKeyDown}
                            placeholder="Type email..."
                            autoComplete="off"
                            className="student-input"
                        />

                        {isOpen && filtered.length > 0 && (
                            <ul className="student-dropdown" role="listbox">
                                {filtered.map((u, idx) => (
                                    <li
                                        key={`${u.email}-${idx}`}
                                        role="option"
                                        aria-selected={idx === highlighted}
                                        className={`student-option ${idx === highlighted ? 'highlighted' : ''}`}
                                        onMouseEnter={() => setHighlighted(idx)}
                                        onMouseDown={(e) => e.preventDefault()}
                                        onClick={() => handleSelectEmail(u.email)}
                                    >
                                        <div className="student-option-main">
                                            <div className="student-option-email">{u.email}</div>
                                            {u.name && <div className="student-option-name">{u.name}</div>}
                                        </div>
                                        <span className="student-option-select">Select</span>
                                    </li>
                                ))}
                            </ul>
                        )}
                    </div>
                </div>

                {/* Selected student */}
                <div className="student-selected">
                    <div className="student-label">Selected Student:</div>
                    <div
                        className={`student-selected-email ${selectedEmail ? '' : 'none'}`}
                    >
                        {userData?.user
                            ? `${userData.user.first_name} ${userData.user.last_name} (${userData.user.email})`
                            : (selectedEmail || 'None Selected')}
                    </div>
                </div>
            </div>

                <div className="filter-buttons-inline">
                    <button
                        className={jobsTab === 'applied' ? 'selected' : ''}
                        onClick={() => setJobsTab('applied')}
                    >
                        Applied To
                    </button>
                    <button
                        className={jobsTab === 'favorites' ? 'selected' : ''}
                        onClick={() => setJobsTab('favorites')}
                    >
                        Favorites
                    </button>
                </div>


                {/* Render jobs */}
                <div style={{ marginTop: 12 }}>
                    {userDataLoading ? (
                        <div className="spinner-container">
                            <div className="spinner-aw" />
                        </div>
                    ) : (
                        <AdminJobsList
                            jobs={
                                jobsTab === 'favorites'
                                    ? (userData?.user?.favorites || [])
                                    : (userData?.user?.applied_to || [])
                            }
                        />
                    )}
                </div>

            {/*
            <div className="student-user-card">
                {userDataLoading && <div className="student-muted">Loading user data…</div>}
                {!userDataLoading && userDataError && (
                    <div className="student-error">Error: {userDataError}</div>
                )}
                {!userDataLoading && !userDataError && userData && (
                    <pre className="student-pretty-json">
            {JSON.stringify(userData, null, 2)}
                    </pre>
                )}
                {!userDataLoading && !userDataError && !userData && selectedEmail && (
                    <div className="student-muted">No data returned for this user.</div>
                )}
            </div>
            */}
        </div>
    );
}
