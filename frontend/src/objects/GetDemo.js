import { useNavigate } from "react-router-dom";
import { useTheme } from '../hooks/ThemeContext';
import '../styles/GetDemoPage.css'

function GetDemo() {
    const {theme} = useTheme();
    const navigate = useNavigate();

    async function requestDemo(event) {
        event.preventDefault();

        // Check that all required fields are complete
        let formData = new FormData(event.target);
        let missing = [];
        for (let entry of formData.entries()) {
            if (entry[1] === "" && entry[0] !== "questions") {
                missing.push(entry[0]);
            }
        }
        if (missing.length > 1) {
            alert("Please complete all required fields.");
            return;
        } else if (missing.length === 1) {
            alert("Please enter your " + missing[0] + ".");
            return;
        }

        // Simple email validation - if there is a more complicated issue, the api request will catch it
        if (!/^.+@.+\..+$/.test(formData.get("email")) && !window.confirm("Your email doesn't look right. Are you sure you want to submit?")) {
            return;
        }

        // Submit demo request
        const response = await fetch('/api/request_demo', {
            method: 'POST',
            body: new FormData(event.target),
        });
        if (response.ok) {
            response.json().then(data => {
                if (!data.demo_request_sent) {
                    alert("Failed to request demo.");
                } else if (!data.demo_request_confirmation_sent) {
                    alert("Your demo request has been submitted, but we were unable to send a confirmation email. Please check that your email is correct and resubmit if necessary.");
                } else {
                    alert("Your demo request has been submitted! Please check your inbox and spam for a confirmation email with your responses. A member of our team will reach out to you shortly.");
                    event.target.reset();
                }
            });
        }
    }

    // info about Rezify, why to get demo, cost, what we are
    return (<>
        <button class="back-button" onClick={() => {
            navigate("..");
        }}>
            Back
        </button>
        <div class="row">
            <div class="column left">
                <div class="info-container">
                    <h1 class="info-container-child">About Rezify</h1>
                    <div class="info-container-child">
                        <h3>What is Rezify?</h3>
                        <ul>
                            <li>Rezify is an AI-powered platform that analyzes resumes and matches students with relevant internship postings.</li>
                        </ul>
                    </div>
                    <div class="info-container-child">
                        <h3>For Your Students</h3>
                        <ul>
                            <li><strong>Premium</strong> level access for entire student base.</li>
                            <li>H1 filter for <strong>international students.</strong></li>
                        </ul>
                    </div>
                    <div class="info-container-child">
                        <h3>For Your University</h3>
                        <ul>
                            <li>Custom school themed portal & secure domain.</li>
                            <li>Career center employees can view student usage statistics in our <strong>admin dashboard.</strong>
                          </li>
                         </ul>
                    </div>
                    <div class="info-container-child">
                        <h3>What is our cost structure?</h3>
                        <ul>
                            <li>University-wide plans starting at <strong>$1k for a 6 month trial.</strong></li>
                            <li>Have a select group of students (5-20) try premium before-hand for cheap!</li>
                            <li>Learn more by requesting a demo with us</li>
                        </ul>
                    </div>
                </div>
            </div>
            <div class="column right">
                <div class="info-container">
                    <h1 class="info-container-child">Request a Demo</h1>
                    <form class="info-container-child flex" onSubmit={(event) => requestDemo(event)}>
                        <table>
                            <tr>
                                <td class="required">University:</td>
                                <td><input id="university" name="university"></input></td>
                            </tr>
                            <tr>
                                <td class="required">Name:</td>
                                <td><input id="name" name="name"></input></td>
                            </tr>
                            <tr>
                                <td class="required">Position:</td>
                                <td><input id="position" name="position"></input></td>
                            </tr>
                            <tr>
                                <td class="required">Email:</td>
                                <td><input id="email" name="email"></input></td>
                            </tr>
                            <tr>
                                <td>Questions:</td>
                                <td><input id="questions" name="questions"></input></td>
                            </tr>
                            <tr>
                                <td></td>
                                <td style={{textAlign: "center"}}><button>
                                    Submit
                                </button></td>
                            </tr>
                        </table>
                    </form>
                </div>
            </div>
        </div>
    </>)
}

export {GetDemo}