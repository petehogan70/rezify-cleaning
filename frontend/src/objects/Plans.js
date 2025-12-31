import { useEffect, useState } from "react";
import { IndexHeader } from "./IndexHeader"
import { updateColors, useTheme } from "../hooks/ThemeContext";
import "../styles/PlansPage.css"
import { useNavigate, useSearchParams } from "react-router-dom";
import { BasicFooter } from "./BasicFooter";


function Plans() {
    const [currUser, setCurrentUser] = useState({});
    const [isLoaded, setIsLoaded] = useState(false); //backend response complete or not
    const {setTheme} = useTheme();
    const [searchParams] = useSearchParams();

    const navigate = useNavigate();

    const [mainMessage, setMainMessage] = useState("Please select a plan");

    useEffect(() => {
        if (searchParams.get("msg") == "1") {
            setMainMessage("Upgrade to upload multiple resumes");
        } else {
            setMainMessage("Please select a plan");
        }
    }, [searchParams]);

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
                //navigate("/login")
            }

            if (data.error_message) {
                //doesn't really matter in this scenerio
            }
            setIsLoaded(true);
          } else {
            setCurrentUser({'error': true})
            //error, prob shouldnt log in
            setIsLoaded(true);
          }
        })
      }, []);

    return (
      <>
        <header>
          <div className="top-header" id="top-header">
            <IndexHeader
              user={currUser}
              firstWait={isLoaded}
              upgradeRedirect={searchParams.get("redirect") ? searchParams.get("redirect") : "results"}
            />
          </div>
        </header>

        {isLoaded ? (
          <section id="pricing-plans" className="plans-section">

            <div className="plans-flex-container">
              {/* Left side — Feature card */}
              <div className="plans-feature-card feature">
                <h2>Pricing Info</h2>
                <div className="feature-text">
                  <ul>
                    <li>
                      All transactions & billing securely handled by <strong>Stripe</strong>.
                    </li>
                    <li>
                      <strong>Cancel easily</strong> at any time, for any reason.
                    </li>
                    <li>
                      With <strong>premium</strong>, unlock <strong>unlimited access</strong> to all of our features!
                    </li>
                  </ul>
                  <p style={{ marginTop: 12 }}>
                    Good news! If your <strong>University partners with Rezify</strong>, you get premium access for{" "}
                    <strong>Free!</strong>
                  </p>
                </div>
              </div>

              {/* Right side — Plans */}
              <div className="plans-container">
                {/* Free Plan */}
                <div
                  className="plan-card"
                  style={{
                    border:
                      (currUser && currUser.plan === "premium") || currUser.na ? "none" : "4px solid #333",
                  }}
                >
                  <div className="plan-left">
                    <h2>Free Plan</h2>
                    <h3>$0.00/month</h3>
                    {!currUser.na && (
                      <>
                        {!(currUser && currUser.plan === "premium") && (
                          <button
                            className="basic"
                            onClick={() => {
                              const redir = searchParams.get("redirect");
                              if (redir) {
                                window.location.href = redir;
                              } else {
                                window.location.href = "/";
                              }
                            }}
                          >
                            Select
                          </button>
                        )}
                      </>
                    )}
                  </div>
                  <ul>
                    <li>4 Search Titles</li>
                    <li>Results Refresh Weekly</li>
                    <li>25 Results Per Search</li>
                    <li>Max 1 Resume</li>
                  </ul>
                </div>

                {/* Premium Plan */}
                <div
                  className="plan-card premium-accent"
                  style={{
                    backgroundColor: "color-mix(in srgb, white, var(--primary-color) 20%)",
                    border: currUser && currUser.plan === "premium" ? "4px solid var(--primary-aw)" : "none",
                  }}
                >
                  <div className="plan-left">
                    <h2 style={{ color: "color-mix(in srgb, var(--primary-color), black 20%)" }}>Premium Plan</h2>
                    <h3 style={{ color: "color-mix(in srgb, var(--primary-color), black 20%)" }}>$4.99/month</h3>

                    {!currUser.na && (
                      <button
                        className="premium"
                        onClick={() => {
                          if (currUser && currUser.plan === "premium") {
                            const redir = searchParams.get("redirect");
                            if (redir) {
                              window.location.href = redir;
                            } else {
                              window.location.href = "/";
                            }
                          } else {
                            navigate("/payment");
                          }
                        }}
                      >
                        <b>{currUser && currUser.plan === "premium" ? "Select" : "Purchase"}</b>
                      </button>
                    )}
                  </div>

                  <ul>
                    <li style={{ color: "color-mix(in srgb, var(--primary-color), black 20%)" }}>
                      <div className="emoji">🔧</div>
                      <b>Fully Customizable Search</b>
                    </li>
                    <li style={{ color: "color-mix(in srgb, var(--primary-color), black 20%)" }}>
                      <div className="emoji">⏱️</div>
                      <b>24/7 Up-To-Date Results</b>
                    </li>
                    <li style={{ color: "color-mix(in srgb, var(--primary-color), black 20%)" }}>
                      <div className="emoji">🔎</div>
                      <b>Unlimited Results</b>
                    </li>
                    <li style={{ color: "color-mix(in srgb, var(--primary-color), black 20%)" }}>
                      <div className="emoji">📄</div>
                      <b>Unlimited Resumes</b>
                    </li>
                  </ul>
                </div>

                {/* Back button for not-logged-in */}
                {currUser.na && (
                  <button
                    className="back-button"
                    onClick={() => {
                      const redir = searchParams.get("redirect");
                      if (redir) {
                        navigate("/" + redir);
                      } else {
                        navigate("/");
                      }
                    }}
                  >
                    Back
                  </button>
                )}
              </div>
            </div>
          </section>
        ) : (
          <div className="spinner" style={{ margin: "auto" }} />
        )}

        <BasicFooter />
      </>
    );

}

export {Plans}