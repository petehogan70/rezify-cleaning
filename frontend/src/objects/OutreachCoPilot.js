import React, { useState, useEffect, useCallback } from 'react';
import { HiLightBulb, HiRocketLaunch, HiBolt, HiPencilSquare } from 'react-icons/hi2';
import '../styles/OutreachCoPilot.css';

function OutreachCoPilot({ 
    isOpen, 
    onClose, 
    job,
    user,
    onDraftGenerated,
    hasMessage
}) {
    const [step, setStep] = useState('loading'); // loading, selection, generating, complete
    const [talkingPoints, setTalkingPoints] = useState([]);
    const [selectedPoints, setSelectedPoints] = useState([]);
    const [messageGoal, setMessageGoal] = useState('');
    const [messageLength, setMessageLength] = useState('standard'); // brief, standard, detailed
    const [generatedMessage, setGeneratedMessage] = useState('');
    const [editableMessage, setEditableMessage] = useState('');
    const [isGenerating, setIsGenerating] = useState(false);

    // LinkedIn message word count limits
    const LINKEDIN_LIMITS = {
        brief: { min: 40, max: 70, label: 'Brief  (Under LinkedIn Message Limit)' },
        standard: { min: 80, max: 120, label: 'Standard Length' },
        detailed: { min: 120, max: 180, label: 'Detailed & Comprehensive' }
    };

    const getExistingMessage = useCallback(() => {
        if (!user?.messages_generated || !job?.id) return null;
        const idStr = String(job.id ?? job.job_id);
        const match = user.messages_generated.find(m => String(m.job_id ?? m.id) === idStr);
        return match?.message || null;
      }, [user?.messages_generated, job?.id]);

    useEffect(() => {
      if (!isOpen || !job?.id || !user) return;
      if (hasMessage && getExistingMessage()) return; // already at 'complete'
      fetchTalkingPoints();
    }, [isOpen, job?.id, user, hasMessage, getExistingMessage]);

    useEffect(() => {
        if (!isOpen) return;

        const existing = hasMessage ? getExistingMessage() : null;

        setTalkingPoints([]);
        setSelectedPoints([]);
        setMessageGoal('');
        setMessageLength('standard');
        setIsGenerating(false);

        if (existing) {
          setGeneratedMessage(existing);
          setEditableMessage(existing);
          setStep('complete');
        } else {
          setGeneratedMessage('');
          setEditableMessage('');
          setStep('loading');
        }
      }, [isOpen, hasMessage, getExistingMessage]);

    // Smart pre-selection of talking points based on relevance
    const autoSelectBestPoints = (points) => {
        if (points.length === 0) return [];
        
        // Auto-select top 2-3 points (assuming they're returned in relevance order)
        const autoSelected = points.slice(0, Math.min(3, points.length)).map(point => point.id);
        setSelectedPoints(autoSelected);
    };

    const fallbackPoints = [
                    {
                        id: 'fallback1',
                        text: `My experience and coursework at ${user?.reported_college || 'university'}  directly applies to the ${job?.title || 'posted'} role`
                    },
                    {
                        id: 'fallback2',
                        text: `${job?.company || 'Your company'} vision aligns with my passions, and I would love to contribute my skills to your team`
                    },
                    {
                        id: 'fallback3',
                        text: `As a ${user?.reported_college || 'university'} student, I understand the collaborative culture at ${job?.company || 'your company'}`
                    }
                ];

    const fetchTalkingPoints = useCallback(async () => {

        if (hasMessage && getExistingMessage()) return; // bail out if we already loaded a draft

        try {
            setStep('loading');
            console.log('Fetching talking points for job:', job.id);
            
            // Add timeout to prevent infinite loading
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 30000); // 30 second timeout
            
            const response = await fetch('/api/messaging/analyze-talking-points', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    jobId: job.id
                }),
                signal: controller.signal
            });

            clearTimeout(timeoutId);

            if (response.ok) {
                const data = await response.json();
                console.log('Received talking points:', data);
                const points = data.talkingPoints || [];
                setTalkingPoints(points);
                autoSelectBestPoints(points); // Auto-select the best points
                setStep('selection');
            } else {
                console.error('Failed to fetch talking points');
                setStep('selection');
                // Enhanced fallback with actual user data
                setTalkingPoints(fallbackPoints);
                autoSelectBestPoints(fallbackPoints);
            }
        } catch (error) {
            if (error.name === 'AbortError') {
                console.log('Request timed out');
            } else {
                console.error('Error fetching talking points:', error);
            }
            setStep('selection');
            // Same enhanced fallback
            setTalkingPoints(fallbackPoints);
            autoSelectBestPoints(fallbackPoints);
        }
    }, [hasMessage, getExistingMessage, job?.id]);

    const skipAnalysis = () => {
        // Enhanced fallback with actual user data
        setTalkingPoints(fallbackPoints);
        autoSelectBestPoints(fallbackPoints);
        setStep('selection');
    };

    const toggleTalkingPoint = (pointId) => {
        setSelectedPoints(prev => 
            prev.includes(pointId) 
                ? prev.filter(id => id !== pointId)
                : [...prev, pointId]
        );
    };

    const generateMessage = async () => {
        if (!messageGoal || selectedPoints.length === 0) {
            alert('Please select at least one talking point and choose your goal.');
            return;
        }

        setIsGenerating(true);
        setStep('generating');

        try {
            let selectedTalkingPointsText;
            
            if (talkingPoints.length > 0) {
                // Use actual talking points from API
                selectedTalkingPointsText = talkingPoints
                    .filter(point => selectedPoints.includes(point.id))
                    .map(point => point.text);
            } else {
                // Use fallback talking points
                const fallbackMap = {
                    'fallback1': 'Your relevant coursework and projects',
                    'fallback2': 'Your technical skills that match this role',
                    'fallback3': 'Your shared school connection'
                };
                selectedTalkingPointsText = selectedPoints
                    .filter(id => fallbackMap[id])
                    .map(id => fallbackMap[id]);
            }

            const response = await fetch('/api/messaging/generate-personalized-draft', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    jobId: job.id,
                    selectedTalkingPoints: selectedTalkingPointsText,
                    messageGoal: messageGoal,
                    messageLength: messageLength
                })
            });

            if (response.ok) {
                const data = await response.json();
                const message = data.message || 'Unable to generate message at this time.';
                setGeneratedMessage(message);
                setEditableMessage(message); // Set the editable version
                setStep('complete');

                onDraftGenerated?.(job.id, message);
            } else {
                alert('Failed to generate message. Please try again.');
                alert(response.error)
                setStep('selection');
            }
        } catch (error) {
            console.error('Error generating message:', error);
            alert('Error generating message. Please try again.');
            setStep('selection');
        } finally {
            setIsGenerating(false);
        }
    };

    const copyToClipboard = () => {
        navigator.clipboard.writeText(editableMessage).then(() => {
            alert('Message copied to clipboard!');
        });
    };

    if (!isOpen) return null;

    return (
        <div className="copilot-overlay">
            <div className="copilot-modal">
                <div className="copilot-header">
                    <h2>
                        <HiRocketLaunch size={24} style={{display: 'inline', marginRight: '8px'}} />
                        AI Outreach Co-Pilot
                    </h2>
                    <p>Craft the perfect personalized message with AI assistance</p>
                    <button className="close-btn" onClick={onClose}>×</button>
                </div>
                <div className="copilot-content">

                {step === 'loading' && (
                    <div className="loading-step">
                        <div className="spinner-large"></div>
                        <p>Analyzing your resume and job posting...</p>
                        <p className="generating-subtitle">This may take a few moments</p>
                        <button 
                            className="skip-btn" 
                            onClick={skipAnalysis}
                            style={{
                                marginTop: '20px',
                                background: 'transparent',
                                border: '1px solid #ccc',
                                borderRadius: '6px',
                                padding: '8px 16px',
                                fontSize: '12px',
                                cursor: 'pointer',
                                color: '#666'
                            }}
                        >
                            Skip Analysis
                        </button>
                    </div>
                )}

                {step === 'selection' && (
                    <div className="selection-step">
                        <div className="step-header">
                            <h3><HiBolt size={20} className="step-icon"/>Let's Build Your Message</h3>
                            <p>Select the strengths you want to highlight in your outreach</p>
                        </div>

                        <div className="talking-points-section">
                            <h4 className="copilot-section-title">
                                <HiLightBulb size={18} className="step-icon" />
                                Your Key Talking Points
                            </h4>
                            <div className="talking-points-grid">
                            {talkingPoints.length > 0 ? (
                                talkingPoints.map((point) => (
                                    <div 
                                        key={point.id}
                                        className={`talking-point ${selectedPoints.includes(point.id) ? 'selected' : ''}`}
                                        onClick={() => toggleTalkingPoint(point.id)}
                                    >
                                        <p className="talking-point-text">{point.text}</p>
                                    </div>
                                ))
                            ) : (
                                // Fallback talking points if API fails
                                <div className="fallback-points">
                                    <div 
                                        className={`talking-point ${selectedPoints.includes('fallback1') ? 'selected' : ''}`} 
                                        onClick={() => toggleTalkingPoint('fallback1')}
                                    >
                                        <p className="talking-point-text">My coursework in {user?.reported_college || 'computer science'} directly applies to this role</p>
                                    </div>
                                    <div 
                                        className={`talking-point ${selectedPoints.includes('fallback2') ? 'selected' : ''}`} 
                                        onClick={() => toggleTalkingPoint('fallback2')}
                                    >
                                        <p className="talking-point-text">My experience with {user?.skills?.[0] || 'programming'} and {user?.skills?.[1] || 'problem-solving'} matches your requirements</p>
                                    </div>
                                    <div 
                                        className={`talking-point ${selectedPoints.includes('fallback3') ? 'selected' : ''}`} 
                                        onClick={() => toggleTalkingPoint('fallback3')}
                                    >
                                        <p className="talking-point-text">As a fellow {user?.reported_college || 'university'} graduate, I understand the company culture</p>
                                    </div>
                                </div>
                            )}
                            </div>
                        </div>

                                                <div className="goal-selection">
                            <h4 className="copilot-section-title">
                                <HiBolt size={18} className="step-icon" />
                                Select Your Goal
                            </h4>
                            <div className="goal-buttons">
                                {['Learn about the role', 'Ask for a referral', 'General networking'].map((goal) => (
                                    <button
                                        key={goal}
                                        className={`goal-btn ${messageGoal === goal ? 'selected' : ''}`}
                                        onClick={() => setMessageGoal(goal)}
                                    >
                                        <span>{goal}</span>
                                    </button>
                                ))}
                            </div>
                        </div>

                        <div className="message-length-selection">
                            <h4 className="copilot-section-title">
                                <HiLightBulb size={18} className="step-icon" />
                                Message Length
                            </h4>
                            <div className="length-buttons">
                                {Object.entries(LINKEDIN_LIMITS).map(([key, config]) => (
                                    <button
                                        key={key}
                                        className={`length-btn ${messageLength === key ? 'selected' : ''}`}
                                        onClick={() => setMessageLength(key)}
                                    >
                                        <div className="length-label">{config.label}</div>
                                        <div className="length-range">{config.min}-{config.max} words</div>
                                    </button>
                                ))}
                            </div>
                        </div>

                        <div className="generate-section">
                            <button 
                                className="generate-btn"
                                onClick={generateMessage}
                                disabled={selectedPoints.length === 0 || !messageGoal}
                            >
                                <HiPencilSquare size={20} style={{marginRight: '8px'}} />
                                Generate Draft
                            </button>
                        </div>
                    </div>
                )}

                {step === 'generating' && (
                    <div className="generating-step">
                        <div className="spinner-large"></div>
                        <p>Crafting your personalized message...</p>
                        <p className="generating-subtitle">This may take a few moments</p>
                    </div>
                )}

                {step === 'complete' && (
                    <div className="complete-step">
                        <div className="message-header">
                            <h3>Your Personalized Message</h3>
                            <p>Here's your AI-generated outreach message:</p>
                        </div>

                        <div className="generated-message">
                            <div className="message-edit-header">
                                <span>✏️ Edit your message below:</span>
                            </div>
                            <textarea
                                className="message-editor"
                                value={editableMessage}
                                onChange={(e) => setEditableMessage(e.target.value)}
                                rows={8}
                                placeholder="Your generated message will appear here..."
                            />
                            <div className="character-count">
                                <span className="char-count">
                                    {editableMessage.trim().split(/\s+/).filter(word => word.length > 0).length} words
                                    <span style={{color: '#6c757d', marginLeft: '8px'}}>
                                        ({editableMessage.length} characters)
                                    </span>
                                </span>
                                <span className={`linkedin-limit ${(() => {
                                    const wordCount = editableMessage.trim().split(/\s+/).filter(word => word.length > 0).length;
                                    const limits = LINKEDIN_LIMITS[messageLength];
                                    if (wordCount > 200) return 'over-limit';
                                    if (wordCount >= limits.min && wordCount <= limits.max) return 'optimal';
                                    return 'suboptimal';
                                })()}`}>
                                    Target: {LINKEDIN_LIMITS[messageLength].min}-{LINKEDIN_LIMITS[messageLength].max} words
                                </span>
                            </div>
                        </div>

                        <div className="message-actions">
                            <button className="copy-btn" onClick={copyToClipboard}>
                                📋 Copy to Clipboard
                            </button>
                        </div>

                        <div className="message-tips">
                            <p><strong>Pro Tips:</strong></p>
                            <ul>
                                <li>✏️ Edit the message above to add your personal touch</li>
                                <li>🔍 Add specific details about the person you're messaging</li>
                                <li>📏 Keep your message under 300 characters for LinkedIn connection requests</li>
                                <li>⏰ Follow up within a week if you don't hear back</li>
                            </ul>
                        </div>
                    </div>
                )}
                </div>
            </div>
        </div>
    );
}

export default OutreachCoPilot; 