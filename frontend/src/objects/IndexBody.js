import React, { useRef } from "react";
import { useEffect, useState } from 'react';
import Lottie from "lottie-react";
import { useNavigate } from "react-router-dom";
import animationData from "../indexAnim.json";
import { IndexAIDemo } from "./IndexAIDemo";
import { Autocomplete } from "./Autocomplete";
import { useTheme } from "../hooks/ThemeContext";
import { driver } from "driver.js";
import "driver.js/dist/driver.css";
import "../styles/TutorialDriver.css";
import { TourButton } from "./TourButton";
import '../styles/NewIndexPage.css';
import { IndexFeatures } from './IndexFeatures';

function IndexBody({user={'na': true}, errormessage=""}) {
    const [locationOn, setLocationOn] = useState(false); //Location box open or not
    const [location, setLocation] = useState(""); //Location value
    const [termsOn, setTermsOn] = useState(false); //Terms box open or not
    const resume = useRef(null); //Reference to resume submit form
    const progressBarRef = useRef(null); //Reference to progress bar
    const progressBarFillRef = useRef(null); //Reference to fill of progress bar
    const transitionOverlayRef = useRef(null); //Reference to transition overlay
    const theForm = useRef(null); //Reference to main form
    const termsCheck = useRef(null); //Reference to terms checkbox                  
    const locationRef = useRef(null); //Reference to location box

    const [dropOpen, setDropOpen] = useState(false); //dropdown hover
    const [profileOpen, setProfileOpen] = useState(false); //profile hover w/ delay
    const [currProfileOpen, setCurrProfileOpen] = useState(false); //profile hover
    const [logoutLoad, setLogoutLoad] = useState(false); //loading spinner for logging out
    const [deleteLoad, setDeleteLoad] = useState(false); //loading spinner for delete account
    const currProfileRef = useRef(currProfileOpen); //extra for hover

    const INDEX_TUTORIAL = 'index_tutorial'; //localStorage key for the index tutorial status
    const driverRef = useRef(driver({
        showProgress: true,
        disableActiveInteraction: true,
        overlayClickBehavior: () => {},
        smoothScroll: true,
        popoverClass: 'rezify-theme',
        onCloseClick: () => {
            localStorage.setItem(INDEX_TUTORIAL, true);
            driverRef.current.destroy();
        },
        steps: [
            {
                popover: {
                    title: 'Welcome to Rezify!',
                    description: 'Would you like to take a quick tour to get started?',
                    disableButtons: [],
                    nextBtnText: 'Start Tour',
                    prevBtnText: 'Skip Tour',
                    showProgress: false,
                    onPrevClick: () => {
                        driverRef.current.moveTo(4);
                    }
                }
            },
            {
                element: '.big-button',
                popover: {
                    title: 'Upload Resume',
                    description: 'Upload your resume for analysis.',
                    side: 'right'
                }
            },
            {
                element: '.cta-right',
                popover: {
                    title: 'Terms and Conditions',
                    description: 'You may filter by location here and on the results page. Accept the terms and'
                    + ' conditions to view your results.',
                    side: 'right'
                }
            },
            {
                element: '.login-profile-section',
                popover: {
                    title: 'Login/Profile',
                    description: 'You can login here or on the results page. When logged in,'
                    + ' you will be able to access your profile/results from this navigation bar.',
                    side: 'right'
                }
            },
            {
                element: '.tour-button',
                popover: {
                    title: 'Review Tour',
                    description: 'You may review this tour anytime by clicking this button.',
                    side: 'top',
                    onNextClick: () => {
                        localStorage.setItem(INDEX_TUTORIAL, true);
                        driverRef.current.moveNext();
                    }
                }
            }
        ]
    }));

    useEffect(() => {
        if (!localStorage.getItem(INDEX_TUTORIAL)) {
            driverRef.current.drive();
        }
    }, []);

    const {theme} = useTheme(); //get logo from theme

    const navigate = useNavigate(); //SPA (Single-page-architecture) navigator

    useEffect(() => {
        currProfileRef.current = currProfileOpen; //extra for hover
        }, [currProfileOpen]); 

    const OnLogout = () => {
        setLogoutLoad(true);
        fetch('/api/logout', {method: 'POST'}).then(data => {
            setLogoutLoad(false);
            window.location.href = '/';
        });
    }

    const OnDeleteAccount = () => {
        const confirmed = window.confirm("Are you sure you want to delete your account?");
        setDeleteLoad(true);
        if (confirmed) {
          fetch('/api/delete_account', {method: 'POST'}).then(data => {
            setDeleteLoad(false);
            window.location.href = '/';
          });
        } else {
          setDeleteLoad(false);
        }
      }


    var cityStateMap = {};

    const HandleSubmit = (event) => {
        event.preventDefault();
        const overlay =  transitionOverlayRef.current;
        if (/*fade for now*/false && (locationOn && (!location || !cityStateMap[location]))) {
            alert("Please select a valid location from the list.");
            return;
        } else {
            overlay.classList.add('show');
            let formdata = new FormData(theForm.current);
            formdata.append('location', location);
            setTimeout(async () => {
                const result = await fetch('/api/index', {
                    method: 'POST',
                    body: formdata,
                }) //send form data post request
                if (result.ok) {
                    result.json().then(data => {
                        if (data.redirect) {
                            //window.location.href = data.redirect;
                            navigate(data.redirect);
                        } else {
                            //do an error message: invalid response, something terrible has happened in this case
                            overlay.classList.remove('show')
                            if (data.error_message) {
                                alert("Error: " + data.error_message);
                            } else {
                                alert("Unknown error")
                            }
                        }
                    });
                } else {
                    //do an error message
                    alert("Error:" + result.statusText);
                    overlay.classList.remove('show')
                }
            }, 1500);
        }
    }
    
    const ValidateResume = (event) => {
        if (!resume.current) {
            event.preventDefault();
            return;
        }
    
        if (!resume.current.files.length) {
            event.preventDefault();
            alert("Upload a resume using the center button.");
            return;
        }
    
        if (!(termsCheck.current) || !(termsCheck.current.checked)) {
            event.preventDefault();
            alert("You must accept the Terms and Conditions to proceed.");
            return;
        }
        HandleSubmit(event);
    }

    const ValidateFile = () => {
        const fileInput = resume.current;
        const file = fileInput.files[0];
    
        if (file) {
            const maxSizeKB = 800;
            const maxSizeBytes = maxSizeKB * 1024; // 400 KB
    
            if (file.size > maxSizeBytes) {
                alert(`File is too large! Please upload a file smaller than ${maxSizeKB}KB.`);
                fileInput.value = ""; // Reset file input
            } else {
                showFileName(file.name);
            }
        }
    }
    
    const showFileName = () => {
        const input = resume.current;
        const file = input.files[0];
        const fileNameElement = document.getElementById('file-name');
    
        if (file && file.type === 'application/pdf') {
            const fileName = file.name;
            fileNameElement.textContent = `Selected File: ${fileName}`;
            fileNameElement.classList.add('attached');
            const progressBar = progressBarRef.current;
            const progressBarFill = progressBarFillRef.current;
            progressBar.style.display = 'block';
            progressBarFill.style.width = '0';
            progressBarFill.style.animation = 'loading 1s ease-in-out forwards';
            setTimeout(() => {
                fileNameElement.classList.remove('attached');
                progressBar.style.display = 'none';
                if (user && user.resume_file && user.resume_file.length >= 1 & user.plan === "basic") {
                    navigate("/plans?redirect=results&msg=1")
                }
            }, 2000);
        } else {
            fileNameElement.textContent = 'Attach Resume (PDF)';
            fileNameElement.classList.remove('attached');
            alert('Please upload a valid PDF file.');
        }
    }

    const scrollAndHighlight = (id) => {
      const el = document.getElementById(id);
      if (el) {
        // Scroll to the element and center it in the viewport
        el.scrollIntoView({ behavior: 'smooth', block: 'center' });

        // Clear and reapply highlight class
        el.classList.remove('flash-highlight');
        setTimeout(() => {
          el.classList.add('flash-highlight');

          // Remove highlight after animation
          setTimeout(() => {
            el.classList.remove('flash-highlight');
          }, 1500);
        }, 500); // Delay to let scroll finish
      }
    };

    const isRootDomain = window.location.hostname.split(".").length === 2;


    return (
        <>
    <TourButton driver={driverRef.current}></TourButton>
    <div className="header-banner">
      <div className="header-left" onClick={() => navigate('/')}>
        <img src={theme.logo} alt="Rezify Logo" className="header-logo" />
        <span className="header-title">Rezify</span>
      </div>

      <div className="header-center">
        <button onClick={() => scrollAndHighlight('cta-left')} className="header-link">Search</button>
        <a href="#features-section" className="header-link">Features & Filters</a>
        {isRootDomain && (
          <>
            <a href="#pricing-plans" className="header-link">Pricing</a>
            <a href="#pricing-plans" className="header-link">For Students</a>
            <a href="#university-info-section" className="header-link">For Universities</a>
          </>
        )}
        <a href="#about-us-section" className="header-link">About Us</a>
        <a href="#index-footer" className="header-link">Contact</a>
        <a href="/help" className="header-link">Help</a>
      </div>

      <div className="header-right">
                {errormessage.length >= 1 &&
            <div id="fail-popup" class="fail-popup">{ errormessage }</div>
                }

            {!isRootDomain && (
                <>

                <button onClick={() => {
                navigate('/login?type=admin');
              }} class="hero-nav__btn">Admin Portal</button>

                </>
            )}

            <a href="/feedback"
               target="_blank"
               class="hero-nav__btn">Feedback</a>

           <div className="header-divider"></div>


            { !(user.error) && !(user.na) && !(user.id) && <div className="spinner-aw"></div>}
        {user.id &&
            <>
            {user.id && user.plan === "basic" && <a href={"/plans?redirect=index"} className='hero-nav__btn' style={{'box-shadow': '0 0px 15px var(--primary-aw)'}}>Upgrade</a>}
            {user.id && user.plan === "premium" && user.stripe_meta && user.stripe_meta.subscription_to_be_cancelled&& <a href={"/plans?redirect=index"} className='hero-nav__btn' style={{'box-shadow': '0 0px 15px var(--primary-aw)'}}>Reactivate</a>}

            <div className="login-profile-section">

            <div tabindex="0" class="profile-text" onClick={()=>{
                navigate('/profile');
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
                    {(user && user.subscription_status !== "active") && <form id="delete-account-form" action="" method="post">
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
               </div>
          </>
        }
        {user.na &&

        <div className="login-profile-section">
          <button onClick={() => {
            navigate('/login');
          }} class="hero-nav__btn">
            { !isRootDomain ? 'Student Login' : 'Login' }
          </button>

        </div>
        }

      </div>
    </div>

    <div class="hero">

  <div class="hero-left">
    <h1 class="hero-title">
      From <span style={{color: 'var(--primary-color)'}}>Campus</span> to <span style={{color: 'var(--primary-color)'}}>Career</span>.<br/>
      Your <span style={{color: 'var(--primary-color)'}}>Internship</span> Search Starts Here.
    </h1>

    <div class="hero-cta">
      <div id="cta-left" class="cta-left">
        <button class="big-button" onClick={() => {
            if (resume.current) {
                const fileNameElement = document.getElementById('file-name');
                if (fileNameElement) {
                    fileNameElement.classList.remove('attached');
                    fileNameElement.textContent = "Attach Resume (PDF)";
                }
                resume.current.click()
            }
        }}>
          <img src={theme.logo} alt="Theme Logo" />
          <div class="ai-icon"></div>
        </button>
        <div class="progress-bar" ref={progressBarRef}>
                    <div class="fill" ref={progressBarFillRef}></div>
                </div>
        <div id="file-name" style={{textAlign: 'center'}}>Attach Resume (PDF)
          <div class="tooltip">Click big button to attach resume</div>
        </div>

        <form method="POST" enctype="multipart/form-data" onSubmit={(event) => {
            HandleSubmit(event);
        }} ref={theForm}>
        <input type="file" id="resume" name="resume"
               accept=".pdf"
               className="file-inp"
               onChange={() => {
                ValidateFile();
               }}
               ref={resume}
               required />
            </form>

      </div>

      <div class="cta-right">
        <button class="action-button" onClick={(event) => {
            if (user && user.plan === "basic" && user.resume_file && user.resume_file.length >= 1) {
                event.preventDefault();
                navigate("/results");
            } else {
                ValidateResume(event);
            }
        }}>
          Search Internships
        </button>

        <label class="checkbox-label">
          <input type="checkbox" id="location-checkbox"
                 onClick={(event) => {
                    setLocationOn(event.target.checked);
                 }}/>
          Specify Location?
        </label>
        {locationOn &&
                        (<div id="location-container">
                            <Autocomplete ref={locationRef} setLocation={setLocation}/>
                            <div id="mile-container">
                                <label for="miles">within</label>
                                <input type="number" id="miles" name="miles" defaultValue="50" min="1" max="2000" className='milesInput' onChange={(event) => {
                                    //setLocation(event.target.value);
                                }}/>
                                <span>mi</span>
                            </div>
                        </div>)
                    }

        <label class="checkbox-label">
          <input type="checkbox" id="terms-checkbox" ref={termsCheck} onChange={(event) => {
          }}/>
          <span>
          I accept the <br/><a onClick={() => {setTermsOn(!termsOn)}} class="terms-link">Terms and Conditions</a>
          </span>
        </label>
        {termsOn && <div id="terms-modal" class="modal">
                        <div class="modal-content">
                            <span class="close-btn" onClick={() => {setTermsOn(!termsOn)}}>&times;</span>
                            <h2>User Terms and Conditions</h2>
                            <p>Rezify considers a “User” to be anyone who uploads a resume into the Rezify application in order to find an internship, co-op, H1 or job opportunity. The User agrees that said User will protect their personal information protected by HIPAA and FERPA rules, and therefore will NOT include personal information such as address, social security number, student ID number, address, or other such information. If User provides their name, e-mail, a contact phone number, or other such information, User does so of their own volition and assumes any risk for providing such information. User agrees to these terms and conditions by checking the acceptance box prior to utilizing Rezify.</p>
                        </div>
                    </div>}
      </div>
    </div>
  </div>

  <div class="hero-right">
      <div id="scanner-container">
        <Lottie
            animationData={animationData}
            loop={true}
            autoplay={true} // <-- this is default, but you can be explicit
            style={{ width: 300, height: 300 }}
            />
      </div>
      <div class="ai-demo-container">
        <IndexAIDemo/>
      </div>
      </div>

  {theme.logo && !theme.logo.includes("rezify") && (
      <div style={{
          position: 'absolute',
          bottom: '10px',
          left: '50%',
          transform: 'translateX(-50%)',
          textAlign: 'center'
      }}>
          <a href="https://rezify.ai" style={{
              color: 'var(--primary-color)',
              textDecoration: 'underline',
              fontWeight: '500'
          }}>
              Leave School Portal
          </a>
      </div>
    )}

  </div>

  <IndexFeatures theme={theme} transitionOverlayRef={transitionOverlayRef} />

  </>

  );

}

export {IndexBody};
