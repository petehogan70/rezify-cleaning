import { useMemo, useState } from "react";
import "../index.css";

function Index() {
    const [url, setUrl] = useState("");
    const [error, setError] = useState("");
    const [status, setStatus] = useState("idle"); // idle | loading | done | error
    const [result, setResult] = useState(null);

    const cardVariant = useMemo(() => {
        if (status === "loading" || status === "error") return "neutral";

        if (status === "done") {
            const decision = (result?.decision || "").toUpperCase();
            if (decision === "KEEP") return "keep";
            if (decision === "DELETE") return "delete";
        }

        return "neutral";
    }, [status, result]);

    async function onCheckLink() {
        setError("");

        const trimmed = url.trim();
        if (!trimmed) {
            setError("Please enter a job link.");
            return;
        }

        setStatus("loading");
        setResult(null);

        try {
            const response = await fetch("/check_job", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                credentials: "include",
                body: JSON.stringify({ final_url: trimmed })
            });

            const data = await response.json();

            if (!response.ok) {
                setError(data?.error || "Backend error");
                setStatus("error");
                return;
            }

            setResult(data);
            setStatus("done");

        } catch (err) {
            setError(`Request failed: ${err.message}`);
            setStatus("error");
        }
    }

    function onKeyDown(e) {
        if (e.key === "Enter") {
            onCheckLink();
        }
    }

    return (
        <div className="check-page">
            <div className="check-card">

                <div className="check-header">
                    <h1 className="check-title">Job Link Status Checker</h1>
                    <p className="check-subtitle">
                        Paste a job posting URL to see if it is still active.
                    </p>
                </div>

                <div className="check-form">
                    <label className="check-label">Job URL</label>

                    <div className="check-row">
                        <input
                            className="check-input"
                            type="text"
                            placeholder="https://..."
                            value={url}
                            onChange={(e) => setUrl(e.target.value)}
                            onKeyDown={onKeyDown}
                            disabled={status === "loading"}
                        />

                        <button
                            className="check-button"
                            onClick={onCheckLink}
                            disabled={status === "loading"}
                        >
                            {status === "loading" ? "Checking..." : "Check Link"}
                        </button>
                    </div>

                    {error && <div className="check-error">{error}</div>}
                </div>

                {(status === "loading" || status === "done") && (
                    <div className={`result-card ${cardVariant}`}>
                        {status === "loading" ? (
                            <div className="result-loading">
                                <div className="spinner"></div>
                                <div className="result-loading-text">
                                    Checking job posting…
                                </div>
                            </div>
                        ) : (
                            <div className="result-grid">
                                <div className="result-field">
                                    <div className="result-label">URL Used</div>
                                    <div className="result-value result-mono">
                                        <a
                                            href={result.final_url}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            className="result-link"
                                        >
                                            {result.final_url}
                                        </a>
                                    </div>
                                </div>

                                <div className="result-field">
                                    <div className="result-label">Decision</div>
                                    <div className="result-value result-strong">
                                        {result.decision}
                                    </div>
                                </div>

                                <div className="result-field">
                                    <div className="result-label">Used</div>
                                    <div className="result-value">
                                        {result.used}
                                    </div>
                                </div>

                                <div className="result-field result-span-2">
                                    <div className="result-label">Reason</div>
                                    <div className="result-value">
                                        {result.reason || "—"}
                                    </div>
                                </div>
                            </div>
                        )}
                    </div>
                )}

            </div>
        </div>
    );
}

export { Index };
