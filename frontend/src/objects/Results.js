import React, { useState, useRef, useEffect } from 'react';
import '../styles/ResultsPage.css'
import { RegisterPanel } from './RegisterPanel';
import { FiltersSection } from './FiltersSection';
import { JobTitles } from './JobTitles';
import { IndexHeader } from './IndexHeader';
import { updateColors, useTheme } from '../hooks/ThemeContext';
import { driver } from "driver.js";
import "driver.js/dist/driver.css";
import "../styles/TutorialDriver.css";
import { TourButton } from './TourButton';
import { BasicFooter } from './BasicFooter';

function Results() {
    const [user, setUser] = useState({}); //User object
    const [passChanged, setPassChanged] = useState(false); //Returning from password change
    const [jobs, setJobs] = useState({}); //List of jobs
    const [segments, setSegments] = useState(0); //How many segments of jobs listing
    const [perSegment, setPerSegment] = useState(0); //Jobs per segment
    const [loginRefresh, setLoginRefresh] = useState(false);
    const [total_jobs, setTotalJobs] = useState(0); //Total jobs available for user
    const [distinct_titles, setDistinctTitles] = useState([]); //List of common job titles in jobs list
    const [distinct_industries, setDistinctIndustries] = useState([]); //List of industries associated with jobs list
    const [error_message, setErrorMessage] = useState("");
    const [firstWait, setFirstWait] = useState(false); //if backend has responded (true) or not (false) [FOR JOB TITLES]
    const [userWait, setUserWait] = useState(false); //if backend has responded (true) or not (false) [FOR USER]
    const [refreshVal, setRefreshVal] = useState(0); //used for refreshing/recalling api call via useEffect
    const [premiumPopup, setPremiumPopup] = useState(false); //if premiumn popup is open or nah
    const [showErrorPopup, setShowErrorPopup] = useState(false);
    const [selectedJobType, setSelectedJobType] = useState('internships');
    const [filtersDisabled, setFiltersDisabled] = useState(false);

    const RESULTS_TUTORIAL = 'results_tutorial'; //localStorage key for the results page tutorial status
    const driverRef = useRef(driver({
        showProgress: true,
        disableActiveInteraction: true,
        overlayClickBehavior: () => {},
        smoothScroll: true,
        popoverClass: 'rezify-theme',
        onCloseClick: () => {
            localStorage.setItem(RESULTS_TUTORIAL, true);
            driverRef.current.destroy();
        },
        steps: [
            {
                popover: {
                    title: 'Welcome to Rezify!',
                    description: 'Let\'s take a tour to get you started.',
                    disableButtons: [],
                    nextBtnText: 'Start Tutorial',
                    prevBtnText: 'Skip Tutorial',
                    showProgress: false,
                    onPrevClick: () => {
                        driverRef.current.moveTo(13);
                    }
                }
            },
            // Discover tab
            {
                element: '#filter-All',
                popover: {
                    title: 'Discover',
                    description: 'The discover tab allows you to browse job recommendations based on your skillset.'
                },
                onHighlightStarted: () => {
                    document.getElementById('filter-All').click();
                }
            },
            // Favorites tab
            {
                element: '#filter-Favorites',
                popover: {
                    title: 'Favorites',
                    description: 'The Favorites tab allows you to view your saved jobs.',
                    onPrevClick: () => {
                        driverRef.current.moveTo(1);
                    }
                },
                onHighlightStarted: () => {
                    document.getElementById('filter-Favorites').click();
                }
            },
            // Applied-to tab
            {
                element: '#filter-Applied_to',
                popover: {
                    title: 'Applied To',
                    description: 'The Applied To tab allows you to view jobs you have previously applied to.'
                },
                onHighlightStarted: () => {
                    document.getElementById('filter-Applied_to').click();
                }
            },
            // Discover tab
            {
                element: '#filter-All',
                popover: {
                    title: 'Discover',
                    description: 'Let\'s take a deeper look at the Discover tab.'
                },
                onHighlightStarted: () => {
                    document.getElementById('filter-All').click();
                }
            },
            {
                element: '#filter-buttons',
                popover: {
                    title: 'Position Titles',
                    description: 'This menu allows you to select position titles to include in your recommended job.',
                    side: 'bottom'
                },
                disableActiveInteraction: false
            },
            {
                element: '#filter-buttons',
                popover: {
                    title: 'Selecting Titles',
                    description: 'Clicking a title will toggle whether it is included in your recommendations...',
                    side: 'bottom'
                },
                disableActiveInteraction: false
            },
            {
                element: '#filter-buttons',
                popover: {
                    title: 'Removing Titles',
                    description: '...and clicking the X will remove the title from your list altogether.',
                    side: 'bottom'
                },
                disableActiveInteraction: false
            },
            {
                element: '#filter-buttons',
                popover: {
                    title: 'Adding Titles',
                    description: 'We have suggested position titles based on your resume. You can also add your own by clicking the plus button.',
                    side: 'bottom'
                },
                disableActiveInteraction: false
            },
            {
                element: '#filter-button',
                popover: {
                    title: 'Search Filters',
                    description: 'You can also filter your recommendations by clicking this button.',
                    onNextClick: () => {
                        document.getElementById('filter-button').click();
                        driverRef.current.moveNext();
                    }
                }
            },
            {
                element: '#filterBox',
                popover: {
                    title: 'Search Filters',
                    description: 'You can filter by job type, availability, location, and industry.'
                },
                onDeselected: () => {
                    document.getElementById('filter-button').click();
                },
                onCloseClick: () => {
                    document.getElementById('filter-button').click();
                    driverRef.current.destroy();
                }
            },
            {
                element: '.job-card',
                popover: {
                    title: 'Jobs Recommendations',
                    description: 'You can browse job recommendations and apply to postings here',
                    onPrevClick: () => {
                        driverRef.current.moveTo(9);
                    }
                }
            },
            {
                element: '.star-checkbox-container',
                popover: {
                    title: 'Jobs Options',
                    description: 'You can also save jobs to your favorites, mark postings as applied to, and remove jobs from your recommendations.'
                }
            },
            {
                element: '.tour-button',
                popover: {
                    title: 'Review Tour',
                    description: 'You may review this tour anytime by clicking this button.',
                    side: 'top'
                }
            },
            {
                popover: {
                    title: 'You\'re all set!',
                    description: 'You now have everything you need to get started. Good luck in your internship search!',
                    onNextClick: () => {
                        localStorage.setItem(RESULTS_TUTORIAL, true);
                        driverRef.current.moveNext();
                    }
                }
            }
        ]
    }));

    useEffect(() => {
        const driverObj = driverRef.current;

        if (firstWait && userWait && user.id && !localStorage.getItem(RESULTS_TUTORIAL)) {
            driverObj.drive();
        }

        return () => {
            driverObj.destroy();
        }
    }, [firstWait, userWait, user.id]);

    const {setTheme} = useTheme()

    const refreshJobs = (newJobs=null, newUser=null, newtotaljobs=0) => {
        if (newJobs && newUser) {
            setJobs(newJobs)
            //Don't mess with selected filter, update everything else
            setUser(prev => (prev.filters ? {
                ...newUser,
                filters: {
                    ...newUser.filters,
                    'selected_filter': prev.filters['selected_filter']
                }
            } : newUser));
            setTotalJobs(newtotaljobs)
        } else {
            setRefreshVal(prev => prev + 1);
        }
    }

    useEffect(() => {
        /*
            Backend response:
            'jobs': jobs,
            'segments': segments,
            'per_segment': per_segment,
            'change': change,
            'login_refresh': login_refresh,
            'total_jobs': total_jobs,
            'distinct_titles': distinct_titles,
            'distinct_industries': distinct_industries,
            'get_jobs_error': get_jobs_error,
            'user': user.to_dict() if (type(user) == User) else None,
            'resume_error': resume_error,
            'colors': colors
        */
        setFirstWait(false);
        setUserWait(false);
        fetch("/api/results").then(async response => {
            //we should get colors, resume_info, error_message
            //get flask backend response
            if (response.ok) {
                const data = await response.json();
                //set colors: UNFINISHED
                if (data.colors) {
                    localStorage.setItem('theme-colors', JSON.stringify(data.colors));
                    updateColors(data.colors, setTheme);
                }

                if (data.jobs) {
                    setJobs(data.jobs)
                }

                if (data.segments) {
                    setSegments(data.segments)
                }

                if (data.per_segment) {
                    setPerSegment(data.per_segment)
                }

                if (data.change) {
                    setPassChanged(true)
                    setTimeout(() => setPassChanged(false), 4000);
                }

                if (data.login_refresh) {
                    setLoginRefresh(data.login_refresh)
                }

                if (data.total_jobs) {
                    setTotalJobs(data.total_jobs)
                }

                if (data.distinct_titles) {
                    setDistinctTitles((data.distinct_titles))
                }

                if (data.distinct_industries) {
                    setDistinctIndustries((data.distinct_industries))
                }

                if (data.get_jobs_error) {
                    setErrorMessage("Error Getting Jobs. Please Try Again.")
                    setShowErrorPopup(true);
                    setTimeout(() => setShowErrorPopup(false), 4000);
                }

                if (data.user) {
                    //Don't mess with selected filter, update everything else
                    setUser(prev => (prev.filters ? {
                        ...data.user,
                        filters: {
                            ...data.user.filters,
                            'selected_filter': prev.filters['selected_filter']
                        }
                    } : data.user));
                    if (data.user.resume_file == null) {
                        //if no resume file, redirect to index
                        window.location.href = '/';
                    }
                }

                if (data.resume_error) {
                    setErrorMessage("Error Parsing Resume. Please Try Again.")
                    setShowErrorPopup(true);
                    setTimeout(() => setShowErrorPopup(false), 4000);
                }

                if (data.error_message) {
                    setErrorMessage(data.error_message)
                    setShowErrorPopup(true);
                    setTimeout(() => setShowErrorPopup(false), 4000);
                }

                if (data.limit_error) {
                    setErrorMessage("Spam Search Detected! Please wait before searching again.")
                    setShowErrorPopup(true);
                    setTimeout(() => setShowErrorPopup(false), 4000);
                }

                if (data.redirect) {
                    window.location.href = data.redirect;
                }
            } else {
                setErrorMessage("Error: " + response.statusText)
                //error, prob shouldnt log in
            }
            setFirstWait(true);
            setUserWait(true);
        });
    }, [refreshVal]);

    return (<>
        {/*=== Register Popup Overlay ===*/}
        {firstWait && !(user.id) &&
            <div class="popup-overlay">
                <div class="popup-container">
                    <h2>Register to View Results</h2>
                    <RegisterPanel/>
                </div>
            </div>
        }
        {/*=====================*/}
        {firstWait && userWait
            ? <TourButton driver={driverRef.current}></TourButton>
            : <></>
        }

        {/*=== Premium Popup Overlay ===*/}
        {premiumPopup &&
            <div class="popup-overlay">
                <div class="popup-container">
                    <h2>Upgrade to premium to use this feature!</h2>
                    <div style={{display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center'}}>
                        <a href={"/plans?redirect=results"} className='upgrade-button' style={{width: 120, margin: 10}}>Upgrade</a>
                        <button className='disabled-refresh-button' style={{width: 80, margin: 10, backgroundColor: '#555', cursor: 'pointer'}} onClick={() => {
                            setPremiumPopup(false);
                        }}>Close</button>
                    </div>

                </div>
            </div>
        }
        {/*=====================*/}

        {/*=== Results Header ===*/}
        <header>
            <div class="top-header" id="top-header">
                <IndexHeader user={user} firstWait={userWait}/>
            </div>
            <div class="user-filter-header">
                <div class="top-links">
                        {(user.plan === "premium" || true) && <div class="filter-buttons-inline">
                            <button id="filter-All" onClick={() => {
                                setUser(prev => ({
                                    ...prev,
                                    filters: {
                                        ...prev.filters,
                                        'selected_filter': 'All'
                                    }
                                }));
                            }} type="button"
                                    className={"filter-option " + ((user.filters && user.filters['selected_filter'] === 'All') ? "selected" : "")}>
                                Discover
                            </button>
                            <button id="filter-Favorites" onClick={() => {
                                    setUser(prev => ({
                                        ...prev,
                                        filters: {
                                            ...prev.filters,
                                            'selected_filter': 'Favorites'
                                        }
                                    }));
                            }}
                            type="button"
                                    className={"filter-option " + ((user.filters && user.filters['selected_filter'] === 'Favorites') ? "selected" : "")
                                    }>
                                Favorites
                            </button>
                            <button id="filter-Applied_to" onClick={() => {
                                    setUser(prev => ({
                                        ...prev,
                                        filters: {
                                            ...prev.filters,
                                            'selected_filter': 'Applied_to'
                                        }
                                    }));
                            }} type="button"
                                    className={"filter-option " + ((user.filters && user.filters['selected_filter'] === 'Applied_to') ? "selected" : "")
                                    }>
                                Applied To
                            </button>
                        </div>}
                </div>
            </div>
        </header>
        {/*=====================*/}

        { passChanged &&
            <div id="success-popup" class="success-popup">Password successfully changed</div>
        }

        {showErrorPopup && (
                <div className="error-popup">
                    {error_message}
                </div>
        )}

        <div id="container-loading-animation" style={{'display': 'none'}}>
            <div class="container-loading-spinner"></div>
        </div>

        {/* Intership / Entry Level Toggle
        {(user.filters && user.filters['selected_filter'] === 'All') && (
            <>
                <div class="top-type-container">
                    <h3>Looking For: </h3>
                    <div class="top-type-filter">
                        <div class="top-links">
                                <button id="filter-internships" onClick={() => {
                                    setSelectedJobType('internships')
                                }} type="button"
                                        className={"filter-option " + ((selectedJobType === 'internships') ? "selected" : "")}>
                                    Internships / Co-ops
                                </button>
                                <button id="filter-entry-level" onClick={() => {
                                    setSelectedJobType('entry_level')
                                }}
                                type="button"
                                        className={"filter-option " + ((selectedJobType === 'entry_level') ? "selected" : "")
                                        }>
                                    Entry Level Positions
                                </button>
                        </div>
                    </div>
            </div>
            </>
        )}
        */}

        <div class="container">

            {selectedJobType === 'internships' && (
                <>

                    <div id="filter-section" class="filter-section">
                        <FiltersSection
                        user={user}
                        distinct_industries={distinct_industries}
                        distinct_titles={distinct_titles}
                        setUser={setUser}
                        refreshJobs={refreshJobs}
                        setFirstWait={setFirstWait}
                        firstWait={firstWait}
                        setErrorMessage={setErrorMessage}
                        setShowErrorPopup={setShowErrorPopup}
                        selectedJobType={selectedJobType}
                        filtersDisabled={filtersDisabled}
                        setFiltersDisabled={setFiltersDisabled}
                        />
                    </div>

                    {!firstWait &&
                        <div id="job-cards-container" class="job-cards-container">
                            <div id="loading-animation">
                                <div class="loading-spinner"></div>
                            </div>
                        </div>
                    }

                    <div id="refresh-animation" style={{'display': 'none', 'text-align': 'center'}}>
                        <div class="loading-spinner" style={{'margin': 0}}></div>
                        <p style={{'color': 'var(--primary-color)', 'font-weight': 'bold', 'margin-top': '10px'}}>Getting up-to-date results...</p>
                    </div>
                    {firstWait &&
                    <div id="job-cards-container" class="job-cards-container">
                        {
                        user.filters ?
                        /* NORMAL USER :) */
                        <JobTitles user={user}
                        jobs={user.filters['selected_filter'] === 'All' ? jobs : ( user.filters['selected_filter'] === 'Favorites' ? user.favorites : user.applied_to)}
                        originalLimit={segments * perSegment}
                        total_jobs={user.filters['selected_filter'] === 'All' ? total_jobs : ( user.filters['selected_filter'] === 'Favorites' ? (user.favorites ? user.favorites.length : 0) : (user.applied_to ? user.applied_to.length : 0))}
                        originalSegments={segments}
                        finding={user.filters['selected_filter'] === 'All'}
                        setUser={setUser}
                        setJobs={setJobs}
                        setTotalJobs={setTotalJobs}
                        refreshJobs={refreshJobs}
                        setFirstWait={setFirstWait}
                        setPremiumPopup={setPremiumPopup}
                        setErrorMessage={setErrorMessage}
                        setShowErrorPopup={setShowErrorPopup}
                        selectedJobType={selectedJobType}
                        filtersDisabled={filtersDisabled}
                        setFiltersDisabled={setFiltersDisabled}
                        />
                        :
                        /* UNINITIALIZED USER !!!! */
                         <JobTitles user={user}
                            jobs={jobs}
                            originalLimit={25}
                            total_jobs={total_jobs}
                            originalSegments={segments}
                            finding={true}
                            setUser={()=>{}}
                            setJobs={()=>{}}
                            refreshJobs={()=>{}}
                            setFirstWait={setFirstWait}
                            setPremiumPopup={setPremiumPopup}
                            selectedJobType={selectedJobType}
                            filtersDisabled={filtersDisabled}
                            setFiltersDisabled={setFiltersDisabled}
                            />}

                    </div>
                    }

                </>
            )}
            {selectedJobType === 'entry_level' && (
                <>
                    <section className="coming-soon">
                      <img
                        className="cs-logo"
                        src={"/static/rezify_logo2.png"}
                        alt="Rezify logo"
                      />

                      <h1 className="cs-title">Coming Soon…</h1>
                      <p className="cs-sub">Rezify will feature all entry level positions for new graduates in the near future!</p>
                      <p className="cs-sub">Follow our Instagram to stay tuned</p>

                      <a
                        className="cs-cta"
                        href="https://www.instagram.com/rezify.ai/"
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        Follow @rezify.ai
                      </a>

                      <div className="insta-embed">
                        <blockquote
                          className="instagram-media"
                          data-instgrm-permalink="https://www.instagram.com/rezify.ai/?utm_source=ig_embed&utm_campaign=loading"
                          data-instgrm-version="14"
                          style={{
                            background: "#FFF",
                            border: 0,
                            borderRadius: 12,
                            boxShadow:
                              "0 0 1px 0 rgba(0,0,0,.5), 0 8px 24px 0 rgba(0,0,0,.15)",
                            margin: "8px auto",
                            maxWidth: 540,
                            minWidth: 326,
                            width: "100%",
                          }}
                        >
                          {/* Instagram will replace this blockquote */}
                        </blockquote>
                      </div>
                    </section>
                </>

            )}

            {user.id && <a href="/index?noredir=1" class="back-button">Back to Search</a>}
        </div>
        <BasicFooter/>
    </>)
}

export {Results}