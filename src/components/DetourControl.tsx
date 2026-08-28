interface Props { value: number; onChange: (value: number) => void }
export function DetourControl({ value, onChange }: Props) {
  return <section className="control-section section-rule">
    <div className="control-title"><label htmlFor="detour">MAX DETOUR</label><output>{value}%</output></div>
    <input id="detour" type="range" min="5" max="40" step="5" value={value} onChange={e => onChange(Number(e.target.value))} aria-label="Maximum detour" />
    <div className="range-labels"><span>5%</span><span>20%</span><span>40%</span></div>
  </section>
}
