import React from 'react';

/**
 * Organisation sign-in artwork: team members feeding one shared Knowledge Hub of SAP BRIM answers.
 * The sibling of LoginVisual (the individual "BRIM flow → verified answer" art): same card and
 * --lv-* theme tokens (the page's dot texture replaces LoginVisual's grid) from `.auth-visual` in index.css, so both themes work; brand orange stays fixed.
 * Illustrative content only.
 */
const MEMBERS = [
  { initials: 'PS', cy: 86, accent: true },
  { initials: 'DK', cy: 160 },
  { initials: 'AM', cy: 234 },
  { initials: 'LR', cy: 308 },
];

const HUB_ENTRY = { x: 196, y: 196 };

const TOPICS = [
  { label: 'All topics', x: 216, width: 66, active: true },
  { label: 'CC', x: 288, width: 34 },
  { label: 'CI', x: 328, width: 30 },
  { label: 'SOM', x: 364, width: 42 },
  { label: 'FI-CA', x: 412, width: 50 },
];

const Heart = ({ x, y }: { x: number; y: number }) => (
  <path
    transform={`translate(${x} ${y})`}
    d="M5 9C5 9 0 6 0 3C0 0.6 3.4-0.6 5 2C6.6-0.6 10 0.6 10 3C10 6 5 9 5 9Z"
    fill="#ff6600"
  />
);

const Bubble = ({ x, y }: { x: number; y: number }) => (
  <path
    transform={`translate(${x} ${y})`}
    d="M1.5 0H8.5A1.5 1.5 0 0 1 10 1.5V5.5A1.5 1.5 0 0 1 8.5 7H4.5L2 9V7H1.5A1.5 1.5 0 0 1 0 5.5V1.5A1.5 1.5 0 0 1 1.5 0Z"
    fill="none"
    className="ov-stroke-muted"
    strokeWidth="1.2"
  />
);

