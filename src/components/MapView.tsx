import { useEffect, useRef } from 'react'
import maplibregl, { type Map } from 'maplibre-gl'
import { Protocol } from 'pmtiles'
import type { GeoJsonLine, RouteResponse } from '../types'

type RoadProps = { kind: 'primary' | 'secondary' | 'local' }
const road = (coordinates: [number, number][], kind: RoadProps['kind']): GeoJSON.Feature<GeoJSON.LineString, RoadProps> => ({ type: 'Feature', properties: { kind }, geometry: { type: 'LineString', coordinates } })
const ROAD_LINES: GeoJSON.FeatureCollection<GeoJSON.LineString, RoadProps> = { type: 'FeatureCollection', features: [
  road([[77.2108,28.6348],[77.2142,28.6339],[77.218,28.6329],[77.2222,28.6305],[77.2269,28.6272]], 'primary'), road([[77.2131,28.6260],[77.2157,28.6288],[77.2188,28.6313],[77.2219,28.6336],[77.2248,28.6350]], 'primary'),
  road([[77.2118,28.6290],[77.2155,28.6297],[77.2195,28.6298],[77.2247,28.6294],[77.2271,28.6288]], 'secondary'), road([[77.2147,28.6360],[77.2161,28.6331],[77.2173,28.6300],[77.2190,28.6262]], 'secondary'), road([[77.2206,28.6352],[77.2202,28.6321],[77.2209,28.6287],[77.2225,28.6255]], 'secondary'),
  road([[77.2122,28.6331],[77.2149,28.6318],[77.2176,28.6307],[77.2204,28.6297],[77.2238,28.6281],[77.2261,28.6265]], 'local'), road([[77.2134,28.6271],[77.2164,28.6280],[77.2197,28.6288],[77.2235,28.6302],[77.2260,28.6319]], 'local'), road([[77.2151,28.6350],[77.2172,28.6322],[77.2193,28.6300],[77.2214,28.6270]], 'local'), road([[77.2170,28.6352],[77.2181,28.6326],[77.2202,28.6294],[77.2236,28.6262]], 'local'), road([[77.2228,28.6342],[77.2225,28.6310],[77.2238,28.6281],[77.2255,28.6262]], 'local')
] }
const BLOCKS: GeoJSON.FeatureCollection<GeoJSON.Polygon> = { type: 'FeatureCollection', features: [
  [[77.2115,28.6340],[77.2139,28.6335],[77.2149,28.6319],[77.2125,28.6321]], [[77.2154,28.6333],[77.2176,28.6327],[77.2184,28.6308],[77.2162,28.6312]], [[77.2194,28.6325],[77.2214,28.6314],[77.2213,28.6298],[77.2195,28.6301]], [[77.2223,28.6304],[77.2246,28.6294],[77.2253,28.6279],[77.2236,28.6280]], [[77.2140,28.6300],[77.2159,28.6298],[77.2168,28.6282],[77.2147,28.6280]], [[77.2173,28.6294],[77.2194,28.6292],[77.2206,28.6277],[77.2188,28.6275]], [[77.2209,28.6285],[77.2226,28.6278],[77.2234,28.6264],[77.2217,28.6262]]
].map(coordinates => ({ type: 'Feature', properties: {}, geometry: { type: 'Polygon', coordinates: [[...coordinates, coordinates[0]]] } })) }
const PARK: GeoJSON.Feature<GeoJSON.Polygon> = { type: 'Feature', properties: {}, geometry: { type: 'Polygon', coordinates: [[[77.2231,28.6334],[77.2258,28.6325],[77.2263,28.6344],[77.2240,28.6351],[77.2231,28.6334]]] } }
const SEGMENTS: GeoJSON.FeatureCollection<GeoJSON.LineString, { seg_id: number; status: string }> = { type: 'FeatureCollection', features: [
  { type:'Feature', properties:{seg_id:4412,status:'observed'}, geometry:{type:'LineString',coordinates:[[77.2186,28.6317],[77.2201,28.6306],[77.2212,28.6286]]}}, { type:'Feature', properties:{seg_id:4413,status:'observed'}, geometry:{type:'LineString',coordinates:[[77.2168,28.6328],[77.2186,28.6317]]}}, { type:'Feature', properties:{seg_id:4414,status:'unknown'}, geometry:{type:'LineString',coordinates:[[77.2161,28.6313],[77.2173,28.6296]]}}, { type:'Feature', properties:{seg_id:4415,status:'observed'}, geometry:{type:'LineString',coordinates:[[77.2173,28.6296],[77.2195,28.6290],[77.2212,28.6286]]}}
] }
const OBSERVATIONS: GeoJSON.FeatureCollection<GeoJSON.Point> = { type:'FeatureCollection', features:[{type:'Feature',properties:{},geometry:{type:'Point',coordinates:[77.2174,28.6298]}},{type:'Feature',properties:{},geometry:{type:'Point',coordinates:[77.2195,28.6290]}},{type:'Feature',properties:{},geometry:{type:'Point',coordinates:[77.2210,28.6287]}}] }
interface Props { data: RouteResponse; selected: 'safe' | 'short'; selectedSegment: number | null; onSegment: (id: number) => void }
const line = (route: GeoJsonLine) => ({ type: 'FeatureCollection' as const, features: [route] })

