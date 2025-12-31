import { useState } from 'react';
// Styled by "../styles/TourButton.css";

function TourButton({ driver }) {
    const [showPopup, setShowPopup] = useState(false);

    return (<>
        <div class="tour-button-outer"
            onMouseLeave={() => setShowPopup(false)}
        >
            {showPopup ? 
                <div class="tour-button-popup-outer">
                    <button class="tour-button-popup-inner" onClick={() => driver.drive()}>
                        View Tour
                    </button>
                </div>
                : <></>
            }
            <button
                class="tour-button"
                onClick={() => driver.drive()}
                onMouseOver={() => setShowPopup(true)}
            >
                ?
            </button>
        </div>
    </>)
}

export {TourButton}