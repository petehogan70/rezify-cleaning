import React, { use, useEffect, useState } from 'react';

function Autocomplete({ref = null, //for ref={} jsx object
                      setLocation = (newloc)=>{}, //if location is set, this function will be a callback
                      overrideValue="" //if backend has a preset location (i.e user already has location picked)
                    }) 
    {
    const [input, setInput] = useState(''); //the actual value in the input box
    const [filteredSuggestions, setFilteredSuggestions] = useState([]);
    const [allSuggest, setAllSuggest] = useState([]);

    useEffect(()=>{
        setInput(overrideValue);
        //In case backend finds there's a user value set already
    }, [overrideValue]);

    useEffect(()=>{
        //load the uscities file
        fetch('/static/uscities.csv').then(result => {
            if (result.ok) {
                result.text().then(data => {
                    var rows = data.split('\n');
                    rows.forEach(function(row, index) {
                        // Skip the first row (index 0) if it contains column names
                        if (index === 0) return;

                        var columns = row.split(',');
                        if (columns.length >= 3) { // Ensure the row has sufficient columns
                            var cityState = columns[1].trim() + ', ' + columns[2].trim();
                            setAllSuggest(prev => prev.includes(cityState) ? prev : [...prev, cityState]);
                        }
                    });
                })
            }
        })
    }, []);

    return (
        <>
          <input value={input} onKeyDown= {(event)=>{
            if (event.key === 'Enter') {
                setInput(filteredSuggestions.length >= 1 ? filteredSuggestions[0] : '');
                setLocation(filteredSuggestions.length >= 1 ? filteredSuggestions[0] : '')
                setFilteredSuggestions([]);
            }
          }}
          onChange={(event) => {
            setInput(event.target.value)
            if (event.target.value.length > 0) {
                setFilteredSuggestions(allSuggest.filter(val => val.toLowerCase().includes(event.target.value.toLowerCase()))
                );
                //filter just by included values
              } else {
                setFilteredSuggestions([]);
              }
          }} type="text" id="location" name="location" placeholder="(ex: St. Louis, MO)" ref={ref} />
          <ul style={{ listStyle: 'none', padding: 0, marginTop: 0 }}>
            {filteredSuggestions.map((item, i) => ( i < 3 ?
              <li key={i} onClick={() => {
                setInput(item);
                setLocation(item);
                setFilteredSuggestions([]);
              }} style={{ cursor: 'pointer' }}>
                <div style={{'padding': '10px', 'marginTop': '0px', 'border-radius': '5px', 'border': '1px solid var(--primary-color)', 'font-size': '16px', 'color': 'var(--primary-color)'}}>
                {
                //highlight each matching part
                item.split(new RegExp(input, "gi")).map((sub, ife) => {
                    return <>
                        <span style={{ backgroundColor: 'var(--primary-aw)', color: 'white' }}>{ife >= 1 ? input : ""}</span>
                        {sub}
                        </>
                })}
                </div>
              </li> : <></>
            ))}
          </ul>
        </>
      );
}

export {Autocomplete}