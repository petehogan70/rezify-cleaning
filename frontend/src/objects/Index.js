import { IndexBody } from './IndexBody';
import { IndexFooter } from './IndexFooter';
import '../styles/NewIndexPage.css';
import { useState, useEffect } from 'react';
import { useSearchParams, useParams, useNavigate } from 'react-router-dom';
import { updateColors, useTheme } from '../hooks/ThemeContext';


function Index({firstTimer = false}) {
    const [currUser, setCurrentUser] = useState({});
    const [currErrMsg, setCurrErrMsg] = useState("");
    const [isLoaded, setIsLoaded] = useState(false); //backend response complete or not
    const {setTheme} = useTheme();
    const [searchParams] = useSearchParams();
    
    const navigate = useNavigate();

    useEffect(() => {
        fetch(`/api`).then(async response => {
          //get flask backend response
          if (response.ok) {
            const data = await response.json();
            if (data.colors) {
                localStorage.setItem('theme-colors', JSON.stringify(data.colors));
                updateColors(data.colors, setTheme)
            }
            
            if (data.should_redirect  && searchParams.get("noredir") !== "1") {
              navigate("/results");
            }

            if (data.redirect_admin) {
                navigate("/admin");
            }

            //get user if exists
            if (data.user) {
                //const userJson = await data.user.json();
                setCurrentUser(data.user);
            } else {
                setCurrentUser({
                    'na': true
                })
            }

            if (data.error_message) {
                setCurrErrMsg(data.error_message)
            }
            setIsLoaded(true);
          } else {
            setCurrentUser({'error': true})
            setCurrErrMsg("Error: " + response.statusText)
            //error, prob shouldnt log in
            setIsLoaded(true);
          }
        })
      }, []);
    return (<>
        {(firstTimer && !isLoaded) ?
        <div style={{display: 'flex', justifyContent: 'center', alignItems: 'center',  height: '100vh', width: '100vw'}}>
          <div className='spinner'></div>
        </div>
        :
        <>
          <IndexBody user={currUser} errormessage={currErrMsg}/>
          <IndexFooter/>
        </>}
        </>);
}

export {Index};