export function MapView({ data, selected, selectedSegment, onSegment }: Props) {
  const container = useRef<HTMLDivElement>(null); const map = useRef<Map | null>(null)
  useEffect(() => {
    if (!container.current || map.current) return
    const protocol = new Protocol(); maplibregl.addProtocol('pmtiles', protocol.tile)
    const useLocalPmtiles = import.meta.env.VITE_USE_LOCAL_PMTILES === 'true'
    const style: maplibregl.StyleSpecification = useLocalPmtiles ? { version: 8, sources: { ward: { type:'vector', url:'pmtiles:///ward.pmtiles' } }, layers: [{id:'background', type:'background', paint:{'background-color':'#e7e3d8'}}] } : { version: 8, sources: {}, layers: [{ id: 'background', type: 'background', paint: { 'background-color': '#e7e3d8' } }] }
    const m = new maplibregl.Map({ container: container.current, style, center: [77.2194, 28.6302], zoom: 15.65, attributionControl: false, pitchWithRotate: false, dragRotate: false })
    map.current = m
    m.on('load', () => {
      m.addSource('blocks', { type:'geojson', data: BLOCKS }); m.addLayer({ id:'blocks', type:'fill', source:'blocks', paint:{'fill-color':'#d8d5ca','fill-opacity':.7} })
      m.addSource('park', { type:'geojson', data: PARK }); m.addLayer({ id:'park', type:'fill', source:'park', paint:{'fill-color':'#cbd4c4','fill-opacity':.9} })
      m.addSource('roads', { type:'geojson', data: ROAD_LINES }); m.addLayer({ id:'road-casing', type:'line', source:'roads', paint:{'line-color':['match',['get','kind'],'primary','#b9b6aa','secondary','#c8c4b8','#d5d1c7'],'line-width':['match',['get','kind'],'primary',6,'secondary',4,2],'line-opacity':.55}, layout:{'line-cap':'round','line-join':'round'} });m.addLayer({ id:'roads', type:'line', source:'roads', paint:{'line-color':['match',['get','kind'],'primary','#f8f6ef','secondary','#f1eee5','#e4e0d6'],'line-width':['match',['get','kind'],'primary',5,'secondary',3,1.3],'line-opacity':1}, layout:{'line-cap':'round','line-join':'round'} })
      m.addSource('shortest', { type:'geojson', data: line(data.shortest.geojson) }); m.addLayer({ id:'shortest-line', type:'line', source:'shortest', paint:{'line-color':'#575b58','line-width': selected === 'short' ? 6 : 3.5,'line-opacity': selected === 'short' ? .92 : .64}, layout:{'line-cap':'round','line-join':'round'} })
      m.addSource('safest', { type:'geojson', data: line(data.safest.geojson) }); m.addLayer({ id:'safest-line', type:'line', source:'safest', paint:{'line-color':'#ad7f24','line-width': selected === 'safe' ? 7 : 4.5,'line-opacity': selected === 'safe' ? 1 : .72}, layout:{'line-cap':'round','line-join':'round'} })
      m.addSource('segments', { type:'geojson', data: SEGMENTS });m.addLayer({ id:'unknown-segments', type:'line', source:'segments', filter:['==',['get','status'],'unknown'], paint:{'line-color':'#6e746e','line-width':4,'line-dasharray':[1.4,1.4],'line-opacity':.95}, layout:{'line-cap':'round'} });m.addLayer({ id:'segment-hit', type:'line', source:'segments', paint:{'line-color':'#000','line-opacity':0,'line-width':18} })
      m.addSource('observations', {type:'geojson',data:OBSERVATIONS});m.addLayer({id:'observations',type:'circle',source:'observations',paint:{'circle-radius':4,'circle-color':'#f9f6ed','circle-stroke-color':'#77836f','circle-stroke-width':2}})
      m.addSource('selected-segment', { type:'geojson', data:{type:'FeatureCollection',features:[]} });m.addLayer({ id:'selected-line', type:'line', source:'selected-segment', paint:{'line-color':'#b84731','line-width':7,'line-opacity':.95}, layout:{'line-cap':'round'} })
      for (const [coords, label, color] of [[[77.2168,28.6328], 'A', '#222522'], [[77.2233,28.6272], 'B', '#ad7f24']] as const) new maplibregl.Marker({ color }).setLngLat(coords as [number, number]).setPopup(new maplibregl.Popup({offset:22}).setText(label === 'A' ? 'Connaught Place' : 'India Gate')).addTo(m)
      m.on('mouseenter','segment-hit',()=>m.getCanvas().style.cursor='pointer');m.on('mouseleave','segment-hit',()=>m.getCanvas().style.cursor='');m.on('click','segment-hit',(e)=> { const id=(e.features?.[0].properties?.seg_id as number | undefined); if(id) onSegment(id) })
    })
    return () => { m.remove(); map.current = null }
  // Initial map setup; route updates are handled below.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])
  useEffect(() => { const m=map.current; if(!m?.isStyleLoaded()) return; (m.getSource('shortest') as maplibregl.GeoJSONSource | undefined)?.setData(line(data.shortest.geojson));(m.getSource('safest') as maplibregl.GeoJSONSource | undefined)?.setData(line(data.safest.geojson));m.setPaintProperty('shortest-line','line-width',selected==='short'?6:3.5);m.setPaintProperty('shortest-line','line-opacity',selected==='short'?.92:.64);m.setPaintProperty('safest-line','line-width',selected==='safe'?7:4.5);m.setPaintProperty('safest-line','line-opacity',selected==='safe'?1:.72) }, [data,selected])
  useEffect(() => { const m=map.current; const feature=SEGMENTS.features.find(f=>f.properties.seg_id===selectedSegment); if(m?.isStyleLoaded()) (m.getSource('selected-segment') as maplibregl.GeoJSONSource | undefined)?.setData({type:'FeatureCollection',features:feature?[feature]:[]}) }, [selectedSegment])
  return <div ref={container} className="map-canvas"><div className="map-name name-cp">CONNAUGHT PLACE</div><div className="map-name name-park">CENTRAL PARK</div><div className="map-name name-ig">INDIA GATE</div><div className="route-chip"><i className={selected === 'safe' ? 'gold' : 'grey'} />{selected === 'safe' ? 'Safer route selected' : 'Shortest route selected'}</div><div className="map-legend"><span><i className="legend-safe" /> Safer</span><span><i className="legend-short" /> Shortest</span><span><i className="legend-unknown" /> Limited observation</span></div><div className="map-scale"><i />100 m</div><div className="map-attribution">&copy; OpenStreetMap contributors &nbsp; Imagery &copy; Mapillary, CC BY-SA</div></div>
}
