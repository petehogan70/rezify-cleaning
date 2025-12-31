import { useState } from "react";
import "../styles/HelpPage.css";
import { useNavigate } from "react-router-dom";

function Help() {
    const [error_message, setErrorMessage] = useState("");
    const [waiting, setWaiting] = useState(false);
    const [success, setSuccess] = useState('none');

    const HandleSubmission = async (event) => {
        event.preventDefault();
        setErrorMessage("");
        setWaiting(true);

        try {
            const response = await fetch("/api/submit_help", {
                method: "POST",
                body: new FormData(event.target),
            });

            const result = await response.json();

            if (result.status === 'success') {
                setSuccess('success');
            } else {
                setErrorMessage("Error: Could not submit right now.");
                setWaiting(false);
                setSuccess('error');
            }
        } catch (error) {
            setErrorMessage("Error: Could not submit right now.");
            setWaiting(false);
            setSuccess('error');
        }
    };

    const navigate = useNavigate();

    return (
        <div className="help-page">
            <div className="container">
                <div className="help-header">
                    <button
                        className="back-btn"
                        onClick={() => navigate("/")}
                    >
                        ← Back
                    </button>

                    <div className="help-header-text">
                        <h1>Rezify Help</h1>
                    </div>
                </div>

                <div className="card contact-card">
                    <div className="card-title-row">
                        <h2>Contact us</h2>
                        <span className="pill">Fast response</span>
                    </div>

                    <p className="muted">
                        If your issue isn’t covered below, send us a note here
                        or email{" "}
                        <a href="mailto:support@rezify.ai">
                            support@rezify.ai
                        </a>.
                    </p>

                    <form
                        method="post"
                        onSubmit={HandleSubmission}
                        className="contact-form"
                    >
                        <div className="form-grid">
                            <div className="field">
                                <label>Email</label>
                                <input
                                    type="email"
                                    name="email"
                                    placeholder="you@school.edu"
                                    maxLength={50}
                                    required
                                />
                            </div>

                            <div className="field field-full">
                                <label>What’s going on?</label>
                                <textarea
                                    name="problem"
                                    rows="3"
                                    placeholder="Describe your problem"
                                    required
                                />
                            </div>
                        </div>

                        {error_message && (
                            <div className="error-message">
                                {error_message}
                            </div>
                        )}

                        <div className="submit-section">
                            {success === 'none' && (
                                <button
                                    type="submit"
                                    disabled={waiting}
                                >
                                    {waiting ? (
                                        <span className="btn-inline">
                                            <span className="spinner-black" />
                                            Submitting…
                                        </span>
                                    ) : (
                                        "Submit"
                                    )}
                                </button>
                            )}

                            {success === 'success' && (
                                <div className="success-box">
                                    ✅ Thanks for your submission! We’ll reach out soon.
                                </div>
                            )}

                            {success === 'error' && (
                                <div className="error-box">
                                    Submission error
                                </div>
                            )}
                        </div>
                    </form>
                </div>

                <div className="faq-header">
                    <h2>FAQ</h2>
                </div>

                <div className="faq-list">
                    <div className="faq-item card">
                        <h3>Why can't I access the results page?</h3>
                        <div className="img-wrap">
                            <img
                                src="/static/faq/faq1.png"
                                alt="FAQ 1 image"
                            />
                        </div>
                        <p>
                            In order to access the results page, you must be
                            logged in. You can do this by either logging in
                            to your existing account or registering an account.
                            At the moment, Rezify only gives access to users
                            with a valid .edu email address.
                        </p>
                    </div>

                    <div className="faq-item card">
                        <h3>What do the search filters at the top mean?</h3>
                        <div className="img-wrap">
                            <img
                                src="/static/faq/faq2.png"
                                alt="FAQ 2 image"
                            />
                        </div>
                        <p>
                            These are the job titles that you are searching for.
                            Our matching algorithm matches based on these search
                            titles as well as the skills and experiences from
                            your resume.
                        </p>
                    </div>

                    <div className="faq-item card">
                        <h3>How can I use the search filters?</h3>
                        <div className="img-wrap">
                            <img
                                src="/static/faq/faq3.png"
                                alt="FAQ 3 image"
                            />
                        </div>
                        <p>
                            By clicking on any of the search filters, you isolate
                            based on those search terms. If none are selected,
                            results for all titles will be returned.
                        </p>
                    </div>

                    <div className="faq-item card">
                        <h3>How can I edit my search titles?</h3>
                        <div className="img-wrap">
                            <img
                                src="/static/faq/faq4.png"
                                alt="FAQ 4 image"
                            />
                        </div>
                        <p>
                            You can remove search terms using the “x” or add new
                            ones using the “+” button to refine results.
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
}

export { Help };
