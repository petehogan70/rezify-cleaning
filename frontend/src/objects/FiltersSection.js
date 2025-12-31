import { useEffect, useState, useRef } from "react";
import { Autocomplete } from "./Autocomplete";
import '../styles/FiltersSection.css';

function FiltersSection({user = {}, //User object
                        distinct_industries = [],
                        distinct_titles = [], 
                        setUser = (()=>{}), //Function to update User object, usually for short frontend updates (i.e. changing selected filter)
                        refreshJobs=((newJobs, newUser, newTotJobs)=>{}), //Function to refresh jobs listings and user after update filter call, prevents whole page refresh
                        setFirstWait=()=>{}, //Set loading status
                        firstWait=false,
                        setPremiumPopup=()=>{}, //Show premium popup
                        setErrorMessage=()=>{}, //Set error message
                        setShowErrorPopup=()=>{}, //Show the error popup
                        selectedJobType = '',
                        filtersDisabled = false,
                        setFiltersDisabled = () => {}
                    }) {
    const [addRec, setAddRec] = useState(false); //add title input
    const [filtersBox, setFiltersBox] = useState(false); //filter section open
    const [locationBox, setLocationBox] = useState(false); //location box open
    const [industryBox, setIndustryBox] = useState(user.filter && user.filters['selected_industries'] && user.filters['selected_industries'].length > 0); //industry box open
    const [deletedTitles, setDeletedTitles] = useState([]); //deleted titles, for some reason react doesn't update mappings
    const [currentLocation, setCurrentLocation] = useState(user.filters?.location || "");
    const [selectedIndustries, setSelectedIndustries] = useState(user.filters?.selected_industries || []);
    const [serverDistinctTitles, setServerDistinctTitles] = useState(distinct_titles || []);


    useEffect(() => {
      setServerDistinctTitles(distinct_titles || []);
    }, [distinct_titles]);


    useEffect(() => {
        //on loading of user
        setLocationBox(user.filters && user.filters['location'] !== null);
        setIndustryBox(user.filters&& user.filters['selected_industries'] && user.filters['selected_industries'].length > 0);
        setCurrentLocation(user.filters?.location || "");
        if (user.filters?.selected_industries) {
            setSelectedIndustries(user.filters.selected_industries);
        }
    }, [user]);

    const [addedTitles, setAddedTitles] = useState([]);

    const addRecRef = useRef(null);

    const advertisePremium = () => {
        setPremiumPopup(true);
    }

    const normalize = s => s.trim().replace(/\s+/g, " ").toLowerCase();

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
                            if (jsondata.user) {
                                syncFromServerPayload(jsondata);
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


    const submitFilters = (event) => {
        event.preventDefault();  // Prevent form submission

        let filters = {};

        // Get Job Type
        //let jobType = jobTypeRef.current.value;
        let jobType = document.querySelector('input[name="type"]:checked').value;
        filters['type'] = jobType;

        // Get Availability
        let availability = document.querySelector('input[name="international_only"]:checked').value;
        filters['international_only'] = availability === 'true';

        // Get Location
        let locationType = document.querySelector('input[name="location_type"]:checked').value;
        if (locationType === 'Specified') {
            let location = document.getElementById('location').value.trim();
            let radius = document.querySelector('input[name="radius"]').value.trim();

            filters['location'] = location || null;
            filters['radius'] = radius || 50;
        } else {
            filters['location'] = null;
            filters['radius'] = 50;
        }

        // Get Industry
        let industryType = document.querySelector('input[name="industry"]:checked').value;
        if (industryType === 'Selected') {
            filters['selected_industries'] = selectedIndustries;
        } else {
            filters['selected_industries'] = [];
        }

        // Optimistically update the UI to show the new filter buttons immediately
        setUser(prev => ({
            ...prev,
            filters: {
                ...prev.filters,
                ...filters
            }
        }));

        // Call searchChange with 'filter_box' parameter and the filters object as value
        setFiltersBox(false);
        updateFilters('filter_box', JSON.stringify(filters));
    }

    const syncFromServerPayload = (payload) => {
      const srvUser = payload?.user;
      const srvDistinct = payload?.distinct_titles || [];

      // 1) Update our local copy of distinct titles from server
      setServerDistinctTitles(srvDistinct);

      // 2) Replace user with server user, but keep the currently selected tab/filter
      setUser(prev => {
        const keepSelectedFilter = prev?.filters?.selected_filter ?? 'All';
        return {
          ...(srvUser || {}),
          filters: {
            ...(srvUser?.filters || {}),
            selected_filter: keepSelectedFilter,
          },
        };
      });

      // 3) Make the chips show *exactly* what the server says:
      //    - addedTitles are any selected titles that aren't in distinct_titles (custom ones)
      //    - clear deletedTitles because server is truth
      const selected = srvUser?.filters?.selected_titles || [];
      const extras = selected.filter(t => !srvDistinct.includes(t));
      setAddedTitles(extras);
      setDeletedTitles([]);
    };



    return (<>
        {(user.filters && user.filters['selected_filter'] === 'All') &&
                (<>
                    {selectedJobType === 'internships' && <h2>Internships Search Titles: (Click to filter)</h2>}
                    {selectedJobType === 'new_grad' && <h2>Job Search Titles: (Click to filter)</h2>}
                    <form id="filterForm" onSubmit={() => {
                        refreshJobs();
                    }}>
                        <input type="hidden" name="parameter" value="title_filters" />
                    </form>

                    <div class="filter-buttons" id="filter-buttons">
                            {[...new Set([...serverDistinctTitles, ...addedTitles])]
                               .sort((a,b)=>a.localeCompare(b))                       // stable order
                               .map(rec => { return (
                                deletedTitles.includes(rec) ? <></> :
                                <button key={rec} disabled={filtersDisabled} style={{ cursor: filtersDisabled ? 'not-allowed' : 'pointer' }} onClick={() => {
                                    if (deletedTitles.includes(rec)) return;
                                    //Frontend toggle
                                    setUser(prev => ({
                                        ...prev,
                                        'filters': {
                                            ...prev.filters,
                                            'selected_titles': (user.filters['selected_titles'].includes(rec) ? prev.filters['selected_titles'].filter(val => val !== rec) : [...prev.filters['selected_titles'], rec])
                                        }
                                    }));
                                    //Backend toggle
                                    updateFilters('title_filters', rec);
                                }} data-rec={ rec } className={(user.filters && user.filters['selected_titles'].includes(rec)) ? "selected" : ""}>
                                { rec }
                                {user.plan === "premium" && <span class="close" style={{ zIndex: 9999, pointerEvents: 'auto'}} onClick={() => {
                                    //Frontend delete
                                    setDeletedTitles(prev => [...prev, rec])
                                    setTimeout(() => {
                                        setUser(prev => ({
                                            ...prev,
                                            'filters': {
                                                ...prev.filters,
                                                'selected_titles': prev.filters['selected_titles'].filter(val => val !== rec)
                                            }
                                        }));
                                    }, 10);
                                    //Backend delete
                                    updateFilters('remove_title', rec);
                                }}>&times;</span>}
                                </button>);
                            })}
                        <div className="add-rec-container">
                            <label style={{ cursor: user.plan === "premium" ? "pointer" : "default", position: "relative" }}>
                                <button
                                    className="add-rec-button"
                                    disabled={user.plan !== "premium" || filtersDisabled}
                                    style={{
                                        cursor: (user.plan !== "premium" || filtersDisabled) ? "not-allowed" : "pointer",
                                        color: user.plan !== "premium" ? 1 : 0.5
                                    }}
                                    onClick={() => {
                                        if (user.plan === "premium" && !filtersDisabled) {
                                            setAddRec(prev => !prev);
                                        } else if (!filtersDisabled) {
                                            advertisePremium(); // Trigger upgrade modal or similar
                                        }
                                    }}
                                >
                                    +
                                </button>
                                <div className="tooltip">
                                    {user.plan === "premium"
                                        ? "Add a search title"
                                        : "Upgrade to premium to fully customize your search titles"}
                                </div>
                            </label>

                            <div style={{ display: addRec ? 'flex' : 'none', flexDirection: 'row' }}>
                                <div className="add-rec-input-container" style={{ display: 'flex' }}>
                                    <input
                                        type="text"
                                        id="addRecInput"
                                        className="add-rec-input"
                                        placeholder="Search for"
                                        ref={addRecRef}
                                        minLength="3"
                                        required
                                    />
                                    <span className="intern-label" id="internLabel"> Intern</span>
                                </div>
                                <button
                                  type="button"
                                  disabled={filtersDisabled}
                                  style={{ cursor: filtersDisabled ? 'not-allowed' : 'pointer' }}
                                  onClick={() => {
                                    const raw = addRecRef.current?.value ?? "";
                                    const base = raw.trim();
                                    if (!base) return;

                                    const newTitle = `${base} Intern`;
                                    const exists =
                                      (serverDistinctTitles || []).some(t => normalize(t) === normalize(newTitle))

                                    if (!exists) {
                                      setAddedTitles(prev => [...prev, newTitle]);
                                      setDeletedTitles(prev => prev.filter(t => normalize(t) !== normalize(newTitle)));
                                      updateFilters('add_title', newTitle);
                                    }

                                    addRecRef.current.value = '';
                                    setAddRec(false);
                                  }}
                                >
                                  Add
                                </button>
                            </div>
                        </div>

                    </div>

                    <hr class="divider" />
                </>)}


            {(user.filters && user.filters['selected_filter'] === 'All') &&
            <>
                {<><div class="filter-button-container">
                    <button class="filter-button" id="filter-button" disabled={filtersDisabled} style={{ cursor: filtersDisabled ? 'not-allowed' : 'pointer' }} onClick={() => {
                        setFiltersBox(prev => !prev);
                    }}>Filters</button>
                    <div className="filter-buttons" style={{ display: 'inline-flex', alignItems: 'center', flexWrap: 'wrap', gap: '8px', marginLeft: '4px' }}>
                        <span>:</span>
                        {user.filters['type'] === 'All' && user.filters['international_only'] === false && user.filters['location'] === null && user.filters['selected_industries'].length === 0 ?
                            <button disabled style={{cursor: 'default', fontSize: '12px', padding: '3px 8px'}}>No filters selected</button>
                            :
                            <>
                                {user.filters['type'] !== 'All' &&
                                    <button className="selected" disabled style={{cursor: 'default', fontSize: '12px', padding: '3px 8px'}}>Job Type: {user.filters['type']}</button>
                                }
                                {user.filters['international_only'] === true &&
                                    <button className="selected" disabled style={{cursor: 'default', fontSize: '12px', padding: '3px 8px'}}>Availability: H1 Sponsorship Likely</button>
                                }
                                {user.filters['location'] !== null &&
                                    <button className="selected" disabled style={{cursor: 'default', fontSize: '12px', padding: '3px 8px'}}>Location: {user.filters['location']}, within {user.filters['radius']} miles</button>
                                }
                                {user.filters['selected_industries'] !== null && user.filters['selected_industries'].length > 0 &&
                                    <div className="dropdown">
                                        <button className="dropdown-button">
                                            {`Industries: ${user.filters['selected_industries'].length} selected...`}
                                        </button>
                                        <div className="dropdown-aligner" style={{position: 'relative'}}>
                                            <div className="dropdown-content" style={{top: '-5px', left: '5px', cursor: 'default', fontSize: '12px', fontFamily: 'Roboto, sans-serif'}}>
                                                {user.filters['selected_industries'].map((industry) => (
                                                    <button className="selected-industry-button" onClick={() => {
                                                    }}>{industry}</button>
                                                ))}
                                            </div>
                                        </div>
                                    </div>
                                }
                            </>
                        }
                    </div>
                </div>

                <div id="filterBox" class="filter-box" style={{'display': (filtersBox ? 'block' : 'none')}}>
                    <form id="filtersForm" onSubmit={(event)=>{
                        submitFilters(event)
                    }}>
                        <input type="hidden" name="parameter" value="filter_box" />
                        
                        <div class="filter-fields-container">
                            <div class="filter-field filter-field-job-type">
                            <h3>Filter by Job Type:</h3>
                            <label>
                                <input type="radio" name="type" value="All" defaultChecked={user.filters['type'] === 'All'} /> All Jobs
                            </label>
                            <label>
                                <input type="radio" name="type" value="Remote" defaultChecked={user.filters['type'] === 'Remote'} /> Remote Jobs
                            </label>
                            <label>
                                <input type="radio" name="type" value="In-person" defaultChecked={user.filters['type'] === 'In-person'} /> In-Person Jobs
                            </label>
                        </div>

                        <div class="filter-field filter-field-availability">
                            <h3>Filter by Availability:</h3>
                            <label>
                                <input type="radio" name="international_only" value={false} defaultChecked={!user.filters['international_only']}/> All Jobs
                            </label>
                            <label>
                                <input type="radio" name="international_only" value={true} defaultChecked={user.filters['international_only']}/> H1 Sponsorship Likely
                                <span className="tooltip-container" style={{ position: 'relative', display: 'inline-block' }}>
                                            <span
                                                style={{
                                                    display: 'inline-block',
                                                    width: '12px',
                                                    height: '12px',
                                                    borderRadius: '50%',
                                                    background: '#3b3b3b',
                                                    color: 'white',
                                                    fontSize: '9px',
                                                    lineHeight: '12px',
                                                    textAlign: 'center',
                                                    cursor: 'pointer',
                                                    marginLeft: '3px'
                                                }}
                                            >
                                                ?
                                            </span>
                                            <span
                                                className="tooltip-text"
                                                style={{
                                                    width: '200px',
                                                    backgroundColor: '#333',
                                                    color: '#fff',
                                                    textAlign: 'left',
                                                    borderRadius: '6px',
                                                    padding: '6px',
                                                    position: 'absolute',
                                                    zIndex: 1,
                                                    bottom: '125%',
                                                    left: '50%',
                                                    transform: 'translateX(-50%)',
                                                    fontSize: '11px'
                                                }}
                                            >
                                                This filter uses up to date LCA Disclosure data from the U.S. Department of Labor to determine which companies sponsor H1 Visas.
                                            </span>
                                        </span>
                            </label>
                        </div>

                        <div class="filter-field filter-field-location">
                            <h3>Filter by Location:</h3>
                            <label>
                                <input type="radio" name="location_type" value="None" defaultChecked={!(user.filters['location'])} onClick={() => {
                                    setLocationBox(false);
                                }} /> No Location
                            </label>
                            <label>
                                <input type="radio" name="location_type" value="Specified" defaultChecked={(user.filters['location']) !== null} onClick={() => {
                                    setLocationBox(true);
                                }} /> Specify Location
                            </label>

                            <div id="locationFields" style={{'display': (locationBox ? 'block' : 'none')}}>
                                <div class="location-input-group">
                                    <span>Location:</span>
                                    <Autocomplete setLocation={setCurrentLocation} overrideValue={(user.filters && user.filters['location'] !== '') ? user.filters['location'] : ""}/>
                                </div>
                                <div class="location-input-group">
                                    <span>Within:</span>
                                    <input type="number" name="radius" class="miles-input" defaultValue={  (user.filters && user.filters['radius'] !== '') ? user.filters['radius'] : 50 } min="0" step="1" />
                                    <span>miles</span>
                                </div>
                            </div>
                        </div>

                        <div class="filter-field filter-field-industry">
                            <h3>Filter by Industry:</h3>
                            <label>
                                <input type="radio" name="industry" value="All" defaultChecked={user.filters['selected_industries'].length === 0} onChange={(event) => {
                                    setIndustryBox(!event.target.value);
                                }} /> All Industries
                            </label>
                            <label>
                                <input type="radio" name="industry" value="Selected" defaultChecked={user.filters['selected_industries'].length > 0} onChange={(event) => {
                                    setIndustryBox(event.target.value);
                                }} /> Select Industries
                            </label>
                            <div class="industry-checkboxes" id="industryCheckboxes" style={{'display': (industryBox ? 'block' : 'none')}}>
                                {distinct_industries.map(industry => {
                                    return (<div class="industry-label">
                                        <input type="checkbox" name="selected_industries" value={ industry } onChange={(event) => {
                                            setSelectedIndustries(prev => (event.target.checked ? [...prev, event.target.value] : prev.filter(val => val !== event.target.value)))
                                        }} defaultChecked={user.filters['selected_industries'].includes(industry)} />
                                        {industry}
                                    </div>);
                                })}
                            </div>
                        </div>
                        </div>

                        <button type="submit" class="filter-apply-button" disabled={filtersDisabled} style={{ cursor: filtersDisabled ? 'not-allowed' : 'pointer' }}>Apply Filters</button>
                    </form>
                </div></>}

                <hr class="divider"/>

                {selectedJobType === 'internships' && <h2>Internship Recommendations:</h2>}
                {selectedJobType === 'new_grad' && <h2>Job Recommendations:</h2>}
                </>
            }
                {user.filters && user.filters['selected_filter'] === 'Favorites' &&
                    <h1>Favorites:</h1>
                }
                {user.filters && user.filters['selected_filter'] === 'Applied_to' &&
                    <h1>Positions Applied To:</h1>
                }
    </>)
}

export {FiltersSection}