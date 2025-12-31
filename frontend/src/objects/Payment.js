import React, { useCallback, useState, useEffect } from "react";
import {loadStripe} from '@stripe/stripe-js';
import {
  EmbeddedCheckoutProvider,
  EmbeddedCheckout
} from '@stripe/react-stripe-js';
import {
  BrowserRouter as Router,
  Route,
  Routes,
  Navigate,
  useNavigate,
  useSearchParams
} from "react-router-dom";

import '../styles/PaymentPage.css'
import { updateColors, useTheme } from "../hooks/ThemeContext";
import { IndexHeader } from "./IndexHeader";
import { BasicFooter } from "./BasicFooter";


const stripePromise = loadStripe("pk_live_51RWiNcBOoKsKuzAu50fYIUXYzYNcqGs5fgAJHN52GyrqcWqqsgpu1tSzRC5iqGMCMfEyJwj09GKKUFOFrrSXTFQR00N2yDLCkq");

const CheckoutForm = () => {
  const fetchClientSecret = useCallback(() => {
    return fetch("/api/payment", {
      method: "POST",
    })
      .then((res) => res.json())
      .then((data) => data.client_secret);
  }, []);

  const options = {fetchClientSecret};

  return (
    <div id="checkout">
      <EmbeddedCheckoutProvider
        stripe={stripePromise}
        options={options}
      >
        <EmbeddedCheckout />
      </EmbeddedCheckoutProvider>
    </div>
  )
}

function Payment() {
    const [currUser, setCurrentUser] = useState({});
    const [isIndexLoaded, setIsIndexLoaded] = useState(false); //backend response for index header complete or not
    const {setTheme} = useTheme();
    const [searchParams, setSearchParams] = useSearchParams();
    const [returnScreen, setReturnScreen] = useState(false);
    const [returnID, setReturnID] = useState("");
    const [status, setStatus] = useState(null);
    const [customerEmail, setCustomerEmail] = useState('');
    const [returnWait, setReturnWait] = useState(false);

    const navigate = useNavigate();

    const userRefresh = (redironupgrade = false) => {
      setIsIndexLoaded(false);
      fetch(`/api/index`).then(async response => {
          //get flask backend response
          if (response.ok) {
            const data = await response.json();
            if (data.colors) {
                localStorage.setItem('theme-colors', JSON.stringify(data.colors));
                updateColors(data.colors, setTheme);
            }
            //get user if exists
            if (data.user) {
                //const userJson = await data.user.json();
                setCurrentUser(data.user);
                if (redironupgrade) {
                  if (data.user.plan === "premium") {
                    if (data.user.resume_file) {
                      navigate("/results")
                    } else {
                      navigate("/index")
                    }
                    
                  }
                }
            } else {
                setCurrentUser({
                    'na': true
                })
                navigate("/login")
            }

            if (data.error_message) {
                //doesn't really matter in this scenerio
            }
            setIsIndexLoaded(true);
          } else {
            setCurrentUser({'error': true})
            //error, prob shouldnt log in
            setIsIndexLoaded(true);
          }
        });
    }

    useEffect(() => {
      setIsIndexLoaded(false);
        const new_return_id = searchParams.get("return_id");
        if (new_return_id) {
            setReturnScreen(true);
            setReturnID(new_return_id);
            setReturnWait(false);
            fetch(`/api/payment?return_id=${new_return_id}`)
            .then((res) => res.json())
            .then((data) => {
                if (data.status === "open") {
                    navigate("payment")
                } else if (data.status === "DNE") {
                  //session doesn't exist, user is probably trying to do something funny
                  searchParams.delete('return_id');
                  setSearchParams(searchParams);
                  return;
                }
                setStatus(data.status);
                setCustomerEmail(data.customer_email);
                setReturnWait(true);
                userRefresh(data.status === "complete");
            });
        } else {
          setReturnScreen(false);
          setReturnID("");
          userRefresh();
        }
        
      }, [searchParams]);
      
    return <>
    <header>
        <div class="top-header" id="top-header">
            <IndexHeader user={currUser} firstWait={isIndexLoaded}/>
        </div>
    </header>
    {returnScreen ?
    (returnWait && isIndexLoaded ?
    (status === 'open' ?
    /*User should not be here, should be renavigated*/
    <p>...</p>
    :
    (status === 'complete' ?    
    <section style={{textAlign: 'center', justifyContent: 'center', display: 'flex', flexDirection: 'column'}} id="success">
      {currUser.plan === "premium" ?
      <>
        <p>
          Success! You are now a premium user.
          </p>
        <p>
          If you have any questions, please email us!
        </p>
      </>
      :
        <>
        <p>
          We are currently processing your payment! A confirmation email will be sent to <span style={{color: 'var(--primary-aw)'}}>{customerEmail}</span>
          </p>
        <p>
          If you have any questions, please email us! Refresh the page to recheck your status.
        </p>
        </>
      }
      </section>
    :
    <p>Unknown Status: {status}</p>
    )
    )
    :
    <div className="spinner" style={{margin:'auto'}}></div>
    )
    :
    <CheckoutForm/>}
    <BasicFooter/>
    </>;
}

export {Payment}