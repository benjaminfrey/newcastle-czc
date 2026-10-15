import { layers, namedFlavor } from "@protomaps/basemaps";
import { addProtocol, LngLatBounds, Map as MlMap, NavigationControl, type GeoJSONSource, type MapMouseEvent } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { Protocol } from "pmtiles";
import { useEffect, useRef } from "react";
import type { Facts } from "../api";

let protocolAdded = false;
const NEWCASTLE: [number, number, number, number] = [-69.66, 43.96, -69.49, 44.13];

type Props = {
  selected: Facts["geometry"] | null;
  focus: { lon: number; lat: number } | null;
  onPick: (lon: number, lat: number) => void;
};

// Every request this map makes goes to our own server: the basemap, its fonts and
// sprites from /basemap/, and parcel lines from /api/tiles/.
export default function ParcelMap({ selected, focus, onPick }: Props) {
  const el = useRef<HTMLDivElement>(null);
  const map = useRef<MlMap | null>(null);
  const pick = useRef(onPick);
  pick.current = onPick;

  useEffect(() => {
    if (!protocolAdded) {
      addProtocol("pmtiles", new Protocol().tile);
      protocolAdded = true;
    }
    const origin = window.location.origin;
    const m = new MlMap({
      container: el.current!,
      maxBounds: NEWCASTLE,
      center: [-69.576, 44.048],
      zoom: 12,
      style: {
        version: 8,
        glyphs: `${origin}/basemap/fonts/{fontstack}/{range}.pbf`,
        sprite: `${origin}/basemap/sprites/light`,
        sources: {
          protomaps: { type: "vector", url: `pmtiles://${origin}/basemap/newcastle.pmtiles`,
                       attribution: "© OpenStreetMap contributors" },
          parcels: { type: "vector", tiles: [`${origin}/api/tiles/parcels/{z}/{x}/{y}.pbf`], minzoom: 12, maxzoom: 18 },
          selected: { type: "geojson", data: { type: "FeatureCollection", features: [] } },
        },
        layers: [
          ...layers("protomaps", namedFlavor("light"), { lang: "en" }),
          { id: "parcel-fill", type: "fill", source: "parcels", "source-layer": "parcels",
            paint: { "fill-color": "#000000", "fill-opacity": 0 } },
          { id: "parcel-line", type: "line", source: "parcels", "source-layer": "parcels",
            paint: { "line-color": "#6b5b3e", "line-width": 0.8 } },
          { id: "selected-line", type: "line", source: "selected",
            paint: { "line-color": "#c2410c", "line-width": 3 } },
        ],
      },
    });
    m.addControl(new NavigationControl({ showCompass: false }));
    m.on("click", (e: MapMouseEvent) => pick.current(e.lngLat.lng, e.lngLat.lat));
    map.current = m;
    return () => m.remove();
  }, []);

  useEffect(() => {
    const m = map.current;
    if (!m) return;
    const apply = () => {
      const src = m.getSource("selected") as GeoJSONSource | undefined;
      src?.setData(selected ? { type: "Feature", properties: {}, geometry: selected }
                            : { type: "FeatureCollection", features: [] });
      if (selected) {
        const b = new LngLatBounds();
        for (const poly of selected.coordinates) for (const ring of poly) for (const c of ring) b.extend([c[0], c[1]]);
        m.fitBounds(b, { padding: 40, maxZoom: 18 });
      }
    };
    if (m.isStyleLoaded()) apply();
    else m.once("load", apply);
  }, [selected]);

  useEffect(() => {
    if (focus && map.current) map.current.flyTo({ center: [focus.lon, focus.lat], zoom: 17 });
  }, [focus]);

  return <div ref={el} className="h-80 w-full rounded-lg sm:h-96" role="region" aria-label="Map of Newcastle" />;
}
