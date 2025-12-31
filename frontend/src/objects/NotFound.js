import React from 'react';
import { IndexHeader } from './IndexHeader';
import '../styles/NewIndexPage.css';
import { useNavigate } from 'react-router-dom';
import { IndexFooter } from './IndexFooter';
import { BasicFooter } from './BasicFooter';


export const NotFound = () => {
    const navigate = useNavigate();

    return (<><div style={{justifyContent: 'center', alignItems: 'center', display: 'flex', flexDirection: 'column'}}>
        <div className="slogan" style={{textAlign:'center', fontSize: '64px'}}>404: <span style={{color: 'var(--primary-ab)'}}>Page not found...</span></div>
        <img src='/static/rezify_logo.png' style={{width: '320px', display: 'flex'}}/>
        <button className='login-button' style={{cursor: 'pointer'}} onClick={() => {
            navigate('/');
        }}>Home</button>
        </div>
        <BasicFooter/>
        </>
    );
};