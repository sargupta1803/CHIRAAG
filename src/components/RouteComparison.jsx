export function RouteComparison({ data, selected, onSelect }) {
  return <section className="comparison" aria-label="Route comparison">
    <p className="eyebrow">COMPARE ROUTES</p>
    <button className={`route-choice ${selected === 'short' ? 'selected' : ''}`} onClick={() => onSelect('short')}>
      <span className="route-swatch shortest" /><span className="route-kind"><b>Shortest</b><small>{data.shortest.dark_m} m unlit</small></span><strong>{data.shortest.length_m} m <small>&middot; ~10 min</small></strong>
    </button>
    <button className={`route-choice ${selected === 'safe' ? 'selected' : ''}`} onClick={() => onSelect('safe')}>
      <span className="route-swatch safe" /><span className="route-kind"><b>Chiraag / safer</b><small>{data.safest.dark_m} m unlit</small></span><strong>{data.safest.length_m} m <small>&middot; ~11 min</small></strong>
    </button>
  </section>
}
