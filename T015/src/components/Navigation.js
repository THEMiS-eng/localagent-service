import React from 'react';
import { Link, useLocation } from 'react-router-dom';

const Navigation = () => {
  const location = useLocation();
  
  return React.createElement(
    'nav',
    { className: 'navigation' },
    React.createElement(
      'div',
      { className: 'nav-brand' },
      React.createElement('h1', null, 'THEMiS UI')
    ),
    React.createElement(
      'ul',
      { className: 'nav-links' },
      React.createElement(
        'li',
        null,
        React.createElement(
          Link,
          {
            to: '/',
            className: location.pathname === '/' ? 'active' : ''
          },
          'Dashboard'
        )
      ),
      React.createElement(
        'li',
        null,
        React.createElement(
          Link,
          {
            to: '/settings',
            className: location.pathname === '/settings' ? 'active' : ''
          },
          'Settings'
        )
      )
    )
  );
};

export default Navigation;