import React, { useEffect, useState } from 'react';
import '../styles/AdminJobsList.css';

export default function RemovedJobsList({ jobs = [] }) {
    const [visibleJobs, setVisibleJobs] = useState(jobs);
    const [fadingOutJobId, setFadingOutJobId] = useState(null);
    const [removingIds, setRemovingIds] = useState([]); // in-flight API calls

    useEffect(() => {
        setVisibleJobs(jobs);
    }, [jobs]);

    const formatReasons = (reasons) =>
        reasons
            ? Object.entries(reasons)
                  .map(([reason, count]) => `${reason} (${count})`)
                  .join(', ')
            : null;

    async function AdminRemoveJob(jobId) {
        const ok = window.confirm('Are you sure you want to remove this job?');
        if (!ok) return;

        // Keep original for potential revert
        const idx = visibleJobs.findIndex(j => (j.id ?? j.job_id) === jobId);
        if (idx === -1) return;
        const originalJob = visibleJobs[idx];

        // Start fade out (match your 600ms timing)
        setFadingOutJobId(jobId);

        // After fade, optimistically remove from UI
        const removeTimer = setTimeout(() => {
            setVisibleJobs(prev => prev.filter(j => (j.id ?? j.job_id) !== jobId));
            setFadingOutJobId(null);
        }, 600);

        // Fire API in background
        setRemovingIds(prev => [...prev, jobId]);
        try {
            const resp = await fetch('/api/admin_remove_job', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ job_id: jobId }),
            });

            const result = await resp.json();

            if (result.status === 'session_fail') {
                window.location.href = '/results';
                return;
            }

            if (result.status === 'fail') {
                // Revert: put job back in the same position
                clearTimeout(removeTimer);
                setFadingOutJobId(null);
                setVisibleJobs(prev => {
                    const next = [...prev];
                    next.splice(Math.min(idx, next.length), 0, originalJob);
                    return next;
                });
                alert(result.message || 'Failed to remove job.');
            }
        } catch (e) {
            // Revert on network error
            clearTimeout(removeTimer);
            setFadingOutJobId(null);
            setVisibleJobs(prev => {
                const next = [...prev];
                next.splice(Math.min(idx, next.length), 0, originalJob);
                return next;
            });
            alert('Something went wrong while removing the job.');
        } finally {
            setRemovingIds(prev => prev.filter(id => id !== jobId));
        }
    }

    async function AdminJobGood(jobId) {
        const ok = window.confirm('Are you sure you want to mark this job as good, removing it from this list and safely sending back to database?');
        if (!ok) return;

        // Keep original for potential revert
        const idx = visibleJobs.findIndex(j => (j.id ?? j.job_id) === jobId);
        if (idx === -1) return;
        const originalJob = visibleJobs[idx];

        // Start fade out (match your 600ms timing)
        setFadingOutJobId(jobId);

        // After fade, optimistically remove from UI
        const removeTimer = setTimeout(() => {
            setVisibleJobs(prev => prev.filter(j => (j.id ?? j.job_id) !== jobId));
            setFadingOutJobId(null);
        }, 600);

        // Fire API in background
        setRemovingIds(prev => [...prev, jobId]);
        try {
            const resp = await fetch('/api/admin_job_good', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ job_id: jobId }),
            });

            const result = await resp.json();

            if (result.status === 'session_fail') {
                window.location.href = '/results';
                return;
            }

            if (result.status === 'fail') {
                // Revert: put job back in the same position
                clearTimeout(removeTimer);
                setFadingOutJobId(null);
                setVisibleJobs(prev => {
                    const next = [...prev];
                    next.splice(Math.min(idx, next.length), 0, originalJob);
                    return next;
                });
                alert(result.message || 'Failed to remove job.');
            }
        } catch (e) {
            // Revert on network error
            clearTimeout(removeTimer);
            setFadingOutJobId(null);
            setVisibleJobs(prev => {
                const next = [...prev];
                next.splice(Math.min(idx, next.length), 0, originalJob);
                return next;
            });
            alert('Something went wrong while removing the job.');
        } finally {
            setRemovingIds(prev => prev.filter(id => id !== jobId));
        }
    }

    return (
        <>
            <p><strong>Total Results:</strong> {visibleJobs.length}</p>

            {visibleJobs.length === 0 && (
                <p style={{ color: '#666', fontStyle: 'italic' }}>No results found</p>
            )}

            {Array.isArray(visibleJobs) && visibleJobs.map(job => {
                const jobId = job.id ?? job.job_id;
                const reasonsText = formatReasons(job.reasons);
                const isRemoving = removingIds.includes(jobId);

                return (
                    <div
                        key={jobId}
                        className={`removed-job-card ${fadingOutJobId === jobId ? 'fade-out' : ''}`}
                    >
                        <div className="removed-logo-title-container">
                            <h2 className="removed-job-title">{job.title}</h2>
                        </div>

                        <p><strong>Company:</strong> {job.company}</p>
                        <p><strong>Date Posted:</strong> {job.date_posted}</p>

                        <p>
                            <strong>
                                <a href={job.final_url} target="_blank" rel="noreferrer">
                                    Application Link
                                </a>
                            </strong>
                        </p>

                        {reasonsText && (
                            <p><strong>Reasons:</strong> {reasonsText}</p>
                        )}

                        <button
                            className="admin-remove-button"
                            disabled={isRemoving}
                            onClick={() => AdminRemoveJob(jobId)}
                            title={isRemoving ? 'Removing…' : 'Remove Job'}
                        >
                            {isRemoving ? 'Removing…' : 'Remove Job'}
                        </button>
                        <button
                            className="admin-job-good-button"
                            disabled={isRemoving}
                            onClick={() => AdminJobGood(jobId)}
                            title={isRemoving ? 'Removing…' : 'Job is Good'}
                        >
                            {isRemoving ? 'Removing…' : 'Job is Good'}
                        </button>
                    </div>
                );
            })}
        </>
    );
}
