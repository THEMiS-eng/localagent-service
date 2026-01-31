import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Dashboard from './Dashboard';
import Settings from './Settings';
import Navigation from './Navigation';

const App = () => {
  return React.createElement(
    'div',
    { className: 'app' },
    React.createElement(
      Router,
      null,
      React.createElement(Navigation),
      React.createElement(
        'main',
        { className: 'main-content' },
        React.createElement(
          Routes,
          null,
          React.createElement(Route, { path: '/', element: React.createElement(Dashboard) }),
          React.createElement(Route, { path: '/settings', element: React.createElement(Settings) })
        )
      )
    )
  );
};

export default App;