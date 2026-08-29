import React from 'react'

export function UnknownPolicy({ policy, onChange }) {
  const options = [['avoid', 'Avoid unknown'], ['neutral', 'Neutral'], ['show', 'Show gaps']]
  return <section className="unknown-control">
    <p className="eyebrow">UNKNOWN POLICY</p>
    <div className="policy-options" role="radiogroup" aria-label="Unknown segment policy">
      {options.map(([value, label]) => <button key={value} onClick={() => onChange(value)} className={policy === value ? 'active' : ''} role="radio" aria-checked={policy === value}>{label}</button>)}
    </div>
    <p>Unknown means we don’t have enough imagery — not that the street is unsafe.</p>
  </section>
}