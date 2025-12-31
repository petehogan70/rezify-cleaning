import { NotFound } from './objects/NotFound';
import { Index } from './objects/Index';
import { Login } from './objects/Login';
import { useEffect, useState } from 'react';
import { BrowserRouter, Routes, Route, useLocation } from 'react-router-dom';
import './styles/NewIndexPage.css'
import { Register } from './objects/Register';
import { Results } from './objects/Results';
import { Recover } from './objects/Recover';
import { PostJob } from './objects/PostJob';
import { GetDemo } from './objects/GetDemo';
import {Feedback} from './objects/Feedback';
import {Help} from './objects/Help';
import './styles/DefaultPage.css'
import { updateColors, useTheme } from './hooks/ThemeContext';
import { Plans } from './objects/Plans';
import { Payment } from './objects/Payment';
import { Profile } from './objects/Profile';
import { AdminDashboard } from './objects/AdminDashboard';

function App() {
  return (
    <>
      <BrowserRouter>
        <AppDetails/>
      </BrowserRouter>
      
    </>
  );
}

function AppDetails() {
  const {setTheme} = useTheme();
  const [firstTimer, setFirstTimer] = useState(true); //indicates no theme decided, don't render colors yet...
  useEffect(() => {
      const savedThemeData = localStorage.getItem('theme-colors'); //check if website has theme saved already
      if (savedThemeData) { //if theme exists, apply those colors
        const savedColors = JSON.parse(savedThemeData)
        updateColors(savedColors, setTheme);
        setFirstTimer(false); //user has data already
      }
  }, [])

  const location = useLocation();
  useEffect(() => {
    document.body.className = ''; //clear class css specification
    if (location.pathname === '/') {
      document.body.classList.add('index');
    } else if (location.pathname === '/login') {
      document.body.classList.add('login');
    } else if (location.pathname === '/register' || location.pathname === '/verify_email' || location.pathname === '/recover' || location.pathname === '/change_password') {
      document.body.classList.add('register');
    } else if (location.pathname === '/results') {
      document.body.classList.add('results');
    } else if (location.pathname === '/post_job') {
      document.body.classList.add('postjob');
    } else if (location.pathname === '/get_demo') {
      document.body.classList.add('getdemo');
    } else if (location.pathname === '/plans') {
      document.body.classList.add('plans');
    } else if (location.pathname === '/payment') {
      document.body.classList.add('payment');
    } else if (location.pathname === '/profile') {
      document.body.classList.add('profile');
    } else if (location.pathname === '/admin') {
      document.body.classList.add('admin');
      } else if (location.pathname === '/feedback') {
      document.body.classList.add('feedback');
    } else if (location.pathname === '/help') {
      document.body.classList.add('help');
    } else {
      document.body.classList.add('index'); //not found page
    }
  }, [location]);

  return (
    <>
        <Routes>
          <Route path="/" element={<Index firstTimer={firstTimer}/>} />
          <Route path="/index" element={<Index  firstTimer={firstTimer}/>} />
          <Route path="/login" element={<Login/>} />
          <Route path="/register" element={<Register/>} />
          <Route path="/verify_email" element={<Register verify={true}/>} />
          <Route path="/results" element={<Results/>} />
          <Route path="/recover" element={<Recover recover={true}/>} />
          <Route path="/change_password" element={<Recover recover={false}/>} />
          <Route path="/post_job" element={<PostJob/>} />
          <Route path="/get_demo" element={<GetDemo/>} />
          <Route path="/:school" element={<Index firstTimer={firstTimer}/>} />
          <Route path="/plans" element={<Plans/>}/>
          <Route path="/payment" element={<Payment/>}/>
          <Route path="/profile" element={<Profile/>}/>
          <Route path="/admin" element={<AdminDashboard/>} />
          <Route path="/feedback" element={<Feedback />} />
          <Route path="/help" element={<Help />} />
          <Route path="*" element={<NotFound/>} />

        </Routes>      
    </>
  );
}


export default App;
