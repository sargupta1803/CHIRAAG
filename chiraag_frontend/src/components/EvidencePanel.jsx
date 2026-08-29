import React from 'react'

const Bar = ({ label, value }) => (
  <div className="score-row">
    <span>{label}</span>
    <div className="bar">
      <i style={{ width: `${value}%` }} />
    </div>
  </div>
)

export function EvidencePanel({ evidence, onClose }) {
  if (!evidence) return null

  const unknown = evidence.is_unknown

  return (
    <aside className="evidence-drawer" aria-label="Segment evidence">
      <div className="drawer-heading">
        <div>
          <p className="eyebrow">EVIDENCE</p>
          <h2>SEGMENT {evidence.seg_id}</h2>
        </div>

        <button
          onClick={onClose}
          className="close"
          aria-label="Close evidence"
        >
          x
        </button>
      </div>

      <div className={`evidence-photo ${unknown ? 'unknown-photo' : ''}`}>
        <img
          src={evidence.image}
          alt={
            unknown
              ? 'No usable street imagery for this segment'
              : 'Street-level observation of selected route segment'
          }
        />

        {unknown && (
          <div>
            <b>UNKNOWN</b>
            <span>Insufficient imagery</span>
          </div>
        )}
      </div>

      {unknown ? (
        <p className="unknown-message">
          We do not have enough imagery to make a claim about this street.
        </p>
      ) : (
        <>
          <div className="evidence-stats">
            <div>
              <b>
                {evidence.lights} LIGHT{evidence.lights !== 1 ? 'S' : ''}
              </b>
              <span>/ 210 m</span>
            </div>

            <div>
              <b>{evidence.longest_gap_m} m</b>
              <span>DARKEST GAP</span>
            </div>
          </div>

          <div className="observations">
            <p className="eyebrow">OBSERVATIONS</p>

            <p>
              <span>+</span> Street light detected
            </p>

            {evidence.cctv && (
              <p>
                <span>+</span> CCTV detected
              </p>
            )}

            <p>
              <span>o</span> Imagery captured: {evidence.captured_at}
            </p>

            <p>
              <span>o</span> Confidence: {evidence.confidence}
            </p>
          </div>

          <div className="score-explanation">
            <p className="eyebrow">WHY CHIRAAG FLAGS THIS</p>

            <p className="plain-reason">
              This segment has a long observed dark gap. It adds more
              night-time risk than nearby lit streets.
            </p>

            <Bar
              label="Lighting coverage"
              value={Math.round((1 - evidence.dark_fraction) * 100)}
            />

            <Bar
              label="Observation coverage"
              value={Math.round(evidence.coverage * 100)}
            />

            <div className="data-line">
              <span>Longest dark gap</span>
              <b>{evidence.longest_gap_m} m</b>
            </div>
          </div>
        </>
      )}

      <div className="evidence-source">
        Mapillary observation · ground-truth-aware score
      </div>
    </aside>
  )
}