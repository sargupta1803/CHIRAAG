import React from 'react'
export function HeroMetric({ delta }) {
  return <section className="hero-metric" aria-label="Unlit road avoided">
    <div className="metric-number">{delta.dark_avoided_m}<span>m</span></div>
    <div className="metric-label">LESS UNLIT ROAD</div>
    <div className="metric-context">for only <b>{delta.extra_m} m extra</b> <span>(+{delta.extra_pct}%)</span></div>
  </section>
}
