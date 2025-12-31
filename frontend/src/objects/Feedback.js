import { useState } from "react";
import "../styles/FeedbackPage.css";
import { useNavigate } from "react-router-dom";

function Feedback() {
    const [error_message, setErrorMessage] = useState("");
    const [waiting, setWaiting] = useState(false);
    const [success, setSuccess] = useState("none");

    const navigate = useNavigate();

    const HandleSubmission = async (event) => {
        event.preventDefault();
        setErrorMessage("");
        setWaiting(true);

        try {
            const response = await fetch("/api/submit_feedback", {
                method: "POST",
                body: new FormData(event.target),
            });

            const result = await response.json();

            if (result.status === "success") {
                setSuccess("success");
            } else {
                setSuccess("error");
                setWaiting(false);
                setErrorMessage("Error: Could not submit right now.");
            }
        } catch (error) {
            setSuccess("error");
            setWaiting(false);
            setErrorMessage("Error: Could not submit right now.");
        }
    };

    return (
        <div className="feedback-page">
            <div className="container">
                <div className="feedback-header">
                    <button
                        className="back-btn"
                        onClick={() => navigate("/")}
                    >
                        ← Back
                    </button>

                    <div className="feedback-header-text">
                        <h1>Rezify Feedback</h1>
                    </div>
                </div>

                <div className="card feedback-card">
                    <div className="card-title-row">
                        <h2>Tell us what you think</h2>
                        <span className="pill">We read everything</span>
                    </div>

                    <p className="muted">
                        Thank you for using Rezify! Any feedback, complaints, or requests are welcomed and appreciated.
                        Use this form to tell us about your results, request new features, or tell us how we could improve.
                        If you need support, leave your email address so we can reach out and help directly.
                    </p>

                    <form
                        method="post"
                        onSubmit={HandleSubmission}
                        className="feedback-form"
                    >
                        <div className="form-grid">
                            <div className="field">
                                <label>Your Email Address (optional)</label>
                                <input
                                    type="email"
                                    name="email"
                                    placeholder="you@school.edu"
                                    maxLength={50}
                                />
                            </div>
                        </div>

                        <div className="divider" />

                        <div className="ratings-grid">
                            <div className="rating-card">
                                <h3 className="rating-title">
                                    On a scale of 1-10, how good were your results?
                                </h3>
                                <div className="scale">
                                    {[1,2,3,4,5,6,7,8,9,10].map((n) => (
                                        <label key={`results-${n}`}>
                                            <input
                                                type="radio"
                                                name="results-rating"
                                                value={String(n)}
                                            />
                                            <span>{n}</span>
                                        </label>
                                    ))}
                                </div>
                            </div>

                            <div className="rating-card">
                                <h3 className="rating-title">
                                    On a scale of 1-10, how easy was Rezify to use?
                                </h3>
                                <div className="scale">
                                    {[1,2,3,4,5,6,7,8,9,10].map((n) => (
                                        <label key={`ease-${n}`}>
                                            <input
                                                type="radio"
                                                name="ease-rating"
                                                value={String(n)}
                                            />
                                            <span>{n}</span>
                                        </label>
                                    ))}
                                </div>
                            </div>
                        </div>

                        <div className="divider" />

                        <div className="form-grid">
                            <div className="field field-full">
                                <label>
                                    Any ideas for improvement for Rezify? What new features would you like to see?
                                </label>
                                <textarea
                                    name="improvements"
                                    rows="3"
                                    placeholder="Feature requests, improvements, missing filters, etc."
                                />
                            </div>

                            <div className="field field-full">
                                <label>Additional Comments</label>
                                <textarea
                                    name="comments"
                                    rows="3"
                                    placeholder="Anything else you want to share?"
                                />
                            </div>
                        </div>

                        {error_message && (
                            <div className="error-message">
                                {error_message}
                            </div>
                        )}

                        <div className="submit-section">
                            {success === "none" && (
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

                            {success === "success" && (
                                <div className="success-box">
                                    ✅ Thank you for providing feedback!
                                </div>
                            )}

                            {success === "error" && (
                                <div className="error-box">
                                    Submission error
                                </div>
                            )}
                        </div>
                    </form>
                </div>
            </div>
        </div>
    );
}

export { Feedback };
