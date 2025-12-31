import React, { useState, useRef, useEffect, useMemo } from 'react';
import DOMPurify from 'dompurify';
import { useNavigate } from 'react-router-dom';
import { HiOutlineUserGroup, HiSparkles } from 'react-icons/hi2';
import OutreachNavigator from './OutreachNavigator';
import OutreachCoPilot from './OutreachCoPilot';
import '../styles/JobTitles.css';

function JobTitles({
                    user = {}, //User object
                    jobs = [], //Jobs list
                    originalLimit = 25, //Original limit on first page load, usually 25 jobs
                    originalSegments = 1, //Orignal # of segments on first page load
                    total_jobs = 0, //Total jobs
                    finding = true, //True if on discover page (selected_filters == 'All'), False if not
                    login_refresh = false,
                    setUser = ((prev)=>{}), //Small frontend update on user object based on frontend action
                    setJobs = ((prev) => {}), //Small frontend update on jobs list based on frontend action
                    setTotalJobs = ((prev) => {}), //Small frontend update on jobs list based on frontend action
                    refreshJobs=(()=>{}), //Refresh jobs on load more 
                    setFirstWait=()=>{}, //Set page loading
                    setPremiumPopup=()=>{}, //Show premium popup
                    setErrorMessage=()=>{}, //Set error message
                    setShowErrorPopup=()=>{}, //Show the error popup
                    selectedJobType = '',
                    filtersDisabled = false,
                    setFiltersDisabled = () => {}
                }) {
    const [preDesc, setPreDesc] = useState([]); //Jobs waiting for backend response on full description
    const [showDesc, setShowDesc] = useState([]); //Jobs ready to display backend response on full description
    const [fullDesc, setFullDesc] = useState({}); //Dictionary of full descriptions (key: jobid, value: full desc)
    const [loadingMore, setLoadingMore] = useState(false); //In the process of loading more
    const [loadFails, setLoadFails] = useState([]); //collection of logos that failed to load
    const perSegment = originalLimit / originalSegments;
    const [limit, setLimit] = useState(originalLimit); //Current limit of jobs, starts at originalLimit
    const [segments, setSegments] = useState(originalSegments); //Current segments of jobs, starts at originalSegments
    const [removePopupJob, setRemovePopupJob] = useState(null); // null or job object
    const [removeReason, setRemoveReason] = useState('');        // selected reason
    const [fadingOutJobId, setFadingOutJobId] = useState(null);  // job id to fade out
    const [pendingApplyPopupJob, setPendingApplyPopupJob] = useState(null);  // job object for pending apply popup
    const [showApplyPopup, setShowApplyPopup] = useState(false);  // whether to show the apply popup
    // Outreach Co-Pilot state
    const [showNavigator, setShowNavigator] = useState(false);
    const [showCoPilot, setShowCoPilot] = useState(false);
    const [selectedJob, setSelectedJob] = useState(null);
    const [messageDisabled, setMessageDisabled] = useState({}); // { [jobIdStr]: true }
    const [msgCount, setMsgCount] = useState({}); // { [jobIdStr]: number }
    const [msgClicksCount, setMsgClicksCount] = useState({}); // total message button clicks

    const [notesDrafts, setNotesDrafts] = useState({}); // { [jobIdStr]: string }
    const [notesSaveState, setNotesSaveState] = useState({});
    const [statusFilter, setStatusFilter] = useState(
      ['applied', 'interviewing', 'offer', 'accepted', 'rejected'] // default = All
    );
    const [notesSavedTimeById, setNotesSavedTimeById] = useState({}); // { [jobIdStr]: isoString }


    const formatSavedTimeLocal = (isoUtc) => {
      if (!isoUtc) return "";
      const d = new Date(isoUtc);
      if (Number.isNaN(d.getTime())) return "";
      return d.toLocaleString(undefined, {
        month: "short",
        day: "numeric",
        hour: "numeric",
        minute: "2-digit",
      });
    };


    const closeNavigator = (opts = {}) => {
      setShowNavigator(false);
      if (!opts.preserveJob) setSelectedJob(null);
    };

    const STATUS_OPTIONS = [
      { key: 'applied',       label: 'Applied' },
      { key: 'interviewing',  label: 'Interviewing' },
      { key: 'offer',         label: 'Offer Received' },
      { key: 'accepted',      label: 'Accepted' },
      { key: 'rejected',      label: 'Rejected' },
    ];


    const handleDraftGenerated = (jobId, message) => {
      const idStr = String(jobId);

      // 1) disable the button for this job
      setMessageDisabled(prev => ({ ...prev, [idStr]: true }));

      // 2) optimistic update to user.messages_generated so the card shows it immediately
      setUser(prev => {
        const prevList = Array.isArray(prev?.messages_generated) ? prev.messages_generated : [];
        const idx = prevList.findIndex(m => String(m.job_id ?? m.id) === idStr);

        const nextList = idx >= 0
          ? prevList.map((m, i) => i === idx ? { ...m, message } : m) // update existing
          : [...prevList, { id: jobId, message }];                    // or append

        return { ...prev, messages_generated: nextList };
      });
    };

    const hasGeneratedMessage = (jobish) => {
      if (!jobish) return false;
      const idStr = String(jobish.id ?? jobish.job_id);
      if (!idStr) return false;

      // trust explicit list if present
      if (Array.isArray(user?.messages_generated)) {
        const found = user.messages_generated.some(m =>
          String(m.job_id ?? m.id) === idStr
        );
        if (found) return true;
      }

      // fall back to count map
      return (msgCount?.[idStr] || 0) >= 1;
    };


    useEffect(() => {
      if (!Array.isArray(user?.messages_generated)) return;

      const ids = user.messages_generated
        .map(it => (typeof it === "object" ? (it.job_id ?? it.id) : it))
        .filter(Boolean)
        .map(String);

      const counts = ids.reduce((acc, id) => {
        acc[id] = (acc[id] || 0) + 1;
        return acc;
      }, {});

      setMsgCount(counts);
    }, [user?.messages_generated]);





    const navigate = useNavigate();

    const advertisePremium = () => {
        //navigate("/plans?redirect=results"); OPTION 1: just navigate them to the plans page
        setPremiumPopup(true);
    }

    const doRefresh = () => {
        setFirstWait(false);
        setFiltersDisabled(true);

        fetch(`/api/refresh_jobs`)
            .then(response => {
                if (response.text !== 'Fail') {
                    response.json()
                        .then(data => {
                            setJobs(data.jobs);
                            setLimit(data.per_segment * data.segments);
                            setSegments(data.segments);
                            setTotalJobs(data.total_jobs);
                            setUser(data.user);
                            setFirstWait(true);

                            if (data.limit_error) {
                                setErrorMessage("Spam Search Detected! Please wait before searching again.");
                                setShowErrorPopup(true);
                                setTimeout(() => setShowErrorPopup(false), 4000);
                            }

                            if (data.get_jobs_error) {
                                setErrorMessage("Error fetching jobs. Please try again.");
                                setShowErrorPopup(true);
                                setTimeout(() => setShowErrorPopup(false), 4000);
                            }
                        })
                        .catch(error => {
                            alert("Error loading more");
                            setFirstWait(true);
                        });
                } else {
                    document.location.href = "/";
                }
            })
            .catch(() => {
                setFirstWait(true);
            })
            .finally(() => {
                setFiltersDisabled(false);
            });
    };


    useEffect((login_refresh) => {
        if (login_refresh) {
            doRefresh();
        }
    }, [login_refresh]);

    const updateFilters = (parameter, value) => {
        setFirstWait(false);
        setFiltersDisabled(true);

        fetch(`/api/update_filters?parameter=${parameter}&value=${value}`)
            .then(data => {
                if (data === "Fail") {
                    window.location.href = '/set_session_id'; //Session expired
                    setFirstWait(true);
                } else {
                    if (data.ok) {
                        data.json().then(jsondata => {
                            if (jsondata.limit_error) {
                                setErrorMessage("Spam Search Detected! Please wait before searching again.");
                                setShowErrorPopup(true);
                                setTimeout(() => setShowErrorPopup(false), 4000);
                            }
                            if (jsondata.get_jobs_error) {
                                setErrorMessage("Error fetching jobs. Please try again.");
                                setShowErrorPopup(true);
                                setTimeout(() => setShowErrorPopup(false), 4000);
                            }
                            if (jsondata.jobs) {
                                refreshJobs(jsondata.jobs, jsondata.user, jsondata.total_jobs);
                                setFirstWait(true);
                            }
                        });
                    } else {
                        //some error occured
                        setFirstWait(true);
                    }
                }
            })
            .catch(() => {
                setFirstWait(true);
            })
            .finally(() => {
                setFiltersDisabled(false);
            });
    };

    const sortBy = () => {
        const sortValue = document.querySelector('input[name="sort"]:checked').value;
        updateFilters('sort_by', sortValue)
    }

    const ImageWithFailsafe = ({logo, letter}) => {
        if (logo) {
            return (loadFails.includes(logo) ? 
                <div class="fallback-logo"> { letter } </div>
                :
                <img src={ logo } alt="Company Logo" class="company-logo"
                  onLoad={() => {}}
                  onError={() => {
                     setLoadFails(prev => [...prev, logo]);
                  }}
                />
              );
        } else {
            return <div class="fallback-logo">
            { letter }
        </div>;
        }
    }

    async function addToFavoritesPost(job_id) {
        const isFavorite = user.favorites.map(val => val.id).includes(job_id);
        const onFavoritesTab = user.filters?.selected_filter === 'Favorites';

        if (isFavorite && onFavoritesTab) {
            // Fade out for removal in Favorites tab
            setFadingOutJobId(job_id);
            setTimeout(() => {
                setUser(prev => ({
                    ...prev,
                    favorites: prev.favorites.filter(val => val.id !== job_id)
                }));
                setFadingOutJobId(null);
            }, 400);
        } else {
            // Optimistically update favorites list
            setUser(prev => ({
                ...prev,
                favorites: isFavorite
                    ? prev.favorites.filter(val => val.id !== job_id)
                    : [...prev.favorites, jobs.find(val => val.id === job_id)]
            }));
        }

        try {
            const response = await fetch('/api/add_favorite', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ job_id }),
            });

            const result = await response.json();

            if (result.status === 'session_fail') {
                window.location.href = '/results';
                return;
            }

            if (result.status === 'fail') {
                // Revert UI change
                setUser(prev => ({
                    ...prev,
                    favorites: isFavorite
                        ? [...prev.favorites, jobs.find(val => val.id === job_id)]
                        : prev.favorites.filter(val => val.id !== job_id)
                }));

                // Show popup
                if (result.message) {
                    setErrorMessage(result.message);
                    setShowErrorPopup(true);
                    setTimeout(() => setShowErrorPopup(false), 2000);
                }
            }
        } catch (error) {
            // You can also show a fallback error here
            setErrorMessage("Something went wrong.");
            setShowErrorPopup(true);
            setTimeout(() => setShowErrorPopup(false), 2000);
        }
    }




    async function addToAppliedPost(job_id) {
        const isApplied = user.applied_to.map(val => val.id).includes(job_id);
        const jobObject = jobs.find(val => val.id === job_id);

        // Optimistic UI: start fade out
        setFadingOutJobId(job_id);

        setTimeout(() => {
            // Update frontend state optimistically
            setUser(prev => ({
                ...prev,
                applied_to: isApplied
                    ? prev.applied_to.filter(val => val.id !== job_id)
                    : [...prev.applied_to, jobObject]
            }));
            setFadingOutJobId(null); // Reset fade
        }, 600);

        try {
            const response = await fetch('/api/add_applied_to', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ job_id }),
            });

            const result = await response.json();

            if (result.status === 'session_fail') {
                window.location.href = '/results';
                return;
            }

            if (result.status === 'fail') {
                // Revert UI update
                setUser(prev => ({
                    ...prev,
                    applied_to: isApplied
                        ? [...prev.applied_to, jobObject]
                        : prev.applied_to.filter(val => val.id !== job_id)
                }));

                // Show popup
                if (result.message) {
                    setErrorMessage(result.message);
                    setShowErrorPopup(true);
                    setTimeout(() => setShowErrorPopup(false), 2000);
                }
            }
        } catch (error) {
            // Show fallback popup
            setErrorMessage("Something went wrong.");
            setShowErrorPopup(true);
            setTimeout(() => setShowErrorPopup(false), 2000);
        }
    }

    async function updateAppliedStatus(job_id, newStatus) {
      try {
        const response = await fetch('/api/update_applied_status', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            job_id,
            status: newStatus,  // e.g. 'applied', 'interviewing', 'offer', 'accepted', 'rejected'
          }),
        });

        const result = await response.json();

        if (result.status === 'session_fail') {
          window.location.href = '/results';
          return;
        }

        if (result.status !== 'success') {
          // Backend said something went wrong
          setErrorMessage(result.message || 'Unable to update job status.');
          setShowErrorPopup(true);
          setTimeout(() => setShowErrorPopup(false), 2000);
        }
      } catch (error) {
        // Network / unexpected error
        setErrorMessage('Something went wrong updating job status.');
        setShowErrorPopup(true);
        setTimeout(() => setShowErrorPopup(false), 2000);
      }
    }

    async function saveNotesToJob(job_id, notes, jobIdStr) {
      // Safety: enforce char limit before sending
      if (notes.length > 300) {
        setErrorMessage("Notes must be 300 characters or less.");
        setShowErrorPopup(true);
        setTimeout(() => setShowErrorPopup(false), 2000);
        return;
      }

      try {
        const response = await fetch('/api/save_notes_to_job', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            job_id: job_id,
            notes: notes,
          }),
        });

        const result = await response.json();

        if (result.status === 'session_fail') {
          window.location.href = '/results';
          return;
        }

        if (result.status === 'success') {
          const savedIso = result.notes_saved_time || null;

          // Update the job object locally so persistedNotes matches
          setJobs(prev =>
            prev.map(j =>
              j.id === job_id ? { ...j, user_notes: notes, notes_saved_time: savedIso } : j
            )
          );

          // update UI timestamp source-of-truth immediately (prevents old timestamp flash)
          if (savedIso) {
            setNotesSavedTimeById(prev => ({ ...prev, [jobIdStr]: savedIso }));
          } else {
            setNotesSavedTimeById(prev => {
              const next = { ...prev };
              delete next[jobIdStr];
              return next;
            });
          }

          setNotesSaveState(prev => ({
            ...prev,
            [jobIdStr]: 'saved',
          }));
        } else {
          setNotesSaveState(prev => ({ ...prev, [jobIdStr]: 'unsaved' }));
          setErrorMessage(result.message || "Unable to save notes.");
          setShowErrorPopup(true);
          setTimeout(() => setShowErrorPopup(false), 2000);
        }
      } catch (error) {
        setNotesSaveState(prev => ({ ...prev, [jobIdStr]: 'unsaved' }));
        setErrorMessage("Something went wrong saving notes.");
        setShowErrorPopup(true);
        setTimeout(() => setShowErrorPopup(false), 2000);
      }
    }

    // Toggle a single status in the filter
    const toggleStatusFilter = (key) => {
      setStatusFilter(prev => {
        if (prev.includes(key)) {
          // remove it
          return prev.filter(k => k !== key);
        } else {
          // add it
          return [...prev, key];
        }
      });
    };

    // Toggle the "All" checkbox
    const toggleAllStatuses = (checked) => {
      if (checked) {
        // select all statuses
        setStatusFilter(STATUS_OPTIONS.map(opt => opt.key));
      } else {
        // clear all (no jobs will show)
        setStatusFilter([]);
      }
    };

    // const nextrefresh = new Date(new Date(user.last_refresh).getTime() + 1000 * 60 * 60 * 24 * 7) 1000 * 60 * 1
    let user_last_refreshISO;
    let nextrefresh;

    if (user.last_refresh) {
        user_last_refreshISO = user.last_refresh.replace(' ', 'T').split('.')[0] + 'Z';
    } else {
        // Default to current time if user.last_refresh is null
        user_last_refreshISO = new Date().toISOString();
    }

    // Next refresh = user_last_refresh + 7 days
    nextrefresh = new Date(new Date(user_last_refreshISO).getTime() + 1000 * 60 * 60 * 24 * 7);

    // --- time helpers ---
    const TWO_HOURS_MS = 2 * 60 * 60 * 1000;

    let timeAgoText = "";
    let withinTwoHours = false;

    if (user.last_refresh) {
      const lastRefreshDate = new Date(user_last_refreshISO);
      const now = new Date();
      const diffMs = now - lastRefreshDate;

      withinTwoHours = diffMs < TWO_HOURS_MS;

      if (withinTwoHours) {
        timeAgoText = "Jobs Up to Date!";
      } else {
        const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
        const diffHours = Math.floor((diffMs % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
        timeAgoText = `Jobs updated ${diffDays} day${diffDays !== 1 ? 's' : ''}, ${diffHours} hr${diffHours !== 1 ? 's' : ''} ago`;
      }
    }

    // Keep your existing 7‑day rule, but also block refresh if within 2 hours
    const finalCanRefresh = (user.plan === "premium" || new Date() >= nextrefresh) && !withinTwoHours;

    const filteredJobs = useMemo(() => {
      let list = jobs.filter(job => !user.removed_jobs?.some(j => j.id === job.id));

      if (user.filters?.selected_filter === 'Applied_to') {
        list = list.filter(job => {
          const statusKey = (job.user_status || 'applied').toLowerCase();
          return statusFilter.includes(statusKey);
        });
      }

      return list;
    }, [jobs, user.removed_jobs, user.filters?.selected_filter, statusFilter]);


    return (<>
        {/* Status Filter - only on Applied_to tab */}
        {user.filters?.selected_filter === 'Applied_to' && (
          <div className="applied-status-filter">
            <span className="applied-status-filter-label"><strong>Filter by status:</strong></span>

            <label className="applied-status-filter-item">
              <input
                type="checkbox"
                checked={statusFilter.length === STATUS_OPTIONS.length}
                onChange={(e) => toggleAllStatuses(e.target.checked)}
              />
              All
            </label>

            {STATUS_OPTIONS.map(opt => (
              <label key={opt.key} className="applied-status-filter-item">
                <input
                  type="checkbox"
                  checked={statusFilter.includes(opt.key)}
                  onChange={() => toggleStatusFilter(opt.key)}
                />
                {opt.label}
              </label>
            ))}
          </div>
        )}
        {selectedJobType === 'internships' && (
          <p>
            {finding ? "Internships Found:" : "Total:"}{" "}
            {user.filters?.selected_filter === 'Applied_to'
              ? filteredJobs.length
              : total_jobs < 300
                ? total_jobs
                : "300+"}
          </p>
        )}

        {selectedJobType === 'new_grad' && (
          <p>
            {finding ? "Jobs Found:" : "Total:"}{" "}
            {user.filters?.selected_filter === 'Applied_to'
              ? filteredJobs.length
              : total_jobs < 300
                ? total_jobs
                : "300+"}
          </p>
        )}
        {finding &&
        <div class="inline-buttons-container">
            <form id="sortFilterForm" method="post" action="{{ url_for('update_filters') }}">
                <input type="hidden" name="parameter" value="sort_buttons" />
                <div class="sort-buttons">
                    <label style={{cursor: "pointer"}}>
                        <input type="radio" name="sort" value="Date" defaultChecked={user.filters && (user.filters['sort_by'] === 'Date')} style={{cursor: "pointer"}} disabled={!user.plan} onClick={() => {
                            sortBy();
                        }}/>
                        Sort by Date
                        <div class="tooltip">{"Sort jobs by the most recent date"}</div>
                    </label>
                    <label style={{cursor: "pointer"}}>
                        <input type="radio" name="sort" value="Relevance" defaultChecked={user.filters && (user.filters['sort_by'] === 'Relevance')} style={{cursor: "pointer"}} disabled={!user.plan} onClick={() => {
                            sortBy();
                        }}/>
                        Sort by Relevance
                        <div class="tooltip">{"Sort jobs by our AI-powered matching algorithm"}</div>
                    </label>
                </div>
            </form>

            {user.filters && user.filters['selected_filter'] === 'All' &&
                <div class="refresh-jobs-container" style={{ display: 'flex', alignItems: 'center', marginLeft: 'auto', gap: '10px' }}>
                    {/* Last refresh text */}
                        {user.last_refresh && (
                            <span style={{ fontSize: '0.9em', color: '#555' }}>
                                {timeAgoText}
                            </span>
                        )}
                        {/* Refresh button */}
                        <button
                          type="submit"
                          className={!finalCanRefresh ? "disabled-refresh-button" : "refresh-button"}
                          onClick={() => {
                            if (finalCanRefresh) {
                              doRefresh();
                            } else {
                              if (withinTwoHours) {
                                //
                              } else {
                                advertisePremium();
                              }
                            }
                          }}
                        >
                          <label style={{ cursor: finalCanRefresh ? "pointer" : "default" }}>
                            Refresh Jobs
                            {user.last_refresh !== null && (
                              <div className="tooltip">
                                {withinTwoHours ? (
                                  (() => {
                                    const last = new Date(user_last_refreshISO);
                                    const minsLeft = Math.max(
                                      0,
                                      Math.ceil((TWO_HOURS_MS - (new Date() - last)) / (1000 * 60))
                                    );
                                    return <span>Up to date. Try again in ~{minsLeft} min.</span>;
                                  })()
                                ) : (
                                  <>
                                    {finalCanRefresh ? (
                                      <span>{timeAgoText}</span>
                                    ) : (
                                      <>
                                        <p>Upgrade to premium to use this</p>
                                        <p>Next Refresh: {nextrefresh.toLocaleString()}</p>
                                      </>
                                    )}
                                  </>
                                )}
                              </div>
                            )}
                          </label>
                        </button>
                        
                </div>
            }
        </div>
        }

        {filteredJobs
            .filter(job => !user.removed_jobs?.some(j => j.id === job.id)) // hide removed jobs
            .filter(job => {
              if (user.filters?.selected_filter !== 'Applied_to') return true;

              const statusKey = (job.user_status || 'applied').toLowerCase();
              return statusFilter.includes(statusKey);
            })
            .slice(0, limit)
            .map(job => {
        const recentlyAdded = (Math.abs(new Date() - new Date(job.date_posted)) / 1000 / 60 / 60 / 24) < 3;
        const jobIdStr = String(job.id ?? job.job_id);
        const totalCount = msgCount[jobIdStr] || 0;
        const msgAlreadyGenerated = totalCount >= 1;
        const totalMsgClicks = msgClicksCount[jobIdStr] || 0;
        const normalizedStatus = (job.user_status || 'applied').toLowerCase();
        const persistedNotes = job.user_notes ?? job.notes ?? '';
        const draft = notesDrafts[jobIdStr];
        const currentNotes = draft !== undefined ? draft : persistedNotes;
        const savedState = notesSaveState[jobIdStr];
        const isUnsaved = savedState
          ? savedState === 'unsaved'
          : currentNotes !== persistedNotes;
        const savedIso = notesSavedTimeById[jobIdStr] ?? job.notes_saved_time ?? null;
        const savedTimeText = savedIso ? formatSavedTimeLocal(savedIso) : "";


        return (
            ((finding && user.applied_to && user.applied_to.map(apil => apil.id).includes(job.id)) || (finding && user.filters && user.filters['selected_titles'].length >= 1 && !user.filters['selected_titles'].includes(job.job_rec)))  ? 
            (<></>)
            
            :

        <div style={{'background-color': recentlyAdded ? 'color-mix(in srgb, white, var(--primary-color) 20%)' : 'white'}} className={`job-card ${fadingOutJobId === job.id ? 'fade-out' : ''}`}>
            {user.applied_to &&
            <div class="star-checkbox-container">
                {/* Container containing the star, checkbox, and x at the top right of the job card */}

                {/* The star icon to add job to favorites */}
                <button tabindex="0" className={"star" + (user.favorites.map(val => val.id).includes(job.id) ? " filled" : "")} data-job-id={ job.id } onClick={() => {
                    addToFavoritesPost(job.id);
                }}>&#9733;</button>
                <div class="tooltip">Add Job To Favorites List</div>

                {/* The checkbox to mark job as applied to */}
                <label>
                <input type="checkbox" aria-label='Applied' checked={user.applied_to.map(apil => apil.id).includes(job.id)} data-job-id={ job.id } id={ job.id } onChange={(event) => {
                   addToAppliedPost(job.id);
                }}/>
                <div class="tooltip">Mark Job As Applied To</div>
                </label>

                {/* The 'X' on the job card to remove it from the list */}
                <button tabindex="0" className="remove-x" onClick={() => {
                    if ((user && user.plan === "premium") || (user && user.removed_jobs && user.removed_jobs.length < 5)) {
                        setRemovePopupJob(job);
                    } else {
                        advertisePremium();
                    }
                }}>x</button>
                <div class="tooltip">Remove This Job From Results</div>
            </div>

            }

            
            {/*=== Job Title & Icon ===*/}
            <div class="logo-title-container">
                {job.company_url ?
                    <a href={ job.company_url } target="_blank" style={{'text-decoration': 'none', 'color': 'inherit'}}>
                        <ImageWithFailsafe  logo={job.company_logo} letter={job.company[0]}/>
                    </a>
                :
                <>
                    <ImageWithFailsafe  logo={job.company_logo} letter={job.company[0]}/>
                    </>
                }

                <h2 class="job-title">{ job.title }</h2>

                {/*=== Recently Added ===*/}
                {
                    recentlyAdded ? 
                    <h3 className="recently-posted-badge">⭐️ Recently Posted! ⭐️</h3>
                    :
                    <></>
                }
                {/*========================*/}
            </div>
            {/*========================*/}

            {/* Job Status Buttons - only show on "Applied_to" tab */}
            {user.filters?.selected_filter === 'Applied_to' && (
              <div className="job-status-container">
                <div className="job-status-pills">
                  {STATUS_OPTIONS.map((opt) => (
                    <button
                      key={opt.key}
                      type="button"
                      className={
                        `status-pill ${normalizedStatus === opt.key ? 'is-selected' : ''}`
                      }
                      onClick={() => {
                      if (normalizedStatus === opt.key) return;

                      job.user_status = opt.key; // Local visual update

                      setJobs(prev =>
                        prev.map(j => (j.id === job.id ? { ...j, user_status: opt.key } : j))
                      );

                      updateAppliedStatus(job.id, opt.key);
                      }}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/*=== Job Title & Icon ===*/}
            { job.company_url !== null ?
                <p><strong>Company: </strong>
                    <a href={ job.company_url } target="_blank" style={{'text-decoration': 'none', 'color': 'inherit'}}>
                        { job.company }
                    </a>
                </p>
                 :
                <p><strong>Company:</strong> { job.company }</p>
             }
             {job.company_industry !== null &&
            <p><strong>Industry:</strong> { job.company_industry }</p>
             }
            {job.company_employee_count_range && job.company_employee_count_range.length > 1 && (
                <p><strong>Company Size:</strong> {job.company_employee_count_range}</p>
            )}
            <p><strong>Location:</strong> {
              job.location === 'Remote' ? job.location :
              job.location && job.location.includes(',') ? job.location :
              `${job.location || 'Unknown'}, ${job.state_code || ''}`
            }</p>
            <p><strong>Date Posted:</strong> { job.date_posted }</p>
            {job.salary && job.salary.length > 1 &&
                <p><strong>Salary:</strong> {job.salary }</p>
            }
            {job.description ? (
                <>
                    <p><strong>Description:</strong></p>
                    <span
                        className="more-link"
                        id={`more-link-${job.id}`}
                        onClick={() => {
                            if (!showDesc.includes(job.id)) {
                                setShowDesc([...showDesc, job.id]);
                            } else {
                                setShowDesc(prev => prev.filter(val => val !== job.id));
                            }
                        }}
                    >
                        {showDesc.includes(job.id) ? "Show Less" : "Read full description"}
                    </span>
                    <div
                        className="full-description"
                        id={`full-description-${job.id}`}
                        style={{ display: showDesc.includes(job.id) ? 'block' : 'none' }}
                    >
                        <div dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(job.description) }} />
                    </div>
                </>
            ) :
                <>

                    <p><strong>Description:</strong></p>
                    <span tabindex="0" class="more-link" id="more-link-{{ job.id }}" onClick={() => {
                        if (!showDesc.includes(job.id)) {
                            setPreDesc(prev => [...prev, job.id])
                            if (!(job.id in fullDesc)) {
                            fetch(`/api/get_description/${job.id}`)
                                .then(response => response.json())
                                .then(data => {
                                    if (data.status === "success") {
                                        setFullDesc(prev => ({
                                            ...prev,
                                            [job.id]: DOMPurify.sanitize(data.html)
                                        }));
                                        setShowDesc(prev => [...prev, job.id])
                                    } else {
                                        setFullDesc(prev => ({
                                            ...prev,
                                            [job.id]: "<p>Could not load description.</p>"
                                        }));
                                        setShowDesc(prev => [...prev, job.id])
                                    }
                                })
                                .catch(err => {
                                    setFullDesc(prev => ({
                                        ...prev,
                                        [job.id]: "<p>Error loading description.</p>"
                                    }));
                                    setShowDesc(prev => [...prev, job.id])
                                });
                            } else {
                                setShowDesc(prev => [...prev, job.id]);
                            }
                        } else {
                            setShowDesc(prev => prev.filter(val => (val !== job.id)))
                            setPreDesc(prev => prev.filter(val => (val !== job.id)))
                        }
                    }}>{preDesc.includes(job.id) ? (showDesc.includes(job.id) ? "Show Less" : <div className='spinner'/>) : "Read full description"}</span>
                    <div class="full-description" id="full-description-{{ job.id }}" style={{'display': showDesc.includes(job.id) ? 'block' : 'none'}}>
                        {<div dangerouslySetInnerHTML={{ __html: fullDesc[job.id] }} />}
                    </div>
                </>
            }
            {/*=== Job link and popup functionality ===*/}
            <p>
              <strong>
                <a
                  href={job.final_url}
                  target="_blank"
                  onClick={() => {
                    setTimeout(() => {
                      setPendingApplyPopupJob(job);
                      setShowApplyPopup(true);
                    }, 3000); // 3-second delay
                  }}
                >
                  {user.filters?.selected_filter === "Applied_to"
                    ? "Application Link"
                    : "Apply Here"}
                </a>
              </strong>
              {recentlyAdded && (
                <em style={{ fontSize: '90%', color: 'var(--color-accent-primary)' }}> ← Be first to apply!</em>
              )}
            </p>
            {job.recruiter_emails &&
                <p><strong>Recruiter Emails:</strong> {job.recruiter_emails.join(', ') }</p>
            }


            {/* Outreach Co-Pilot Section */}
            <div
              className={
                "outreach-section" +
                (user.filters?.selected_filter === "Applied_to" ? " no-border" : "")
              }
            >
              <div className="outreach-buttons">
                <button
                  type="button"
                  className="outreach-btn navigator-btn"
                  onClick={() => {
                    setSelectedJob(job);
                    setShowNavigator(true);
                  }}
                >
                  <HiOutlineUserGroup size={16} />
                  Find Alumni on LinkedIn
                </button>

                {user.plan === "premium" ? (
                    <>

                    <div className="copilot-btn-container" style={{ position: "relative", display: "inline-block" }}>
                      <button
                        type="button"
                        disabled={msgClicksCount[jobIdStr] >= 3 || !user.resume_json}
                        title={
                          !user.resume_json
                            ? "Resume Data Not Gathered. Please re-enter a resume by going to your profile."
                            : msgClicksCount[jobIdStr] >= 3
                            ? "Limit Reached For This Job. Try again later"
                            : messageDisabled[jobIdStr] || msgAlreadyGenerated
                            ? "View the generated message again"
                            : "Draft Message with Rezify"
                        }
                        className={`outreach-btn copilot-btn ${
                          !user.resume_json || msgClicksCount[jobIdStr] >= 3 ? "is-disabled" : ""
                        }`}
                        onClick={() => {
                          if (!user.resume_json || msgClicksCount[jobIdStr] >= 3) return;

                          if (!messageDisabled[jobIdStr] && !msgAlreadyGenerated) {
                            setMsgClicksCount(prev => ({
                              ...prev,
                              [jobIdStr]: (prev[jobIdStr] || 0) + 1
                            }));
                          }

                          // open modal
                          setSelectedJob(job);
                          setShowCoPilot(true);
                        }}
                        style={{
                          opacity: !user.resume_json || msgClicksCount[jobIdStr] >= 3 ? 0.5 : 1,
                          cursor: !user.resume_json || msgClicksCount[jobIdStr] >= 3 ? "not-allowed" : "pointer",
                          filter: !user.resume_json || msgClicksCount[jobIdStr] >= 3 ? "grayscale(100%)" : "none",
                        }}
                      >
                        <HiSparkles size={16} />
                        {!user.resume_json
                          ? "Draft Message with Rezify"
                          : messageDisabled[jobIdStr] || msgAlreadyGenerated
                          ? "View Generated Message"
                          : "Draft Message with Rezify"}
                      </button>

                      {/* Tooltip */}
                      {(!user.resume_json || msgClicksCount[jobIdStr] >= 3) && (
                        <div className="tooltip">
                          {!user.resume_json
                            ? "Resume Data Not Gathered. Please re-enter a resume by going to your profile."
                            : "Limit Reached For This Job. Try again later"}
                        </div>
                      )}
                    </div>


                    </>
                ) : (
                  <button
                    type="button"
                    className="outreach-btn premium-btn"
                    onClick={advertisePremium}
                  >
                    <HiSparkles size={16} />
                    Draft Message with Rezify
                  </button>
                )}
              </div>
            </div>

            {/* Notes - only show on "Applied_to" tab */}
            {user.filters?.selected_filter === 'Applied_to' && (
              <div className="job-notes-container">
                <label className="job-notes-label">
                  Notes
                </label>
                <textarea
                  className="job-notes-textarea"
                  maxLength={300}
                  value={currentNotes}
                  onChange={(e) => {
                    const next = e.target.value.slice(0, 300); // hard enforce
                    setNotesDrafts(prev => ({
                      ...prev,
                      [jobIdStr]: next,
                    }));

                    setNotesSaveState(prev => ({
                        ...prev,
                        [jobIdStr]: 'unsaved'
                      }));
                  }}
                  placeholder="Add notes about your application, interviews, timeline, etc."
                />
                <div className="job-notes-footer">
                    <div className="notes-left">
                      <span className="job-notes-counter">
                        {currentNotes.length}/300
                      </span>

                      {/* Saved status indicator */}
                      <span className={isUnsaved ? "notes-status unsaved" : "notes-status saved"}>
                          {isUnsaved ? (
                            "(unsaved)"
                          ) : notesSaveState[jobIdStr] === "saving" ? (
                            "(Saved • Just Now)"
                          ) : savedTimeText ? (
                            `(Saved • ${savedTimeText})`
                          ) : (
                            "(Saved)"
                          )}
                        </span>
                   </div>
                  <button
                    type="button"
                    className="job-notes-save-button"
                    onClick={() => {
                      const original = persistedNotes;
                      if (currentNotes === original) return;

                      // Immediately show "Saved • Just Now"
                      setNotesSaveState(prev => ({
                        ...prev,
                        [jobIdStr]: 'saving',
                      }));

                      saveNotesToJob(job.id, currentNotes, jobIdStr);
                    }}
                  >
                    Save Notes
                  </button>
                </div>
              </div>
            )}

        </div>);
    })}

    {showApplyPopup && pendingApplyPopupJob && (
      <div className="modal-overlay">
        <div className="modal-content">
          <h2>Did you apply?</h2>
          <p>
            Did you submit an application to <strong>{pendingApplyPopupJob.title}</strong> at <strong>{pendingApplyPopupJob.company}</strong>?
          </p>
          <div className="modal-buttons">
            <button
              className="submit-btn"
              onClick={() => {
                addToAppliedPost(pendingApplyPopupJob.id);
                setShowApplyPopup(false);
                setPendingApplyPopupJob(null);
              }}
            >
              Yes
            </button>
            <button
              className="cancel-btn"
              onClick={() => {
                setShowApplyPopup(false);
                setPendingApplyPopupJob(null);
              }}
            >
              No
            </button>
          </div>
        </div>
      </div>
    )}


    {removePopupJob && (
  <div className="modal-overlay">
    <div className="modal-content">
      <h2>Why do you want to remove this job?</h2>
      <p><strong>{removePopupJob.title}</strong> at <strong>{removePopupJob.company}</strong></p>

      <select value={removeReason} onChange={(e) => setRemoveReason(e.target.value)}>
        <option value="">Select a reason</option>
        <option value="Expired">Job is not available/expired</option>
        <option value="Scam">Job is a scam</option>
        <option value="Duplicate">Job is a duplicate of another</option>
        <option value="Bad Match">Does not match my search</option>
        <option value="Not qualified">I am not qualified</option>
        <option value="Other">Other</option>
      </select>

      <div className="modal-buttons">
            <button
            className="submit-btn"
            onClick={async () => {
              if (!removeReason) {
                alert("Please select a reason.");
                return;
              }

              setFadingOutJobId(removePopupJob.id);

                setTimeout(() => {
                  setUser(prev => ({
                    ...prev,
                    removed_jobs: [...(prev.removed_jobs || []), removePopupJob],
                  }));
                  setRemovePopupJob(null);
                  setRemoveReason('');
                  setFadingOutJobId(null);
                }, 600);  // match the CSS animation timing

              // Send to backend
              try {
                await fetch('/api/remove_job', {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({
                    job_id: removePopupJob.id,
                    reason: removeReason,
                  }),
                });
                /*
                
                setUser(prev => ({
                  ...prev,
                  removed_jobs: [...prev.removed_jobs, removePopupJob],
                }));
                
                setRemovePopupJob(null); // close modal
                setRemoveReason('');
                */ 
              } catch (err) {
                alert("Failed to remove job.");
              }
            }}>Submit</button>

            <button
            className="cancel-btn"
            onClick={() => {
              setRemovePopupJob(null);
              setRemoveReason('');
            }}>Cancel</button>
          </div>
        </div>
      </div>
    )}


    {user.id ?
    (user.plan !== "premium" ?
    <>
    <p style={{textAlign: 'center'}}>You've reached your limit of <span style={{color:'var(--primary-aw)'}}>25 results</span></p>
    <p style={{textAlign: 'center'}}><a style={{color:'var(--primary-aw)'}} href="/plans?redirect=results"><b>Upgrade</b></a> to view more...</p>
    </>
    :
    <div class="pagination">
        {(total_jobs > limit) &&
        <button onClick={(event) => {
            if (!loadingMore) {
                if (finding) {
                    setLoadingMore(true);
                    //ask backend for more
                    fetch(`/api/load_more?segments=${segments + 1}`)
                    .then(response => response.json())
                    .then(data => {
                        setJobs(data.jobs);
                        setLimit(prev => prev + perSegment);
                        setLoadingMore(false);
                        setSegments(segments + 1);
                    })
                    .catch(error => {
                        alert("Error loading more")
                        setLoadingMore(false);
                    })
                } else {
                    //If not in discover, then we're really just upping the amount of jobs currently on display, no backend response needed
                    setLimit(prev => prev + perSegment)
                }
            }
        }}>{loadingMore ? <div className='spinner'/> : "Load More Results"}</button>
        }
        <p>
          {user.filters?.selected_filter === "Applied_to" ? (
            <>
              {Math.min(limit, filteredJobs.length)} of {filteredJobs.length} results
            </>
          ) : (
            <>
              {limit > total_jobs ? total_jobs : limit} of {total_jobs} results
            </>
          )}
        </p>
    </div>
    )
    :
    <>
    <br/>
    <p style={{textAlign: 'center'}}>Register to view more...</p>
    </>
                }

    {/* Outreach Co-Pilot Modals */}
    <OutreachNavigator
      isOpen={showNavigator}
      onClose={() => closeNavigator()}
      onOpenCoPilot={(jobFromNav) => {
        setSelectedJob(jobFromNav);
        closeNavigator({ preserveJob: true });
        setShowCoPilot(true);
      }}
      job={selectedJob}
      user={user}
      hasMessage={hasGeneratedMessage(selectedJob)}
    />
    
    <OutreachCoPilot 
      isOpen={showCoPilot}
      onClose={() => {
        setShowCoPilot(false);
        setSelectedJob(null);
      }}
      job={selectedJob}
      user={user}
      onDraftGenerated={handleDraftGenerated}
      hasMessage={hasGeneratedMessage(selectedJob)}
    />
    </>);
}

export {JobTitles}