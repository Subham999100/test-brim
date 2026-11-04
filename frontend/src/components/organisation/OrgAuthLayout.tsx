import React from 'react';
import { ArrowLeft, Building2, Check } from 'lucide-react';
import { Link } from 'react-router-dom';
import { BrandLogo } from '../navbar/BrandLogo';
import { OrgVisual } from './OrgVisual';
import './organisation.css';

const ORG_AUTH_POINTS = [
  'A shared Knowledge Hub organised by SAP BRIM topic',
  'Every member has their own sign-in, managed by your admin',
  'Only the answers your team chooses to share are visible',
];

/**
 * The organisation sign-in family (sign in, activate, change password). Same split as /login, but with
 * its own identity: the team-and-hub artwork, the workspace promise and what membership means, so an
 * organisation member can tell at a glance they are not on the individual sign-in.
 */
export function OrgAuthLayout({
  children,
  backTo,
  backLabel,
  quote = '“Your team’s SAP BRIM knowledge: shared, searchable and private by default.”',
  caption = 'Organisation workspace · Approved by Clyptus',
  points = ORG_AUTH_POINTS,
}: {
  children: React.ReactNode;
  /** Optional way back, for a signed-in member who opened a page voluntarily. Sign-in pages have none. */
  backTo?: string;
  backLabel?: string;
  quote?: string;
  caption?: string;
  points?: string[];
}) {
  return (
    <main className="auth-split auth-split-org">
      <aside className="auth-visual">
        <BrandLogo size="xl" shine />
        <OrgVisual className="auth-visual-art" />
        <div className="auth-pitch">
          <figure className="auth-quote">
            <span className="auth-quote-icon" aria-hidden="true">
              <Building2 size={22} strokeWidth={2} />
            </span>
            <blockquote>{quote}</blockquote>
            <figcaption>{caption}</figcaption>
          </figure>
          {points.length > 0 && (
            <ul className="auth-points">
              {points.map((point) => (
                <li key={point}>
                  <Check size={14} strokeWidth={2.5} aria-hidden="true" />
                  <span>{point}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </aside>

      <section className="auth-form-side">
        <div className="auth-form-scroll">
          <div className="auth-mobile-brand">
            <BrandLogo />
          </div>
          {backTo && (
            <Link to={backTo} className="login-back">
              <ArrowLeft size={15} /> {backLabel}
            </Link>
          )}
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
