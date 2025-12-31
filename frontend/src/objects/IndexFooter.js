import React from 'react';


export const IndexFooter = ({ prop }) => {
    return (
        <>
            <footer id="index-footer">

                <p style={{ fontWeight: 'bold', fontSize: '1.1rem' }}>Contact us:</p>
                <p>Sales Email: <a href="mailto:sales@rezify.ai" style={{ color: 'var(--text-color)' }}>sales@rezify.ai</a></p>
                <p>Support: <a href="mailto:support@rezify.ai" style={{ color: 'var(--text-color)' }}>support@rezify.ai</a></p>

                <p>2025 Rezify &reg;. All rights reserved.</p>
            </footer>
        </>
    );
};
