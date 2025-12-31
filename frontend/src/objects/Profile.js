import { useEffect, useRef, useState } from "react";
import { IndexHeader } from "./IndexHeader"
import { updateColors, useTheme } from "../hooks/ThemeContext";
import "../styles/ProfilePage.css"
import { useNavigate, useSearchParams } from "react-router-dom";
import { BasicFooter } from "./BasicFooter";

function Profile() {
    const [currUser, setCurrentUser] = useState({});
    const [isLoaded, setIsLoaded] = useState(false); //backend response complete or not
    const [isProfileLoaded, setIsProfileLoaded] = useState(false); //backend response complete or not
    const [isBillingLoaded, setIsBillingLoaded] = useState(true); //backend response complete or not
    const {theme, setTheme} = useTheme();

    const theForm = useRef(); //Form to handle update profile

    const navigate = useNavigate();

    useEffect(() => {
        fetch(`/api/index`).then(async response => {
          //get flask backend response
          if (response.ok) {
            const data = await response.json();
            if (data.colors) {
                localStorage.setItem('theme-colors', JSON.stringify(data.colors));
                updateColors(data.colors, setTheme);
            }
            

            //get user if exists
            if (data.user) {
                //const userJson = await data.user.json();
                setCurrentUser(data.user);
            } else {
                setCurrentUser({
                    'na': true
                })
                navigate("/login")
            }

            if (data.error_message) {
                //doesn't really matter in this scenerio
            }
            setIsLoaded(true);
            setIsProfileLoaded(true);
          } else {
            setCurrentUser({'error': true})
            //error, prob shouldnt log in
            setIsLoaded(true);
            setIsProfileLoaded(true);
          }
        })
      }, []);

    const UpdateProfie = async () => {
        setIsProfileLoaded(false);
        fetch('/api/update_profile', {
            method: 'POST',
            body: new FormData(theForm.current),
        }).then(result => {
            if (result.ok) {
                result.json().then(data => {
                    if (data.user) {
                        setCurrentUser(data.user);
                    }
                    setIsProfileLoaded(true);
                });
            } else {
                setIsProfileLoaded(true);
            }
        })
    }

    const HandleBilling = async () => {
        setIsBillingLoaded(false);
        fetch('/api/get_billing', {
            method: 'POST'
        }).then(result => {
            if (result.ok) {
                result.json().then(data => {
                    if (data.redirect) {
                        window.location.href = data.redirect;
                    }
                    setIsBillingLoaded(true);
                });
            } else {
                setIsBillingLoaded(true);
            }
        })
    }

    return <>
            <header>
                <div class="top-header" id="top-header">
                    <IndexHeader user={currUser} firstWait={isLoaded} upgradeRedirect={"profile"}/>
                </div>
            </header>
            {isLoaded ?
            <div className="content">
                <div className="profile-container">
                    <div className="profile-left">
                        <img src="/static/pdf.png"/>
                        <p>Reusme uploaded: {currUser && currUser.resume_file}</p>
                        <div className="change-resume-btn">
                            {currUser.plan === "premium" ? <button onClick={() => {
                                navigate("/index?noredir=1")
                            }} className="update-button">
                                Change Resume
                            </button>
                            :
                            <>
                                <label className="disabled-button" style={{padding: 10}}>
                                    <span style={{padding: 10}}>Change Resume</span>
                                    <div className="tooltip">Upgrade to premium to upload a new resume</div>
                                </label>
                                
                            </>
                            }
                        </div>
                    </div>
                    <div className="profile-right">
                        {isProfileLoaded ?
                        <form onSubmit={(event)=>{
                            event.preventDefault();
                            UpdateProfie();
                        }} ref={theForm} className="profile-form">
                            <h1>Profile</h1>
                            <input type="email" id="email" name="email" value={currUser && currUser.email ? currUser.email : ""} disabled placeholder="Email"/>
                            <div className="college-input">
                                <label style={{ marginRight: 10 }}>College:</label>
                                <input
                                    type="text"
                                    name="reported_college"
                                    value={currUser?.reported_college || ""}
                                    disabled
                                    placeholder="College"
                                    style={{ flex: 1 }}
                                />
                            </div>
                            <div className="name-input">
                                <input type="text" name="first_name" defaultValue={currUser && currUser.first_name ? currUser.first_name : ""} placeholder="First Name" required/>
                                <input type="text" name="last_name" defaultValue={currUser && currUser.last_name ? currUser.last_name : ""} placeholder="Last Name" required/>
                            </div>
                            <div className="update-profile-btn">
                                <button onClick={() => {
                                    UpdateProfie();
                                }} className="update-button">
                                    Update Info
                                </button>
                            </div>
                            <br></br>
                            <p>Your current plan: {currUser.plan === "premium" ? <span style={{color: 'var(--primary-aw)'}}>Premium Plan</span> : "Basic Plan"}</p>
                            {currUser.plan === "premium" && currUser.stripe_meta && currUser.stripe_meta.subscription_to_be_cancelled && <p style={{marginTop: 0, fontSize: 10}}>Cancels <b>{new Date(currUser.stripe_meta.cancel_date * 1000).toDateString()}</b>❗️</p>}
                            {currUser.plan === "premium" && (currUser.subscription_status ? <div style={{alignItems: 'center', justifyContent: 'center', display: 'flex', width: '100%', marginTop: 10}}>
                                <button onClick={(event)=>{
                                    event.preventDefault();
                                    HandleBilling();
                                }}className="update-button" style={{alignItems: 'center', justifyContent: 'center', display: 'flex'}}>
                                {isBillingLoaded ? "Manage Subscription" : <div className="spinner"></div>}
                                </button>
                            </div> :
                            <p>Partnered with <img src={theme.logo} alt="Logo" style={{'vertical-align': 'middle', 'height': '30px'}} /></p>
                            )}
                            <br></br>
                        </form>
                        :
                        <div className="spinner"/>
                        }
                    </div>
                </div>
                {currUser.resume_file && <button onClick={() => {
                    navigate("/results")
                }} className="update-button">
                    Job Listings
                </button>}
            </div>
            :
            <div className="spinner" style={{margin: 'auto'}}/>
            }
            <BasicFooter/>
    </>
}

export {Profile}