export const OrgVisual: React.FC<{ className?: string }> = ({ className }) => (
  <svg
    className={className}
    viewBox="0 0 560 380"
    role="img"
    aria-label="Organisation members connected to one shared Knowledge Hub of SAP BRIM answers, organised by topic and private to the team"
  >
    <defs>
      <linearGradient id="ov-link" x1="0" y1="0" x2="1" y2="0">
        <stop offset="0" stopColor="#ff6600" stopOpacity="0.25" />
        <stop offset="1" stopColor="#ff6600" stopOpacity="0.85" />
      </linearGradient>
      <filter id="ov-soft" x="-20%" y="-20%" width="140%" height="140%">
        <feGaussianBlur stdDeviation="14" />
      </filter>
    </defs>

    {/* Members: each one's own sign-in, all feeding the same hub */}
    {MEMBERS.map(({ cy }) => (
      <path
        key={`link-${cy}`}
        d={`M93 ${cy}C150 ${cy} 140 ${HUB_ENTRY.y} ${HUB_ENTRY.x} ${HUB_ENTRY.y}`}
        fill="none"
        stroke="url(#ov-link)"
        strokeWidth="2"
        strokeDasharray="3 5"
        strokeLinecap="round"
      />
    ))}
    <g className="lv-label" textAnchor="middle">
      {MEMBERS.map(({ initials, cy, accent }) => (
        <g key={initials}>
          <circle cx="72" cy={cy} r="21" className={accent ? 'lv-node lv-node-accent' : 'lv-node'} strokeWidth="1.5" />
          <text x="72" y={cy + 4} fontSize="12" fontWeight="700" className="lv-text">
            {initials}
          </text>
        </g>
      ))}
    </g>

    {/* "Members only" */}
    <g className="lv-label">
      <rect x="22" y="342" width="102" height="24" rx="12" className="lv-chip" />
      <path d="M36 352V349.5A3.5 3.5 0 0 1 43 349.5V352" fill="none" className="ov-stroke-muted" strokeWidth="1.4" />
      <rect x="34" y="352" width="11" height="8" rx="2" fill="#ff6600" />
      <text x="51" y="358" fontSize="9.5" fontWeight="600" className="lv-muted">
        Members only
      </text>
    </g>

    {/* The shared Knowledge Hub */}
    <rect x="206" y="52" width="312" height="300" rx="18" fill="#ff6600" opacity="0.12" filter="url(#ov-soft)" />
    <rect x="196" y="34" width="332" height="312" rx="18" className="lv-card" />
    <circle cx={HUB_ENTRY.x} cy={HUB_ENTRY.y} r="4.5" fill="#ff6600" />

    <g className="lv-label">
      <rect x="216" y="54" width="34" height="34" rx="9" fill="#ff6600" fillOpacity="0.14" stroke="#ff6600" strokeOpacity="0.45" />
      <path
        d="M226 81V63H240V81M223 81H243M230 67H231.5M234.5 67H236M230 71H231.5M234.5 71H236M230 75H231.5M234.5 75H236"
        fill="none"
        stroke="#ff6600"
        strokeWidth="1.6"
        strokeLinecap="round"
      />
      <text x="262" y="68" fontSize="13" fontWeight="700" className="lv-text">
        Your organisation
      </text>
      <text x="262" y="84" fontSize="10" className="lv-muted">
        24 members · Knowledge Hub
      </text>

      <rect x="444" y="58" width="66" height="22" rx="11" className="ov-live-pill" />
      <circle cx="457" cy="69" r="3" fill="#10b981" />
      <text x="466" y="72.5" fontSize="9" fontWeight="700" letterSpacing="0.06em" className="ov-live">
        SHARED
      </text>

      <rect x="216" y="102" width="294" height="28" rx="14" className="lv-chip" />
      <circle cx="233" cy="115" r="4.5" fill="none" className="ov-stroke-muted" strokeWidth="1.4" />
      <path d="M236.4 118.4L239.5 121.5" className="ov-stroke-muted" strokeWidth="1.4" strokeLinecap="round" />
      <text x="246" y="119.5" fontSize="10" className="lv-muted">
        Search your team&apos;s saved answers…
      </text>

      {TOPICS.map(({ label, x, width, active }) => (
        <g key={label}>
          <rect
            x={x}
            y="142"
            width={width}
            height="22"
            rx="11"
            className={active ? undefined : 'lv-chip'}
            fill={active ? '#ff6600' : undefined}
            fillOpacity={active ? 0.14 : undefined}
            stroke={active ? '#ff6600' : undefined}
            strokeOpacity={active ? 0.5 : undefined}
          />
          <text
            x={x + width / 2}
            y="156.5"
            fontSize="9.5"
            fontWeight="700"
            textAnchor="middle"
            className={active ? undefined : 'lv-muted'}
            fill={active ? '#ff6600' : undefined}
          >
            {label}
          </text>
        </g>
      ))}

      {/* A shared answer, liked and discussed by the team */}
      <rect x="216" y="178" width="294" height="86" rx="12" className="lv-node" />
      <text x="230" y="197" fontSize="8.5" fontWeight="700" letterSpacing="0.08em" fill="#ff6600">
        CONVERGENT INVOICING
      </text>
      <text x="230" y="214" fontSize="11.5" fontWeight="600" className="lv-text">
        Billable items stuck after the billing run?
      </text>
      <rect x="230" y="222" width="236" height="6" rx="3" className="lv-bar" />
      <rect x="230" y="233" width="172" height="6" rx="3" className="lv-bar" />
      {/* Teammates who liked it: overlapping avatars, the first in brand orange */}
      {[262, 250, 238].map((cx) => (
        <circle
          key={cx}
          cx={cx}
          cy="251"
          r="7"
          className={cx === 238 ? undefined : 'lv-node'}
          fill={cx === 238 ? '#ff6600' : undefined}
          stroke={cx === 238 ? 'var(--lv-card)' : undefined}
          strokeWidth="1.5"
        />
      ))}
      <text x="276" y="254.5" fontSize="9" className="lv-muted">
        Shared by Priya S.
      </text>
      <Heart x={444} y={246.5} />
      <text x="458" y="254.5" fontSize="9.5" fontWeight="600" className="lv-text">
        6
      </text>
      <Bubble x={474} y={246} />
      <text x="489" y="254.5" fontSize="9.5" fontWeight="600" className="lv-text">
        3
      </text>

      <rect x="216" y="274" width="294" height="56" rx="12" className="lv-node" opacity="0.85" />
      <text x="230" y="293" fontSize="8.5" fontWeight="700" letterSpacing="0.08em" fill="#ff6600">
        SAP BRIM INTEGRATION
      </text>
      <text x="230" y="311" fontSize="11.5" fontWeight="600" className="lv-text">
        How does a SOM contract reach CC?
      </text>
      <Heart x={474} y={302.5} />
      <text x="489" y="310.5" fontSize="9.5" fontWeight="600" className="lv-text">
        4
      </text>
    </g>
  </svg>
);
