import React, { useState } from 'react';
import DOMPurify from 'dompurify';
import '../styles/AdminJobsList.css';

export default function AdminJobsList({ jobs = [] }) {
    const [loadFails, setLoadFails] = useState([]);     // logos that failed to load
    const [showDesc, setShowDesc] = useState([]);       // job ids with full desc shown
    const [preDesc, setPreDesc] = useState([]);         // job ids currently fetching
    const [fullDesc, setFullDesc] = useState({});       // { [jobId]: sanitized HTML }

    const ImageWithFailsafe = ({ logo, letter }) => {
        if (logo && !loadFails.includes(logo)) {
            return (
                <img
                    src={logo}
                    alt="Company Logo"
                    className="company-logo"
                    onError={() => setLoadFails(prev => [...prev, logo])}
                />
            );
        }
        return <div className="fallback-logo">{letter}</div>;
    };

    return (
        <>
            {/* Results header */}
            <p><strong>Total Results:</strong> {jobs.length}</p>

            {/* Empty state */}
            {jobs.length === 0 && (
                <p style={{ color: '#666', fontStyle: 'italic' }}>No results found</p>
            )}

            {Array.isArray(jobs) && jobs.map((job) => {
                const jobId = job.id ?? job.job_id;

                return (

                    <div key={jobId} className="job-card">
                        {/* Top: logo + title */}
                        <div className="logo-title-container">
                            {job.company_url ? (
                                <a
                                    href={job.company_url}
                                    target="_blank"
                                    rel="noreferrer"
                                    style={{ textDecoration: 'none', color: 'inherit' }}
                                >
                                    <ImageWithFailsafe
                                        logo={job.company_logo}
                                        letter={job.company?.[0] || '?'}
                                    />
                                </a>
                            ) : (
                                <ImageWithFailsafe
                                    logo={job.company_logo}
                                    letter={job.company?.[0] || '?'}
                                />
                            )}

                            <h2 className="job-title">{job.title}</h2>
                        </div>

                        {/* Company / meta */}
                        {job.company_url ? (
                            <p>
                                <strong>Company: </strong>
                                <a
                                    href={job.company_url}
                                    target="_blank"
                                    rel="noreferrer"
                                    style={{ textDecoration: 'none', color: 'inherit' }}
                                >
                                    {job.company}
                                </a>
                            </p>
                        ) : (
                            <p>
                                <strong>Company:</strong> {job.company}
                            </p>
                        )}

                        {job.company_industry && (
                            <p>
                                <strong>Industry:</strong> {job.company_industry}
                            </p>
                        )}

                        {job.company_employee_count_range && (
                            <p>
                                <strong>Company Size:</strong> {job.company_employee_count_range}
                            </p>
                        )}

                        <p>
                            <strong>Location:</strong>{' '}
                            {job.location === 'Remote'
                                ? job.location
                                : job.location && job.location.includes(',')
                                ? job.location
                                : `${job.location || 'Unknown'}, ${job.state_code || ''}`}
                        </p>

                        <p>
                            <strong>Date Posted:</strong> {job.date_posted}
                        </p>

                        {job.salary && job.salary.length > 1 && (
                            <p>
                                <strong>Salary:</strong> {job.salary}
                            </p>
                        )}

                        {/* Description (toggle + content). If missing, fetch from backend. */}
                        {job.description ? (
                            <>
                                <p><strong>Description:</strong></p>
                                <span
                                    className="more-link"
                                    onClick={() => {
                                        setShowDesc(prev =>
                                            prev.includes(jobId)
                                                ? prev.filter(id => id !== jobId)
                                                : [...prev, jobId]
                                        );
                                    }}
                                >
                                    {showDesc.includes(jobId) ? 'Show Less' : 'Read full description'}
                                </span>
                                <div
                                    className="full-description"
                                    style={{ display: showDesc.includes(jobId) ? 'block' : 'none' }}
                                >
                                    <div
                                        dangerouslySetInnerHTML={{
                                            __html: DOMPurify.sanitize(job.description)
                                        }}
                                    />
                                </div>
                            </>
                        ) : (
                            <>
                                <p><strong>Description:</strong></p>
                                <span
                                    className="more-link"
                                    onClick={() => {
                                        if (!showDesc.includes(jobId)) {
                                            if (!(jobId in fullDesc)) {
                                                setPreDesc(prev => [...prev, jobId]);
                                                fetch(`/api/get_description/${jobId}`)
                                                    .then(r => r.json())
                                                    .then(data => {
                                                        const html =
                                                            data?.status === 'success'
                                                                ? data.html
                                                                : '<p>Could not load description.</p>';
                                                        setFullDesc(prev => ({
                                                            ...prev,
                                                            [jobId]: DOMPurify.sanitize(html)
                                                        }));
                                                        setShowDesc(prev => [...prev, jobId]);
                                                    })
                                                    .catch(() => {
                                                        setFullDesc(prev => ({
                                                            ...prev,
                                                            [jobId]: '<p>Error loading description.</p>'
                                                        }));
                                                        setShowDesc(prev => [...prev, jobId]);
                                                    })
                                                    .finally(() => {
                                                        setPreDesc(prev => prev.filter(id => id !== jobId));
                                                    });
                                            } else {
                                                setShowDesc(prev => [...prev, jobId]);
                                            }
                                        } else {
                                            setShowDesc(prev => prev.filter(id => id !== jobId));
                                            setPreDesc(prev => prev.filter(id => id !== jobId));
                                        }
                                    }}
                                >
                                    {preDesc.includes(jobId)
                                        ? (showDesc.includes(jobId) ? 'Show Less' : <div className="spinner" />)
                                        : 'Read full description'}
                                </span>
                                <div
                                    className="full-description"
                                    style={{ display: showDesc.includes(jobId) ? 'block' : 'none' }}
                                >
                                    <div
                                        dangerouslySetInnerHTML={{
                                            __html: fullDesc[jobId] || ''
                                        }}
                                    />
                                </div>
                            </>
                        )}

                        {/* Apply link */}
                        <p>
                            <strong>
                                <a href={job.final_url} target="_blank" rel="noreferrer">
                                    Apply Here
                                </a>
                            </strong>
                        </p>

                        {/* Optional recruiter emails */}
                        {job.recruiter_emails && Array.isArray(job.recruiter_emails) && (
                            <p>
                                <strong>Recruiter Emails:</strong> {job.recruiter_emails.join(', ')}
                            </p>
                        )}
                    </div>
                );
            })}
        </>
    );
}
