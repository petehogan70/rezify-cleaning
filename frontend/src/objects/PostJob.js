import { useState } from 'react';
import '../styles/PostJobPage.css'
import { Autocomplete } from './Autocomplete';
import { useNavigate } from 'react-router-dom';

function PostJob() {
    const [loadWait, setLoadWait] = useState(false); //show loading wheel on submit button

    const navigate = useNavigate();

    const OnSubmit = (event) => {
        event.preventDefault();
        setLoadWait(true);
        fetch('/api/post_job', {
            method: 'POST',
            body: new FormData(event.target),
        }).then((result) => {
            if (result.ok) {
                result.json().then(data => {
                    if (data.redirect) {
                        navigate(data.redirect);
                    }
                    setLoadWait(false);
                })
            } else {
                setLoadWait(false);
            }
        })
    }

    return (<div class="container">
        <h1>Post a New Job</h1>
        <form method="POST" onSubmit={(event) => {OnSubmit(event)}}>
            <label for="title">Job Title</label>
            <input type="text" id="title" name="title" required/>

            <label for="location">Job Location</label>
            <Autocomplete/>

            <label>
                <input type="checkbox" name="remote"/> Remote Job?
            </label>

            <label for="pay">Pay Offered (USD)</label>
            <input type="text" id="pay" name="pay" required/>

            <label for="description">Job Description</label>
            <textarea id="description" name="description" rows="4" required></textarea>

            <label for="requirements">Job Requirements</label>
            <textarea id="requirements" name="requirements" rows="4" required></textarea>

            <label>
                <input type="checkbox" name="visa_sponsorship"/> Visa Sponsorship Available?
            </label>

            <label for="url">Link to application page</label>
            <input type="text" id="url" name="url" required/>

            <button type="submit">{loadWait ? <div className='spinner'/> : "Post Job"}</button>
        </form>
    </div>);
}

export {PostJob}