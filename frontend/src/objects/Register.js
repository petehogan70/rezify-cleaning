import { useEffect, useState } from "react"
import "../styles/RegisterPage.css"
import { RegisterPanel } from "./RegisterPanel";
import { useNavigate } from "react-router-dom";
import { useTheme } from "../hooks/ThemeContext";



function Register({
                    verify = false //on verifying stage or register stage
                }) {
    const [error_message, setErrorMessage] = useState("");
    const [user_email, setUserEmail] = useState("");
    const [waiting, setWaiting] = useState(false); //false = waiting on POST repsonse from /verify on button click, true = /verify responded
    const [firstWait, setFirstWait] = useState(false); //false = waiting on repsonse from /verify, true = /verify responded
    const [adminReg, setAdminReg] = useState(null);
    const {theme} = useTheme(); //get logo from theme
    const [notifyWaiting, setNotifyWaiting] = useState(false);
    const [notifySuccess, setNotifySuccess] = useState('none');


    useEffect(() => {
        const params = new URLSearchParams(window.location.search);
        setAdminReg(params.get("type") === "admin");
    }, []);


    const HandleVerify = async (event) => {
        event.preventDefault();
        setWaiting(true);
        const result = await fetch('/api/verify_email', {
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

    const HandleAdminVerify = async (event) => {
        event.preventDefault();
        setWaiting(true);
        const result = await fetch('/api/admin_verify_email', {
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

    async function notifyVerificationError(email) {
        try {
            const response = await fetch('/api/notify_verification_not_received', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                email: email
              }),
            });

            const result = await response.json();

            if (result.status === 'success') {
              // Everything went well
              setNotifySuccess('success');
              setNotifyWaiting(false);
            }
        } catch (error) {
            setNotifySuccess('error');
            setNotifyWaiting(false);
        }
    }


    useEffect(() => {
            if (verify && adminReg !== null) {

                const endpoint = adminReg ? "/api/admin_verify_email" : "/api/verify_email";

                fetch(endpoint).then(async response => {
                    //we should get colors, resume_info, error_message
                    //get flask backend response
                    if (response.ok) {
                        const data = await response.json();
                        //get user if exists
                        if (data.user_email) {
                            setUserEmail(data.user_email)
                            
                        }
            
                        if (data.error_message) {
                            setErrorMessage(data.error_message)
                        }
                    } else {
                        setErrorMessage("Error: " + response.statusText)
                        //error, prob shouldnt log in
                    }
                    setFirstWait(true);
                });
            }
          }, [verify, adminReg]); // <== empty dependency array = run once on load

    const navigate = useNavigate();

    return (
        <>
        <div className="container">
        <button style={{position: 'absolute', left: 10, top: 10, padding: 5}} onClick={() => {
            navigate("/");
        }}>←</button>
        {verify &&
            <>
                {adminReg &&
                    <>
                        <h1>Admin Verify Email</h1>
                        <img src={theme.logo} alt="Rezify Logo" className="admin-logo"/>
                    </>
                }
                {!adminReg && <h1>Verify Email</h1>}
            </>
        }
        {!verify &&
            <>
                {adminReg &&
                    <>
                        <h1>Admin Register</h1>
                        <img src={theme.logo} alt="Rezify Logo" className="admin-logo"/>
                    </>
                }
                {!adminReg && <h1>Register</h1>}
            </>
        }
        {verify &&
            <>
                <form method="post" onSubmit={(event) => {
                    adminReg ? HandleAdminVerify(event) : HandleVerify(event)
                }}>
                    {!firstWait && <div style={{width: '100%', display: 'flex', justifyContent: 'center', alignItems: 'center'}}><div className="spinner-black"></div></div>}
                    {firstWait && <p>Enter verification code sent to: { user_email }</p>}
                    <p>It may take up to a minute or 2 to receive the email.</p>
                    
                    <input type="text" name="code" placeholder="Code" required minlength="6" maxlength="6"/>
                    <button type="submit">{!waiting && "Verify"}{waiting && <div className="spinner"></div>}</button>
                    {error_message.length >= 1 &&
                        <p className="error-message">{ error_message }</p>
                    }
                </form>
                <p>Didn't get email? Make sure to check spam</p>
                <button class="toggle-form" style={{marginTop: '0px'}} onClick={() => {window.location.href="/verify_email"}}>Send Code Again</button>
                <div className="register-divider"></div>

                <div className="support-row">
                    {notifySuccess !== 'error' && notifySuccess !== 'success' && (
                        <>
                            <span className="support-text">
                                Not receiving email?:
                            </span>

                            {!notifyWaiting && (
                                <>
                                    <button
                                        type="button"
                                        className="support-button"
                                        disabled={notifyWaiting}
                                        onClick={() => {
                                            setNotifyWaiting(true);
                                            notifyVerificationError(user_email);
                                        }}
                                    >
                                        Notify Support
                                    </button>
                                </>
                            )}
                            {notifyWaiting && <span className="support-spinner"></span>}


                            <span className="tooltip-container">
                                <span className="tooltip-icon">?</span>
                                <span className="tooltip-text">
                                    Sends a support notification to the Rezify team to help resolve email verification issues.
                                    Your email address ({user_email}) will be included in the support request, so we can assist you directly.
                                </span>
                            </span>
                        </>
                    )}
                    {notifySuccess === 'error' && (
                        <>
                            <span className="support-text">
                                Error sending notification. Please try again later, or email us directly at support@rezify.ai
                            </span>
                        </>
                    )}
                    {notifySuccess === 'success' && (
                        <>
                            <span className="support-text">
                                Support has been notified! We will be at your assistance shortly.
                            </span>
                        </>
                    )}
                </div>
            </>
        }
        {!verify &&
            (<RegisterPanel/>)
        }
    </div>
    </>
    );
}

export {Register};