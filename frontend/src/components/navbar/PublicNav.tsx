import React, { useState } from 'react';
import { Menu, X } from 'lucide-react';
import { Link, NavLink } from 'react-router-dom';
import { BrandLogo } from './BrandLogo';

// The login page opens the matching tab from ?mode=.
const SIGN_IN_PATH = '/login?mode=login';
const SIGN_UP_PATH = '/login?mode=register';

export const PublicNav: React.FC = () => {
  const [open, setOpen] = useState(false);

  return (
    <header className="public-nav">
      <div className="nav-inner">
        <BrandLogo size="xl" shine />
        <button
          className="icon-button mobile-menu-toggle"
          aria-label={open ? 'Close navigation' : 'Open navigation'}
          onClick={() => setOpen(!open)}
        >
          {open ? <X size={19} /> : <Menu size={19} />}
        </button>
        <nav className={`nav-links ${open ? 'nav-links-open' : ''}`} aria-label="Main navigation">
          <NavLink to="/features" onClick={() => setOpen(false)}>Features</NavLink>
          <NavLink to="/how-it-works" onClick={() => setOpen(false)}>How it works</NavLink>
          <NavLink to="/organisation" onClick={() => setOpen(false)}>Organisation</NavLink>
          <a href="/#about" onClick={() => setOpen(false)}>About</a>
          <a href="/#faq" onClick={() => setOpen(false)}>FAQ</a>
          <div className="mobile-nav-actions">
            <Link className="nav-signin" to={SIGN_IN_PATH} onClick={() => setOpen(false)}>Sign in</Link>
            <Link className="button button-brand button-small" to={SIGN_UP_PATH} onClick={() => setOpen(false)}>
              Sign up
            </Link>
          </div>
        </nav>
        <div className="nav-actions">
          <Link className="nav-signin" to={SIGN_IN_PATH}>Sign in</Link>
          <Link className="button button-brand button-small" to={SIGN_UP_PATH}>
            Sign up
          </Link>
        </div>
      </div>
    </header>
  );
};
