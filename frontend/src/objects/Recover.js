import { useEffect, useState } from "react"
import "../styles/RegisterPage.css"
import { useNavigate } from "react-router-dom";


function Recover() {
    const [recover, setRecover] = useState(false); //if on /recover or /change_password
    const [user_email, setUserEmail] = useState(""); //user email sent
    const [error_message, setErrorMessage] = useState(""); //error message
    const [firstWait, setFirstWait] = useState(false); //First page load, false = backend hasn't responded yet, true = backend finished response
    const [loadWait, setLoadWait] = useState(false); //On button click, waiting for POST backend result
    const [notifyWaiting, setNotifyWaiting] = useState(false);
    const [notifySuccess, setNotifySuccess] = useState('none');


    useEffect(() => {
        // Only run once when component mounts
        setFirstWait(false);
        fetch('/api/change_password').then(response => {
            if (response.ok) {
                response.json().then(data => {
                    if (data.user_email) setUserEmail(data.user_email);
                    if (data.recover) setRecover(true); // Set mode, but don't trigger another fetch
                    setFirstWait(true); // Mark fetch as complete
                });
            } else {
                setErrorMessage("Error: " + response.statusText);
                setFirstWait(true); // Mark fetch as complete even on failure
            }
        });
    }, []); // <== empty dependency array = run once on load

    const triggerRecoverFlow = async () => {
        setLoadWait(true); // spinner state
        // setRecover(true); // switch to recover mode
        try {
            const result = await fetch('/api/recover', {
                method: 'GET'
            });

            if (result.ok) {
                const data = await result.json();
                if (data.redirect) {
                    window.location.href = data.redirect;
                } else if (data.error_message) {
                    setErrorMessage(data.error_message);
                }
            } else {
                setErrorMessage("Error: " + result.statusText);
            }
        } catch (err) {
            console.error("Recover request failed:", err);
            setErrorMessage("Unexpected error occurred.");
        } finally {
            setLoadWait(false);
        }
    };


    const onSubmit = (event) => {
        event.preventDefault();
        setLoadWait(true);
        fetch('/api/change_password', {
            method: 'POST',
            body: new FormData(event.target),
        }).then(response => {
            if (response.ok) {
                response.json().then(data => {
                    if (data.redirect) {
                        window.location.href = data.redirect;
                    } else {
                        if (data.error_message) {
                            setErrorMessage("Error: " + data.error_message);
                        } else {
                            setErrorMessage("Unknown error");
                        }
                    }
                    setLoadWait(false);
                });
            } else {
                setErrorMessage("Error: " + response.statusText);
                setLoadWait(false);
            }
        })
    }

    async function notifyPasswordRecoveryError(email) {
        try {
            const response = await fetch('/api/notify_password_recovery_not_received', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    email: email
                }),
            });

            const result = await response.json();

            if (result.status === 'success') {
                setNotifySuccess('success');
                setNotifyWaiting(false);
            } else {
                setNotifySuccess('error');
                setNotifyWaiting(false);
            }
        } catch (error) {
            setNotifySuccess('error');
            setNotifyWaiting(false);
        }
    }


    const navigate = useNavigate();
    
    return (<div className="container">
        <button style={{position: 'absolute', left: 10, top: 10, padding: 5}} onClick={() => {
            navigate("/");
        }}>←</button>
        {
        !firstWait ? <div style={{display: 'inline-block'}} className="spinner-black"/>
        :
        <>
        {recover ?
        <>
          <h1>Recover Password</h1>
          <form method="post" onSubmit={(event) => {
            onSubmit(event);
          }}>
              {!firstWait ? <div className="spinner"/> : <p>Enter recovery code sent to { user_email }</p>}
              <p>It may take up to a minute or 2 to receive the email.</p>
              <input type="hidden" name="type" value="recover" />
              <input type="text" autoComplete="off" name="code" placeholder="Code" required maxlength="6" minlength="6" />
              <input type="password" name="password" placeholder="New Password" required minlength="8" maxlength="40" />
              <input type="password" name="confirm_password" placeholder="Confirm New Password" required minlength="8" maxlength="40" />
              <button type="submit">{loadWait ? <div className="spinner"/> : "Confirm"}</button>
              {error_message.length >= 1 &&
                  <p className="error-message">{ error_message }</p>
              }
          </form>
          <button className="toggle-form" onClick={triggerRecoverFlow}>Send Code Again</button>
          <div className="register-divider"></div>

            <div className="support-row">
                {notifySuccess !== 'error' && notifySuccess !== 'success' && (
                    <>
                        <span className="support-text">
                            Not receiving email?:
                        </span>

                        {!notifyWaiting && (
                            <button
                                type="button"
                                className="support-button"
                                disabled={notifyWaiting}
                                onClick={() => {
                                    setNotifyWaiting(true);
                                    notifyPasswordRecoveryError(user_email);
                                }}
                            >
                                Notify Support
                            </button>
                        )}

                        {notifyWaiting && <span className="support-spinner"></span>}

                        <span className="tooltip-container">
                            <span className="tooltip-icon">?</span>
                            <span className="tooltip-text">
                                Sends a support notification to the Rezify team to help resolve password recovery email issues.
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
        :
        <>
            <h1>Change Password</h1>
            <form method="post"  onSubmit={(event) => {
                onSubmit(event);
            }}>
                {!firstWait ? <div className="spinner"/> : <p>Change password for { user_email }</p>}
                <input type="hidden" name="type" value="change" />
                <input type="password" name="old_password" placeholder="Current Password" required maxlength="40"/>
                <input type="password" name="password" placeholder="New Password" required minlength="8" maxlength="40"/>
                <input type="password" name="confirm_password" placeholder="Confirm New Password" required minlength="8" maxlength="40"/>
                <button type="submit">{loadWait ? <div className="spinner"/> : "Confirm"}</button>
                {error_message.length >= 1 && <>
                    <p className="error-message">{ error_message }</p>
                </>}
                <button className="toggle-form" onClick={triggerRecoverFlow}>Forgot Password?</button>
            </form>
            </>
        }
        </>
    }
    </div>);
}

export {Recover}