import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import { OrganisationPortalPage } from './OrganisationPortalPage';
import { AGENTIC_HIGHLIGHTS, HUB_TOPICS, PORTAL_CAPABILITIES, PORTAL_STEPS } from '../../components/organisation/portalContent';

const html = renderToStaticMarkup(
  <MemoryRouter initialEntries={['/organisation']}>
    <OrganisationPortalPage />
  </MemoryRouter>,
);
// Rendered text with tags removed and entities decoded, for copy checks.
const text = html
  .replace(/<[^>]+>/g, ' ')
  .replace(/&#x27;|&#39;/g, "'")
  .replace(/&amp;/g, '&')
  .replace(/&quot;/g, '"')
  .replace(/\s+/g, ' ');

const hrefs = [...html.matchAll(/<a[^>]*href="([^"]*)"/g)].map(([, href]) => href);

describe('OrganisationPortalPage', () => {
  it('shows the product-owner heading and sub-copy', () => {
    expect(html).toMatch(/<h1>Welcome to Your Organisation Workspace<\/h1>/);
    expect(text).toContain(
      'Create your organisation, invite your team members, and collaborate in a shared AI-powered knowledge environment.',
    );
  });

  it('lists every Organisation Portal capability', () => {
    expect(text).toContain('With the Organisation Portal, you can:');
    expect(PORTAL_CAPABILITIES).toHaveLength(8);
    for (const capability of [
      'Create and manage your organisation',
      'Add and manage organisation members',
      'Provide individual login credentials to each member',
      'Allow team members to interact with the AI chatbot',
      'Share useful AI-generated answers with your organisation',
      'Organise saved answers into topic-based categories',
      'Comment on saved answers and participate in discussions',
      'View which organisation members liked, saved, or commented on each answer',
    ]) {
      expect(text).toContain(capability);
    }
  });

  it('explains the flow from request to the knowledge hub in order', () => {
    const titles = PORTAL_STEPS.map((s) => s.title);
    expect(titles).toEqual([
      'Request',
      'Super Admin approval',
      'Activation code',
      'Set up admin account',
      'Add members',
      'Collaborate in the Knowledge Hub',
    ]);
    const positions = titles.map((t) => html.indexOf(`<h3>${t}</h3>`));
    expect(positions.every((p) => p > -1)).toBe(true);
    expect([...positions].sort((a, b) => a - b)).toEqual(positions);
  });

  it('previews the knowledge hub topics', () => {
    for (const label of [
      'Convergent Charging',
      'Convergent Invoicing',
      'Subscription Order Management',
      'SAP BRIM Integration',
      'Troubleshooting',
      'Architecture and Configuration',
    ]) {
      expect(text).toContain(label);
    }
    expect(HUB_TOPICS.map((t) => t.abbreviation)).toEqual(expect.arrayContaining(['CC', 'CI', 'SOM', 'FI-CA']));
  });

  it('badges the Secure Agentic AI Chatbot as coming soon, with its highlights and security statement', () => {
    expect(html).toMatch(/class="org-soon-badge"[^>]*>.*?Coming soon<\/span>/);
    expect(text).toContain('Secure Agentic AI Chatbot');
    expect(text).toContain(
      "We are developing an advanced Agentic AI chatbot that can securely interact with your organisation's authorised portal and perform tasks based on your permissions.",
    );
    expect(AGENTIC_HIGHLIGHTS.map((h) => h.text)).toEqual([
      'Secure portal integration',
      'Permission-based access',
      'Automated workflows through AI agents',
      'Secure handling of organisation data',
      'Authentication and authorisation controls',
      'No direct visibility of login credentials to developers',
    ]);
    for (const { text: highlight } of AGENTIC_HIGHLIGHTS) expect(text).toContain(highlight);
    expect(text).toMatch(/encrypted or securely tokenised/);
    expect(text).toMatch(/least-privilege access/);
    expect(text).toMatch(/never be exposed in logs or developer interfaces/);
  });

  it('offers sign-in, activation and a request form as the three entry points', () => {
    expect(hrefs).toContain('/organisation/login');
    expect(hrefs).toContain('/organisation/activate');
    expect(text).toContain('Sign in to your organisation');
    expect(text).toContain('Activate with an activation code');
    expect(html).toContain('id="request"');
    for (const id of ['org-request-name', 'org-request-contact', 'org-request-email', 'org-request-message']) {
      expect(html).toContain(`for="${id}"`);
      expect(html).toContain(`id="${id}"`);
    }
    expect(text).toContain('Request an organisation account');
  });

  it('uses the public navigation and footer', () => {
    expect(html).toContain('class="public-nav"');
    expect(html).toContain('class="footer"');
  });
});
