import React, { useEffect } from 'react';
import { motion } from 'framer-motion';
import { ArrowRight, ArrowUpRight, Heart, KeyRound, LogIn, MessageCircle, ShieldCheck, Sparkles } from 'lucide-react';
import { Link, useLocation } from 'react-router-dom';
import { Footer } from '../../components/footer/Footer';
import { PublicNav } from '../../components/navbar/PublicNav';
import { PageMeta } from '../../components/ui/PageMeta';
import { OrgRequestForm } from '../../components/organisation/OrgRequestForm';
import { WorkspacePreview } from '../../components/organisation/WorkspacePreview';
import {
  AGENTIC_DESCRIPTION,
  AGENTIC_HIGHLIGHTS,
  AGENTIC_ICON as AgenticIcon,
  AGENTIC_SECURITY_STATEMENT,
  HUB_TOPICS,
  PORTAL_CAPABILITIES,
  PORTAL_HEADING,
  PORTAL_STEPS,
  PORTAL_SUBCOPY,
} from '../../components/organisation/portalContent';
import { ORG_ACTIVATE_PATH, ORG_LOGIN_PATH } from '../../layouts/accountRouting';
import '../../components/organisation/organisation.css';

export const OrganisationPortalPage: React.FC = () => {
  // Router links do not scroll to a #fragment (e.g. the nav's "Request access" to #request); do it here.
  const { hash } = useLocation();
  useEffect(() => {
    if (!hash) return;
    const reduceMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    document.getElementById(hash.slice(1))?.scrollIntoView({ behavior: reduceMotion ? 'auto' : 'smooth', block: 'start' });
  }, [hash]);

  return (
    <>
      <PageMeta
        title="Organisation Portal"
        description="Create your organisation workspace, add your team and share verified SAP BRIM answers in a shared knowledge hub."
      />
      <PublicNav />
      <main className="org-portal">
        {/* Hero */}
        <section className="org-hero section-wrap">
          <motion.div
            className="org-hero-copy"
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.55 }}
          >
            <div className="hero-kicker">
              <span className="org-kicker-dot" aria-hidden="true" />
              <strong>ORGANISATION</strong> PORTAL
            </div>
            <h1>{PORTAL_HEADING}</h1>
            <p className="org-hero-sub">{PORTAL_SUBCOPY}</p>
            <div className="org-hero-actions">
              <Link className="button button-brand" to={ORG_LOGIN_PATH}>
                <LogIn size={16} aria-hidden="true" /> Sign in to your organisation
              </Link>
              <Link className="button org-button-outline" to={ORG_ACTIVATE_PATH}>
                <KeyRound size={16} aria-hidden="true" /> Activate with a code
              </Link>
            </div>
            <a className="text-link org-hero-request" href="#request">
              New here? Request an organisation account <ArrowRight size={16} aria-hidden="true" />
            </a>
            <div className="hero-trust">
              <span className="trust-line" />
              <strong>Approved by Clyptus</strong> · <strong>Individual member credentials</strong> ·{' '}
              <strong>Private chats by default</strong>
            </div>
          </motion.div>
          <motion.div
            className="org-hero-visual"
            initial={{ opacity: 0, y: 22 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.14 }}
          >
            <WorkspacePreview />
          </motion.div>
        </section>

        {/* Capabilities */}
        <section className="section section-wrap org-capabilities-section" aria-labelledby="org-capabilities-title">
          <div className="features-heading">
            <div>
              <span className="eyebrow">ONE WORKSPACE FOR YOUR TEAM</span>
              <h2 id="org-capabilities-title">
                With the Organisation Portal,
                <br />
                <span>you can:</span>
              </h2>
            </div>
            <p className="org-heading-note">
              Every member keeps <strong>private chats</strong>. Only the answers your team{' '}
              <strong>chooses to share</strong> reach the organisation.
            </p>
          </div>
          <ul className="org-capability-grid">
            {PORTAL_CAPABILITIES.map(({ text, icon: Icon }, index) => (
              <li className="org-capability" key={text}>
                <span className="feature-icon" aria-hidden="true">
                  <Icon size={18} strokeWidth={1.8} />
                </span>
                <span className="org-capability-index">{String(index + 1).padStart(2, '0')}</span>
                <p>{text}</p>
              </li>
            ))}
          </ul>
        </section>

        {/* How it works */}
        <section className="workflow-section" aria-labelledby="org-flow-title">
          <div className="section section-wrap">
            <div className="workflow-heading">
              <div>
                <span className="eyebrow">HOW IT WORKS</span>
                <h2 id="org-flow-title">
                  From request
                  <br />
                  <span>to a shared knowledge hub.</span>
                </h2>
              </div>
              <p>
                Organisations are created only by a <strong>Clyptus Super Admin</strong>. Your administrator activates
                the workspace with a <strong>single-use, time-limited code</strong>.
              </p>
            </div>
            <ol className="workflow-track workflow-track-six org-flow">
              {PORTAL_STEPS.map(({ title, text, icon: Icon }, index) => (
                <li className="workflow-step" key={title}>
                  <div className="workflow-node">
                    <Icon size={18} aria-hidden="true" />
                  </div>
                  <span className="step-number">{String(index + 1).padStart(2, '0')}</span>
                  <h3>{title}</h3>
                  <p>{text}</p>
                  {index < PORTAL_STEPS.length - 1 && <span className="workflow-connector" aria-hidden="true" />}
                </li>
              ))}
            </ol>
          </div>
        </section>

        {/* Shared Knowledge Hub preview */}
        <section className="section section-wrap org-hub-section" aria-labelledby="org-hub-title">
          <div className="org-hub-copy">
            <span className="eyebrow">SHARED KNOWLEDGE HUB</span>
            <h2 id="org-hub-title">
              Your team's best answers,
              <br />
              <span>organised by SAP BRIM topic.</span>
            </h2>
            <p>
              When an answer helps, like it and <strong>share it to your organisation</strong>. It is filed under the
              right topic automatically, and the person who shared it or an admin can move it.
            </p>
            <p>
              Members can <strong>like</strong>, <strong>comment</strong> and see <strong>who engaged</strong> with each
              answer, so proven solutions are easy to find next time.
            </p>
          </div>
          <div className="org-hub-board">
            <div className="org-hub-board-head">
              <span>Topics</span>
              <span className="org-hub-board-note">Classified automatically</span>
            </div>
            <ul className="org-topic-list">
              {HUB_TOPICS.map(({ abbreviation, label, icon: Icon }) => (
                <li key={label}>
                  <span className="org-topic-icon" aria-hidden="true">
                    <Icon size={15} strokeWidth={1.9} />
                  </span>
                  <span className="org-topic-label">{label}</span>
                  <span className="org-topic-abbr">{abbreviation}</span>
                </li>
              ))}
            </ul>
            <div className="org-hub-sample">
              <span className="org-pill">Troubleshooting</span>
              <p>Billing document not generated for a contract account: what to check first?</p>
              <div className="org-hub-sample-meta">
                <span>
                  <Heart size={13} aria-hidden="true" /> Liked by Priya, Daniel and 2 others
                </span>
                <span>
                  <MessageCircle size={13} aria-hidden="true" /> 3 comments
                </span>
              </div>
            </div>
          </div>
        </section>

        {/* Coming soon: Secure Agentic AI Chatbot */}
        <section className="org-agentic-section" aria-labelledby="org-agentic-title">
          <div className="section section-wrap">
            <div className="org-agentic-card">
              <div className="org-agentic-head">
                <span className="org-agentic-icon" aria-hidden="true">
                  <AgenticIcon size={24} strokeWidth={1.8} />
                </span>
                <span className="org-soon-badge">
                  <Sparkles size={12} aria-hidden="true" /> Coming soon
                </span>
              </div>
              <span className="eyebrow">COMING SOON</span>
              <h2 id="org-agentic-title">
                Secure Agentic AI Chatbot
                <br />
                <span>that works within your permissions.</span>
              </h2>
              <p className="org-agentic-lead">{AGENTIC_DESCRIPTION}</p>
              <ul className="org-agentic-grid">
                {AGENTIC_HIGHLIGHTS.map(({ text, icon: Icon }) => (
                  <li key={text}>
                    <span aria-hidden="true">
                      <Icon size={16} strokeWidth={1.9} />
                    </span>
                    {text}
                  </li>
                ))}
              </ul>
              <div className="org-security-note">
                <ShieldCheck size={20} aria-hidden="true" />
                <div>
                  <strong>Security by design</strong>
                  <p>{AGENTIC_SECURITY_STATEMENT}</p>
                </div>
              </div>
              <p className="org-agentic-foot">In development. Not yet available in your workspace.</p>
            </div>
          </div>
        </section>

        {/* Entry points and request form */}
        <section className="section section-wrap org-start-section" id="request" aria-labelledby="org-start-title">
          <div className="org-start-intro">
            <span className="eyebrow">GET STARTED</span>
            <h2 id="org-start-title">
              Three ways in.
              <br />
              <span>Pick the one that fits.</span>
            </h2>
          </div>
          <div className="org-start-grid">
            <div className="org-entry-stack">
              <Link className="org-entry-card" to={ORG_LOGIN_PATH}>
                <span className="org-entry-icon" aria-hidden="true">
                  <LogIn size={19} />
                </span>
                <span className="org-entry-text">
                  <strong>Sign in to your organisation</strong>
                  <span>Members and administrators with organisation credentials.</span>
                </span>
                <ArrowUpRight size={17} aria-hidden="true" />
              </Link>
              <Link className="org-entry-card" to={ORG_ACTIVATE_PATH}>
                <span className="org-entry-icon" aria-hidden="true">
                  <KeyRound size={19} />
                </span>
                <span className="org-entry-text">
                  <strong>Activate with an activation code</strong>
                  <span>For the administrator who received a code from Clyptus.</span>
                </span>
                <ArrowUpRight size={17} aria-hidden="true" />
              </Link>
              <p className="org-entry-note">
                Using Clyptus.AI on your own? <Link to="/login">Sign in with an individual account</Link>.
              </p>
            </div>
            <div className="org-request-card">
              <h3>Request an organisation account</h3>
              <p>Tell us who you are. We will review the request and send an activation code when it is approved.</p>
              <OrgRequestForm />
            </div>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
};
