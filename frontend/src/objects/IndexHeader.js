import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTheme } from '../hooks/ThemeContext';
import '../styles/NewIndexPage.css';

export const IndexHeader = ({
                              user, //User object
                              firstWait, //Whether user is loaded or not
                              upgradeRedirect="results"
                            }) => {
    const [dropOpen, setDropOpen] = useState(false);
    const [profileOpen, setProfileOpen] = useState(false);
    const [currProfileOpen, setCurrProfileOpen] = useState(false);
    const [logoutLoad, setLogoutLoad] = useState(false); //loading spinner for logging out
    const [deleteLoad, setDeleteLoad] = useState(false); //loading spinner for delete account

    const {theme} = useTheme();

    const navigate = useNavigate();

    const OnLogout = () => {
      setLogoutLoad(true);
      fetch('/api/logout', {method: 'POST'}).then(data => {
        setLogoutLoad(false);
        window.location.href = '/';
      });
    }

    const OnDeleteAccount = () => {
      const confirmed = window.confirm("Are you sure you want to delete your account?");
      if (!confirmed) return;

      setDeleteLoad(true);

      fetch('/api/delete_account', { method: 'POST' })
        .then(async response => {
          setDeleteLoad(false);

          const contentType = response.headers.get("content-type");
          if (contentType && contentType.includes("application/json")) {
            const json = await response.json();
            if (json.error_message === 'ActiveSubscription') {
              alert("You must cancel your subscription before deleting account.");
            } else {
              alert("Error deleting account.");
            }
          } else {
            const text = await response.text();
            if (text.trim() === 'success') {
              window.location.href = '/';
            } else {
              alert("Error deleting account.");
            }
          }
        })
        .catch(err => {
          setDeleteLoad(false);
          console.error("Fetch error:", err);
          alert("Error deleting account.");
        });
    };


    const currProfileRef = useRef(currProfileOpen);

    useEffect(() => {
        currProfileRef.current = currProfileOpen;
      }, [currProfileOpen]);

    return (<>
          <div onClick={() => {
            navigate("/index?noredir=1")
          }} style={{cursor: 'pointer'}}>
            <h1>Rezify <img src={theme.logo} alt="Logo" style={{'vertical-align': 'middle', 'height': '43px', 'margin-left': '10px'}} /> </h1>
          </div>
          <div class="top-links">
            { !firstWait && <div className="spinner"></div>}
            { !(user.id) && firstWait &&
              <button href="/login" className="login-button">Login</button>
            }
            { user.id && firstWait &&
            <>
              <div tabindex="0" className="profile-text" 
                onBlur={() => {
                  
                }}
                onClick={() => {
                navigate("/profile");
                }}
                onFocus={(event) => {
                setCurrProfileOpen(prev => !prev);
                setProfileOpen(prev => !prev);
              }} onMouseOver={(event) => {
                setCurrProfileOpen(true);
                setProfileOpen(true);
              }} onMouseOut={() => {
                setCurrProfileOpen(false);
                setTimeout(() => {
                    if (!currProfileRef.current) {                        
                        setProfileOpen(false);
                    }
                }, 100);
              }}>{ user.first_name }'s Profile</div>
              {(profileOpen || dropOpen) && <div className="dropdown-content" style={{display: 'block'}} onMouseOver={(event) => {
                setDropOpen(true);
              }} onMouseOut={() => {
                setDropOpen(false);
              }}>
                  <p>{ user.email } <button className="toggle-form" onClick={() => {
                    navigate('/change_password')
                  }}><u>Change Password</u></button></p>
                  <p>Resume: '{user.resume_file }'</p>
                  <p>Subscription: {user.plan === 'premium' ? 'Premium Plan' : 'Free Plan'}</p>
                  <form id="logout-form" action="" method="post" class="logout-text">
                      {logoutLoad ? <div className='spinner'/> : <button type="button" style={{borderColor: 'transparent', background: 'none', padding: 0, font: 'inherit', outline: 'inherit', color: 'blue', cursor: 'pointer'}} onClick={()=>{
                        OnLogout();
                      }} className='logout-button'>Logout</button>}
                  </form>
                {(user && user.subscription_status != "active") && <form id="delete-account-form" action="" method="post">
                      {deleteLoad ? <div className='spinner'/> : <button type="button" style={{borderColor: 'transparent', background: 'none', padding: 0, font: 'inherit', outline: 'inherit', color: 'red', cursor: 'pointer'}} onClick={()=>{
                            OnDeleteAccount();
                          }} className='delete-button'>Delete Account</button>
                        }
                  </form>}

                <button
                  type="button"
                  className="see-full-profile-btn"
                  onClick={() => navigate("/profile")}
                >
                  See Full Profile
                </button>
              </div>}
              </>
            }
            {user.id && user.plan != "premium" && firstWait && <a href={"/plans?redirect=" + upgradeRedirect} className='upgrade-button'>Upgrade</a>}
            {user.id && user.plan == "premium" && user.stripe_meta && user.stripe_meta.subscription_to_be_cancelled && firstWait && <a href={"/profile"} className='upgrade-button'>Reactivate</a>}

              <div class="top-right-link">
                  <a href="/feedback">Feedback Form</a>
              </div>

              <div class="top-right-link">
                  <a href="/help">Help</a>
              </div>
          </div>
    </>);
};