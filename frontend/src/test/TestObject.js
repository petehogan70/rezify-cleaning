import React from 'react';

export const TestObject = ({prop}) => {
    return (<h1>{(prop && prop.message) ? prop.message : "null"}</h1>);
};