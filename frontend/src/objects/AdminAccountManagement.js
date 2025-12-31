// src/components/AdminAccountManagement.js
import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';

export default function AdminAccountManagement({
    admin,
    setAdmin,
    setStats,
    onLogout,
    onDelete,
    loading
}) {
    const navigate = useNavigate();

    const fullName = useMemo(() => {
        const fn = admin?.first_name || '';
        const ln = admin?.last_name || '';
        return `${fn} ${ln}`.trim() || '—';
    }, [admin]);

    const createdText = useMemo(() => {
        const t = admin?.time_created;
        if (!t) return '—';
        try {
            const dt = new Date(String(t).replace(' ', 'T'));
            return dt.toLocaleString();
        } catch {
            return String(t);
        }
    }, [admin]);


    return (
        <div className="account-view">
            <h1 className="student-view-title">
                <span style={{ color: 'black' }}>Account:</span>{' '}
                <span style={{ color: 'var(--primary-color)' }}>
                    {fullName}
                </span>
            </h1>

            <div className="account-grid">
                {/* Left: details */}
                <div className="account-card">
                    <h3>Admin Details</h3>
                    <div className="account-field">
                        <label>Full name</label>
                        <div>{fullName}</div>
                    </div>
                    <div className="account-field">
                        <label>Email</label>
                        <div>{admin?.email || '—'}</div>
                    </div>
                    <div className="account-field">
                        <label>School</label>
                        <div>{admin?.school_fullname || '—'}</div>
                    </div>
                    <div className="account-field">
                        <label>Date created</label>
                        <div>{createdText}</div>
                    </div>
                </div>

                {/* Right: actions */}
                <div className="account-card">
                    <h3>Actions</h3>

                    <div className="account-actions">
                        <button
                            type="button"
                            className="link-like primary-link"
                            onClick={() => navigate('/change_password')}
                            disabled={loading}
                        >
                            Change Password
                        </button>

                        <a
                          href="https://docs.google.com/forms/d/e/1FAIpQLScO906_cFeHxCN_3UdPhA8FckpcUWxMFfcNn5wCstICRnv52Q/viewform?usp=header"
                          target="_blank"
                          rel="noreferrer"
                          className="link-like primary-link"
                        >
                          Request New Admin
                        </a>


                        <button
                            type="button"
                            className="link-like logout-link"
                            onClick={onLogout}
                            disabled={loading}
                            title={loading ? 'Logging out...' : 'Log out'}
                        >
                            Logout
                        </button>


                        <button
                            type="button"
                            className="link-like red-link"
                            onClick={onDelete}
                            disabled={loading}
                            title={loading ? 'Processing…' : 'Delete Account'}
                        >
                            Delete Account
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}
