import React, { createContext, useContext, useState } from 'react';

const ThemeContext = createContext();

const ThemeProvider = ({children}) => {
    const [theme, setTheme] = useState({
        logo: '/static/rezify_logo2.png',
        primary_color: '#DB3A00',
        hover_color: '#ff4500'
    });

    return (
        <ThemeContext.Provider value={{theme, setTheme}}>
        {children}
        </ThemeContext.Provider>
    );
};

const useTheme = () => useContext(ThemeContext)

const updateColors = (parsedData, setTheme) => {
    /*
    Takes in parsed json color data, either from localStorage or an API fetch, and updates colors and returns the logo in use
    */
   if (parsedData) {
        document.documentElement.style.setProperty('--primary-color', parsedData.primary_color);
        document.documentElement.style.setProperty('--logo', "/static/" + parsedData.logo);
        document.documentElement.style.setProperty('--hover-color', parsedData.hover_color);
        document.documentElement.style.setProperty('--text-against-pc', parsedData.text_against_pc);
        setTheme(prev => ({
            ...prev,
            logo: "/static/" + parsedData.logo,
            primary_color: parsedData.primary_color,
            hover_color: parsedData.hover_color
        }));
   }
}
  
export {ThemeProvider, useTheme, updateColors};