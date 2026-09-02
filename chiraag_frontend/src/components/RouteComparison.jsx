import React from 'react'

export function RouteComparison({ data, selected, onSelect }) {
  const shortest = data.baseline_route
  const safer = data.chiraag_route

  return (
    <section className="comparison" aria-label="Route comparison">
      <p className="eyebrow">COMPARE ROUTES</p>

      <button
        type="button"
        className={`route-choice ${
          selected === 'shortest' ? 'selected' : ''
        }`}
        onClick={() => onSelect('shortest')}
      >
        <span className="route-swatch shortest" />

        <span className="route-kind">
          <b>Shortest</b>
          <small>
            {Math.round(shortest.metrics.unlit_length_m)} m unlit
          </small>
        </span>

        <strong>
          {Math.round(shortest.metrics.total_length_m)} m
        </strong>
      </button>

      <button
        type="button"
        className={`route-choice ${
          selected === 'safe' ? 'selected' : ''
        }`}
        onClick={() => onSelect('safe')}
      >
        <span className="route-swatch safe" />

        <span className="route-kind">
          <b>Chiraag / safer</b>
          <small>
            {Math.round(safer.metrics.unlit_length_m)} m unlit
          </small>
        </span>

        <strong>
          {Math.round(safer.metrics.total_length_m)} m
        </strong>
      </button>
    </section>
  )
}