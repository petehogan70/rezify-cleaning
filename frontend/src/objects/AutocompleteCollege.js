import { useEffect, useState } from "react";

function AutocompleteCollege({ claimedEmail, ref = null, setLocation = (newloc) => {}, detectedSubdomain = "", setAllValidColleges = () => {} }) {
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const [savedData, setSavedData] = useState([]);
    const [allSuggest, setAllSuggest] = useState([]);
    const [filteredSuggestions, setFilteredSuggestions] = useState([]);
    const [lockInput, setLockInput] = useState(false);
    const [showTooltip, setShowTooltip] = useState(false);

    useEffect(() => {
        console.log("Running subdomain detection useEffect");
        Promise.all([
            fetch('/static/wuad.json').then(res => res.ok ? res.json() : []),
            fetch('/static/school_themes.json').then(res => res.ok ? res.json() : {})
        ]).then(([wuadData, themesData]) => {
            setSavedData(wuadData);
            const collegeNames = wuadData.map(college => college["name"]);
            setAllSuggest([...collegeNames]);
            setAllValidColleges(collegeNames);

            console.log("Running subdomain detection useEffect part 2");

            if (detectedSubdomain) {
                console.log("Detected subdomain:", detectedSubdomain);
            }


            // Subdomain logic
            if (detectedSubdomain && themesData[detectedSubdomain]) {
                console.log("Detected a subdomain!");
                const matchingTheme = themesData[detectedSubdomain];

                if (matchingTheme.full_name) {
                    setInput(matchingTheme.full_name);
                    setLocation(matchingTheme.full_name);
                    setLockInput(true);
                    setFilteredSuggestions([]);  // Clear any dropdown
                } else {
                    setInput("None");
                    setLocation("None");
                }
                setLoading(false);
            }
        });
    }, [detectedSubdomain]);

    useEffect(() => {
        if (lockInput || savedData.length === 0) return;
        const splemail = claimedEmail.split("@");
        if (splemail.length >= 2) {
            const domain = splemail[1];
            setLoading(true);
            const filtresult = savedData.filter(item => item["domains"].includes(domain));
            if (filtresult.length >= 1) {
                const collegeName = filtresult[0]["name"];
                setInput(collegeName);
                setLocation(collegeName);
            } else {
                setInput("None");
                setLocation("None");
            }
            setLoading(false);
        } else {
            setInput("None");
            setLocation("None");
        }
    }, [savedData, claimedEmail]);

    useEffect(() => {
        const handleClick = (event) => {
            if (event.target.id !== "college") {
                setFilteredSuggestions([]);
            }
        };
        document.addEventListener("click", handleClick);
        return () => document.removeEventListener("click", handleClick);
    }, []);

    const getFilteredSuggestions = (value) => {
        const lowerVal = value.toLowerCase();
        const filtered = allSuggest.filter(val =>
            val.toLowerCase().includes(lowerVal)
        );

        return [...filtered.slice(0, 25), 'None', 'School not listed'];
    };

    return (
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', width: '100%', position: 'relative' }}
            onMouseEnter={() => lockInput && setShowTooltip(true)}
            onMouseLeave={() => setShowTooltip(false)}
        >
            <span style={{ margin: 3 }}>College:</span>
            <div style={{ flex: 1, position: 'relative' }}>
                <input
                    value={loading ? "..." : input}
                    required
                    type="text"
                    id="college"
                    name="college"
                    ref={ref}
                    readOnly={lockInput}
                    onChange={(event) => {
                        if (lockInput) return;  // Prevent dropdown opening if locked
                        setInput(event.target.value);
                        setFilteredSuggestions(getFilteredSuggestions(event.target.value));
                        setLocation(event.target.value);
                    }}
                    onFocus={() => {
                        if (lockInput) return;  // Prevent dropdown opening if locked
                        if (input.length > 0) {
                            setFilteredSuggestions(getFilteredSuggestions(input));
                        }
                    }}
                    onKeyDown={(event) => {
                        if (event.key === 'Enter') {
                            const first = filteredSuggestions[0] || input;
                            setInput(first);
                            setLocation(first);
                            setFilteredSuggestions([]);
                        }
                    }}
                    style={{ width: '90%' }}
                />

                {lockInput && showTooltip && (
                    <div
                        style={{
                            position: 'absolute',
                            top: '-25px',
                            left: 0,
                            backgroundColor: '#333',
                            color: '#fff',
                            padding: '5px 10px',
                            borderRadius: '4px',
                            fontSize: '12px',
                            whiteSpace: 'normal',
                            maxWidth: '200px',
                            zIndex: 200
                        }}
                    >
                        You cannot edit this field. Leave the school portal to change your college.
                        <br />
                        <a
                            href="https://rezify.ai/register"
                            target="_blank"
                            rel="noopener noreferrer"
                            style={{ color: '#aad7ff', textDecoration: 'underline' }}
                        >
                            Rezify
                        </a>
                    </div>
                )}

                {!lockInput && filteredSuggestions.length > 0 && (
                    <ul style={{
                        listStyle: 'none',
                        padding: 0,
                        margin: 0,
                        backgroundColor: 'white',
                        border: '1px solid var(--primary-color)',
                        maxHeight: '200px',
                        overflowY: 'auto',
                        position: 'absolute',
                        width: '100%',
                        zIndex: 100
                    }}>
                        {filteredSuggestions.map((item, i) => (
                            <li
                                key={i}
                                onClick={() => {
                                    setInput(item);
                                    setLocation(item);
                                    setFilteredSuggestions([]);
                                }}
                                style={{
                                    cursor: 'pointer',
                                    padding: '10px',
                                    borderBottom: '1px solid #eee',
                                    backgroundColor: 'white',
                                    color: 'var(--primary-aw)'
                                }}
                            >
                                {item.split(new RegExp(`(${input})`, 'gi')).map((part, index) =>
                                    part.toLowerCase() === input.toLowerCase() ? (
                                        <span key={index} style={{ backgroundColor: 'var(--primary-color)', color: 'white' }}>{part}</span>
                                    ) : (
                                        <span key={index}>{part}</span>
                                    )
                                )}
                            </li>
                        ))}
                    </ul>
                )}
            </div>
        </div>
    );
}

export { AutocompleteCollege };
