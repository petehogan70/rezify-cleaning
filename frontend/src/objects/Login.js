
import React from "react";
import { useEffect, useState } from 'react';
import '../styles/LoginPage.css';
import { IndexFooter } from './IndexFooter';
import { BasicFooter } from "./BasicFooter";
import { useNavigate } from "react-router-dom";
import { useTheme } from "../hooks/ThemeContext";


function Login() {
    const [recover, setRecover] = useState(false);
    const [errorMessage, setErrorMessage] = useState("");
    const [userEmail, setUserEmail] = useState("");
    const [waiting, setWaiting] = useState(false);
    const [fromRecover, setFromRecover] = useState(false);
    const [adminLogin, setAdminLogin] = useState(false);


    const navigate = useNavigate();

    const {theme} = useTheme(); //get logo from theme

    useEffect(() => {
        const params = new URLSearchParams(window.location.search);
        if (params.get("fromRecover") === "true") {
            setFromRecover(true);
        }
    }, []);

    useEffect(() => {
        const params = new URLSearchParams(window.location.search);
        if (params.get("type") === "admin") {
            setAdminLogin(true);
        }
    }, []);


    function validateLoginForm(event) {
        const inputs = document.querySelectorAll('input[type="email"]');
        const forbiddenKeywords = ['DROP', 'DELETE', 'INSERT', 'UPDATE', 'SELECT', '--', ';'];

        for (let input of inputs) {
            const value = input.value.trim();
            const upperValue = value.toUpperCase();

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

        return true;
    }

    const HandleLogIn = async (event) => {
        event.preventDefault();
        setWaiting(true);
        const result = await fetch('/api/login', {
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

    const HandleAdminLogIn = async (event) => {
        event.preventDefault();
        setWaiting(true);
        const result = await fetch('/api/admin_login', {
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

    const HandleRecover = async (event) => {
        event.preventDefault();
        setWaiting(true);
        const result = await fetch('/api/recover', {
            method: 'POST',
            body: new FormData(event.target),
        }) //send form data post request
        if (result.ok) {
            result.json().then(data => {
                if (data.redirect) {
                    setWaiting(false);
                    window.location.href = data.redirect;
                } else {
                    //do an error message, recover prob unsuccessful
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

    return (<>
        <div class="container" style={{position: 'relative'}}>
        <button style={{position: 'absolute', left: 10, top: 10, padding: 5}} onClick={() => {
            navigate("/");
        }}>←</button>
        { recover &&
            (<>
                <h1>Recover Password</h1>
                <p>Enter account email to send recovery code to</p>
                <form method="post" onSubmit={(event) => {HandleRecover(event)}}>
                    <input type="email" name="email" placeholder="Email" required maxlength="50" />
                    <button type="submit">{!waiting && "Send"}{waiting && <div className="spinner"></div>}</button>
                    { errorMessage.length >= 1 &&
                        <p class="error-message">{ errorMessage }</p>
                    }
                </form>
                <button class="toggle-form" onClick={() => {window.location.href="/login"}}>Back to login</button>
            </>)
        }
        {!recover &&
        <>

            {adminLogin &&
                <>
                    <h1>Admin Login</h1>
                    <img src={theme.logo} alt="Rezify Logo" className="admin-logo"/>
                </>
            }
            {!adminLogin && <h1>Login</h1>}

            { userEmail.length >= 1 &&
                <p>Password successfully changed for {{ userEmail }}. Proceed to login</p>
            }
            <form method="post" onSubmit={(event) => {
                    if (validateLoginForm(event)) {
                        adminLogin ? HandleAdminLogIn(event) : HandleLogIn(event)
                    }
                }}>
                <input type="email" name="email" placeholder="Email" required maxlength="50" />
                <input type="password" name="password" placeholder="Password" required maxlength="40" />
                <button type="submit">{!waiting && "Login"}{waiting && <div className="spinner"></div>}</button>

                {fromRecover &&
                  <p className="success-message">Password changed successfully. Please login to proceed.</p>
                }

                
                { errorMessage.length >= 1 &&
                    <>
                    <p class="error-message">{ errorMessage }</p>
                    {errorMessage.includes('Invalid Credentials') &&
                        <button class="toggle-form" onClick={() => {setRecover(true); setErrorMessage("");}}>Forgot Password?</button>
                    }
                    </>
                }
            </form>
                <button
                  className="toggle-form"
                  onClick={() => {
                    window.location.href = adminLogin
                      ? "/register?type=admin"
                      : "/register";
                  }}
                >
                  Register
                </button>
            </>
        }
        </div>
        </>);
}

export {Login};