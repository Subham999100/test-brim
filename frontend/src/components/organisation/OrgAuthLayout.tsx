import React from 'react';
import { ArrowLeft, Building2 } from 'lucide-react';
import { Link } from 'react-router-dom';
import { BrandLogo } from '../navbar/BrandLogo';
import { LoginVisual } from '../auth/LoginVisual';
import './organisation.css';

/**
 * The /login layout family for organisation pages: brand visual and shield quotation on the left,
 * the form on the right, locked to the viewport on desktop (see the .auth-* rules in index.css).
 */
export function OrgAuthLayout({
  children,
  backTo = '/organisation',
  backLabel = 'Back to Organisation Portal',
  quote = '“Every member signs in with their own credentials, and only the answers your team chooses to share reach your organisation.”',
  caption = 'Organisation workspace · Private by default',
}: {
  children: React.ReactNode;
  backTo?: string;
  backLabel?: string;
  quote?: string;
  caption?: string;
}) {
  return (
    <main className="auth-split">
      <aside className="auth-visual">
        <BrandLogo size="xl" shine />
        <LoginVisual className="auth-visual-art" />
        <figure className="auth-quote">
          <span className="auth-quote-icon" aria-hidden="true">
            <Building2 size={22} strokeWidth={2} />
          </span>
          <blockquote>{quote}</blockquote>
          <figcaption>{caption}</figcaption>
        </figure>
      </aside>

      <section className="auth-form-side">
        <div className="auth-form-scroll">
          <div className="auth-mobile-brand">
            <BrandLogo />
          </div>
          <Link to={backTo} className="login-back">
            <ArrowLeft size={15} /> {backLabel}
          </Link>
          <div className="login-card">{children}</div>
          <div className="login-legal">
            <span>Organisation workspaces are approved by Clyptus.</span>
            <Link to="/organisation">About the Organisation Portal</Link>
          </div>
        </div>
      </section>
    </main>
  );
}
