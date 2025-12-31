import { Index } from './objects/Index';
import { useEffect, useState } from 'react';
import { BrowserRouter, Routes, Route, useLocation } from 'react-router-dom';

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

  const location = useLocation();

  return (
    <>
        <Routes>
          <Route path="/" element={<Index/>} />
        </Routes>      
    </>
  );
}


export default App;
