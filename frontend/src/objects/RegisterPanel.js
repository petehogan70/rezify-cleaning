import { useEffect, useState } from "react"
import { AutocompleteCollege } from "./AutocompleteCollege";
import { useTheme } from "../hooks/ThemeContext";

function RegisterPanel() {
    const [firstWait, setFirstWait] = useState(false); //false = waiting on repsonse from /register on page load, true = /register responded
    const [waiting, setWaiting] = useState(false); //false = waiting on repsonse from /register on submit, true = /register responded
    const [error_message, setErrorMessage] = useState("");
    const [hasResume, setHasResume] = useState(false); //resume is available to autofill
    // const [showCollege, setShowCollege] = useState(true); //whether or not user should specify college on form

    const [firstName, setFirstName] = useState(""); //reference to first name field
    const [lastName, setLastName] = useState(""); //reference to last name field
    const [email, setEmail] = useState(""); //reference to email field
    const [reportedCollege, setReportedCollege] = useState(""); //reference to email field
    const subdomain = window.location.hostname.split(".")[0];
    const [validColleges, setValidColleges] = useState([]); //list of all valid colleges, used for autocomplete
    const {theme} = useTheme(); //get logo from theme
    const [adminReg, setAdminReg] = useState(null);

    useEffect(() => {
        const params = new URLSearchParams(window.location.search);
        setAdminReg(params.get("type") === "admin");
    }, []);



    const validateRegisterForm = (event) => {
        const inputs = document.querySelectorAll('input[type="text"], input[type="email"]');
        const forbiddenKeywords = ['DROP', 'DELETE', 'INSERT', 'UPDATE', 'SELECT', '--', ';'];

        for (let input of inputs) {
            const value = input.value.trim();
            const upperValue = value.toUpperCase();

            // Length check
            if (value.length < 1 || value.length > 80) {
                alert(`"${input.placeholder}" must be between 1 and 80 characters.`);
                input.focus();
                event.preventDefault();
                return false;
            }

            // SQL injection keyword check
            for (let keyword of forbiddenKeywords) {
                if (upperValue.includes(keyword)) {
                    alert(`Input rejected in "${input.placeholder}". Please try again.`);
                    input.focus();
                    event.preventDefault();
                    return false;
                }
            }
        }

        // Check that reportedCollege is one of the valid suggestions
        if (!validColleges.includes(reportedCollege) && reportedCollege !== "None" && reportedCollege !== "School not listed") {
            alert("Please select a valid college from the suggestions.");
            event.preventDefault();
            return false;
        }

        return true;
    }

    const HandleRegister = async (event) => {
        event.preventDefault();
        setWaiting(true);
        const result = await fetch('/api/register', {
            method: 'POST',
            body: new FormData(event.target),
        }) //send form data post request
        if (result.ok) {
            result.json().then(data => {
                if (data.redirect) {
                    setWaiting(false);
                    window.location.href = data.redirect;
                } else {
                    //do an error message, login prob unsuccessful
                    if (data.error_message) {
                        setErrorMessage(data.error_message)
                        setWaiting(false);
                    }
                }
            });
        } else {
            //do an error message
            setErrorMessage("Error: " + result.statusText)
            setWaiting(false);
        }
    }

     const HandleAdminRegister = async (event) => {
        event.preventDefault();
        setWaiting(true);
        const result = await fetch('/api/admin_register', {
            method: 'POST',
            body: new FormData(event.target),
        }) //send form data post request
        if (result.ok) {
            result.json().then(data => {
                if (data.redirect) {
                    setWaiting(false);
                    window.location.href = data.redirect;
                } else {
                    //do an error message, login prob unsuccessful
                    if (data.error_message) {
                        setErrorMessage(data.error_message)
                        setWaiting(false);
                    }
                }
            });
        } else {
            //do an error message
            setErrorMessage("Error: " + result.statusText)
            setWaiting(false);
        }
    }


    useEffect(() => {
        if (adminReg !== null) {
          const endpoint = adminReg ? "/api/admin_register" : "/api/register";

          fetch(endpoint).then(async (response) => {
            if (response.ok) {
              const data = await response.json();

              // auto fill resume if elements exist
              if (data.resume_info) {
                if (data.has_resume_entered) {
                    setHasResume(true);
                }
                if (data.resume_info.first_name) {
                  setFirstName(data.resume_info.first_name);
                }
                if (data.resume_info.last_name) {
                  setLastName(data.resume_info.last_name);
                }
                if (data.resume_info.email) {
                  setEmail(data.resume_info.email);
                }
                if (data.resume_info.reported_college) {
                  setReportedCollege(data.resume_info.reported_college);
                }
              }

              if (data.error_message) {
                setErrorMessage(data.error_message);
              }
            } else {
              setErrorMessage("Error: " + response.statusText);
            }
            setFirstWait(true);
          });
        }
    }, [adminReg]);



    return (<>
        <form method="post" style={{justifyContent: 'center', alignItems: 'center', display: 'flex', flexDirection: 'column'}}  onSubmit={(event) => {
            if (validateRegisterForm(event)) {
                adminReg ? HandleAdminRegister(event) : HandleRegister(event)
            }
        }}>
            {firstWait ?
            <>
                <div style={{display: 'flex', flexDirection: 'row'}}>
                    <input type="text" name="first_name" defaultValue={firstName} placeholder="First Name" required/>
                    <input type="text" name="last_name" defaultValue={lastName} placeholder="Last Name" required/>
                </div>
                <input type="email" id="email" name="email" onChange={(event) => {
                    setEmail(event.target.value);
                }} defaultValue={email} placeholder="Email" required/>
                <>
                    <AutocompleteCollege
                        claimedEmail={email}
                        setLocation={(newloc) => setReportedCollege(newloc)}
                        detectedSubdomain={subdomain}
                        setAllValidColleges={setValidColleges}
                    />
                    <input type="hidden" name="college" value={reportedCollege} />
                </>
                {hasResume &&
                    <p class="parsed-resume-note">* Parsed from resume</p>
                }
                <input type="password" name="password" placeholder="Password" required minlength="8" maxlength="40" />
                <input type="password" name="confirm_password" placeholder="Confirm Password" required minlength="8" maxlength="40" />
                <button className="register-button" type="submit" style={{justifyContent: 'center', alignItems: 'center', display: 'flex', position: 'relative', width: '100px'}}>{!waiting && "Register"}{waiting && <div className="spinner"/>}</button>
                { error_message.length >= 1 &&
                    <p class="error-message">{ error_message }</p>
                }
            </>
            :
            <div className="spinner-black"></div>
            }
        </form>
        <div className="register-options">
            {adminReg && (<a className="register-link" href="/login?type=admin">Back to Login</a>)}
            {!adminReg && (<a className="register-link" href="/login">Back to Login</a>)}
            {adminReg && (
                <a href="https://docs.google.com/forms/d/e/1FAIpQLScO906_cFeHxCN_3UdPhA8FckpcUWxMFfcNn5wCstICRnv52Q/viewform?usp=header"
                  target="_blank"
                  rel="noreferrer"
                  className="register-link"
                >
                  Request New Admin
                </a>
            )}
            {theme.logo && !theme.logo.includes("rezify") && !adminReg && (
                <a href="https://rezify.ai/register"
                    className="register-link">
                      Leave School Portal
                  </a>
            )}
            </div>
        </>);
}

export {RegisterPanel};