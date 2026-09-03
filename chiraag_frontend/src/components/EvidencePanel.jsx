import React from 'react'

const Bar = ({ label, value, muted }) => (
  <div className={`score-row ${muted ? 'muted' : ''}`}>
    <span>{label}</span>
    <div className="bar">
      <i style={{ width: `${Math.max(0, Math.min(100, value))}%` }} />
    </div>
  </div>
)


const STATE_LABEL = {
  audited: 'Confirmed by a night audit',
  predicted: 'Inferred from street imagery',
  unobserved: 'No imagery available',
}

export function EvidencePanel({ evidence, onClose }) {
  if (!evidence) return null

  // The API returns NULL for anything we have no imagery for. Treat missing
  // evidence as missing -- never as zero darkness.
  const unknown =
    evidence.observation_state === 'unobserved' ||
    evidence.dark_fraction === null ||
    evidence.dark_fraction === undefined

  const length = Math.round(evidence.length_m ?? 0)
  const darkFraction = evidence.dark_fraction ?? 0
  const litPercent = Math.round((1 - darkFraction) * 100)
  const darkMetres = Math.round(darkFraction * (evidence.length_m ?? 0))
  const longestGap = Math.round(evidence.longest_gap_m ?? 0)

  return (
    <aside className="evidence-drawer" aria-label="Segment evidence">
      <div className="drawer-heading">
        <div>
          <p className="eyebrow">EVIDENCE</p>
          <h2>SEGMENT {evidence.road_id}</h2>
        </div>

        <button
          onClick={onClose}
          className="close"
          aria-label="Close evidence"
        >
          x
        </button>
      </div>

      <p className="segment-state">
        {STATE_LABEL[evidence.observation_state] || evidence.observation_state}
        {' · '}
        {length} m long
      </p>

      {unknown ? (
        <>
          <p className="unknown-message">
            We do not have enough street imagery to say anything about the
            lighting here. That is not the same as saying it is dark, and
            CHIRAAG will not score it as dark.
          </p>

          <div className="score-explanation">
            <p className="eyebrow">WHAT WOULD CHANGE THIS</p>

            <p className="plain-reason">
              A Mapillary capture along this street, or a night audit
              submitted by someone who has walked it.
            </p>
          </div>
        </>
      ) : (
        <>
          <div className="evidence-stats">

            <div>
              <b>{litPercent}%</b>
              <span>OF THIS STREET IS LIT</span>
            </div>

            <div>
              <b>{longestGap} m</b>
              <span>LONGEST DARK GAP</span>
            </div>
          </div>
        </>
      )}

      <div className="evidence-source">
        {unknown
          ? 'No Mapillary street-light detections on this segment'
          : 'Mapillary street-light detections · 25 m assumed light reach'}
      </div>
    </aside>
  )
}