interface Props { hour: number; onChange: (value: number) => void }
export function TimeControl({ hour, onChange }: Props) {
  const format = (h: number) => `${String(h).padStart(2, '0')}:00`
  return <section className="control-section section-rule">
    <div className="control-title"><label htmlFor="time">TIME OF DAY</label><output>{format(hour)}</output></div>
    <input id="time" type="range" min="14" max="30" value={hour < 14 ? hour + 24 : hour} onChange={e => onChange(Number(e.target.value) % 24)} aria-label="Time of day" />
    <div className="range-labels"><span>14:00</span><span>19:00</span><span>23:00</span><span>06:00</span></div>
  </section>
}
