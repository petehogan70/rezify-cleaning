import React, { useState, useEffect } from 'react';
import { HiOutlineBriefcase, HiOutlineUsers, HiSparkles, HiMagnifyingGlass } from 'react-icons/hi2';
import '../styles/OutreachNavigator.css';

function OutreachNavigator({ 
    isOpen, 
    onClose, 
    onOpenCoPilot,
    job,
    user,
    hasMessage
}) {
    const [showCoPilot, setShowCoPilot] = useState(false);

    // Reset state when component opens
    useEffect(() => {
        if (isOpen) {
            setShowCoPilot(false);
        }
    }, [isOpen]);

    if (!isOpen) {
        return null;
    }

    // Generate LinkedIn URLs using better search approaches
    const generateLinkedInURL = (searchType) => {
        if (!job || !user) {
            console.error('Missing job or user data:', { job, user });
            return 'https://www.linkedin.com/';
        }
        
        if (!job.company) {
            console.error('Missing company name in job object:', job);
            return 'https://www.linkedin.com/';
        }
        
        if (!user.reported_college) {
            console.error('Missing school name in user object:', user);
            return 'https://www.linkedin.com/';
        }
        
        const companyName = (job.company || '').trim();
        const schoolName = (user.reported_college || '').trim();
        
        console.log('LinkedIn URL generation:', { 
            companyName, 
            schoolName, 
            searchType, 
            fullJobObject: job,
            fullUserObject: user 
        });

        const base = 'https://www.linkedin.com/search/results/people/';
        
        if (searchType === 'alumni') {
            // Create a simple but effective search for alumni at the company
            // This will work once the user is logged into LinkedIn
            // Structured alumni search
            const finalURL = `${base}?company=${encodeURIComponent(companyName)}&origin=FACETED_SEARCH&schoolFreetext=${encodeURIComponent(`"${schoolName}"`)}`;
            console.log('Generated alumni search URL:', finalURL);
            return finalURL;

        } else if (searchType === 'recruiters') {
            // Search specifically for recruiters at the company
            const titles = ['Recruiter', 'Talent Acquisition', 'University Recruiting'];
            const titleQuery = titles.map(t => `"${t}"`).join(' OR ');
            const finalURL = `https://www.linkedin.com/search/results/people/?keywords=${encodeURIComponent(titleQuery)}&company=${encodeURIComponent(companyName)}&origin=FACETED_SEARCH`;
            console.log('Generated recruiter search URL:', finalURL);
            return finalURL;
        }
        
        return 'https://www.linkedin.com/';
    };

    const handleCardClick = (searchType) => {
        
        const linkedinURL = generateLinkedInURL(searchType);
        
        // Show a brief confirmation of what we're searching for
        const companyName = job?.company || '';
        const schoolName = user?.reported_college || '';
        
        let searchDescription = '';
        if (searchType === 'alumni') {
            searchDescription = `${schoolName} alumni at ${companyName}`;
        } else if (searchType === 'recruiters') {
            searchDescription = `recruiters at ${companyName}`;
        }

        window.open(linkedinURL, '_blank');

        // API CALL TO INCREMENT LINKEDIN CLICKS
        fetch('/api/increment_linkedin_clicks', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({})
        })
        .then(res => res.json())
        .then(data => {
            if (data.status !== 'success') {
                console.error("Failed to increment linkedin clicks:", data);
            }
        })
        .catch(err => {
            console.error("Error calling increment linkedin clicks:", err);
        });
        
        // After they use the navigator, show the Co-Pilot option
        setTimeout(() => {
            setShowCoPilot(true);
        }, 1000);
    };

    if (showCoPilot) {
        return (
            <div className="navigator-overlay">
                <div className="navigator-modal">
                    <div className="modal-header">
                        <h2>✨ Ready to Draft Your Message?</h2>
                        <button className="close-btn" style={{ "color": "black" }}onClick={onClose}>×</button>
                    </div>
                    
                    <div className="copilot-intro">
                        <p>Now that you've found the right people to connect with, let's craft a personalized message that stands out.</p>
                        
                        <div className="copilot-cta">
                            <button 
                                className="big-copilot-btn"
                                onClick={() => {
                                    onOpenCoPilot?.(job)
                                }}
                            >
                                <HiSparkles size={16} style={{marginRight: '6px'}} />
                                Draft Message with AI Co-Pilot
                            </button>
                        </div>
                        
                        <p className="copilot-subtitle">
                            Our AI will analyze your resume and this job posting to create a highly personalized outreach message.
                        </p>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="navigator-overlay">
            <div className="navigator-modal">
                <div className="modal-header">
                    <h2>
                        <HiMagnifyingGlass size={24} style={{display: 'inline', marginRight: '8px'}} />
                        LinkedIn Navigator
                    </h2>
                    <button className="close-btn" style={{ "color": "black" }} onClick={onClose}>×</button>
                </div>
                
                <div className="navigator-cards">
                    <div 
                        className="navigator-card alumni"
                        onClick={() => handleCardClick('alumni')}
                    >
                        <div className="card-icon">
                            <HiOutlineUsers size={32} />
                        </div>
                        <h3>School Alumni</h3>
                        <p className="card-subtitle">Find {user?.reported_college} Alumni</p>
                        <p className="card-description">
                            Connect with {user?.reported_college} graduates who work at {job?.company}.
                        </p>
                    </div>
                    
                    <div 
                        className="navigator-card recruiters"
                        onClick={() => handleCardClick('recruiters')}
                    >
                        <div className="card-icon">
                            <HiOutlineBriefcase size={32} />
                        </div>
                        <h3>Company Recruiters</h3>
                        <p className="card-subtitle">Find Recruiters</p>
                        <p className="card-description">
                            Connect with recruiters and talent acquisition specialists at {job?.company}.
                        </p>
                    </div>
                </div>
                
                <div className="navigator-footer">
                    <p><strong>Alumni:</strong> Search for {user?.reported_college} graduates at {job?.company}.<br/>
                    <strong>Recruiters:</strong> Find hiring managers and talent acquisition specialists.</p>
                    <p style={{fontSize: '12px', color: '#666', marginTop: '8px', fontStyle: 'italic'}}>
                        💡 Note: You'll need to sign into LinkedIn to see search results.
                    </p>
                </div>
            </div>
        </div>
    );
}

export default OutreachNavigator; 