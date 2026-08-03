import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { MapContainer, TileLayer, CircleMarker, Polygon, Polyline, Tooltip, useMapEvents } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import { SectionHeader } from '../components/UIHelpers';
import { MapPin, Plus, Globe, Layers, Trash2, CheckCircle, Navigation, Info, RefreshCw, ArrowRight, Send, MousePointerClick, LoaderCircle, AlertTriangle } from 'lucide-react';
import { useApp } from '../contexts/AppContext';
import { analyzeField, ApiError, deriveFieldId, pointsToPolygonGeoJson } from '../services/api';

// Cauvery Delta Region Bounds (Tamil Nadu, India)
const CAUVERY_DELTA_CENTER = [10.85, 79.35];
const CAUVERY_DELTA_BOUNDS = [
  [10.0, 78.4], // South-West
  [11.7, 80.1], // North-East
];

// Default sample points within Cauvery Delta
const DEFAULT_POINTS = [
  { lat: 10.7850, lng: 79.1350 },
  { lat: 10.7910, lng: 79.1350 },
  { lat: 10.7910, lng: 79.1420 },
  { lat: 10.7850, lng: 79.1420 },
];

const MAP_LAYERS = {
  satellite: {
    id: 'satellite',
    name: 'Satellite Map',
    url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    attribution: '&copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community',
  },
  present: {
    id: 'present',
    name: 'Present Map',
    url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
  },
};

// Component to handle map clicks for placing points
const MapClickHandler = ({ onMapClick, isDrawing }) => {
  useMapEvents({
    click(e) {
      if (isDrawing) {
        onMapClick({ lat: Number(e.latlng.lat.toFixed(5)), lng: Number(e.latlng.lng.toFixed(5)) });
      }
    },
  });
  return null;
};

export const MyFields = () => {
  const navigate = useNavigate();
  const {
    setFieldBoundaryPoints,
    fieldDisplayName,
    setFieldDisplayName,
    setFieldId,
    setLatestRequestId,
    setLatestAnalysisSummary,
    setActiveField,
  } = useApp();
  const [selectedLayer, setSelectedLayer] = useState('satellite');
  const [points, setPoints] = useState(DEFAULT_POINTS);
  const [isDrawing, setIsDrawing] = useState(false);
  const [isClosed, setIsClosed] = useState(true); // true when polygon is finalized
  const [analysisYear, setAnalysisYear] = useState(new Date().getFullYear());
  const [generateArtifacts, setGenerateArtifacts] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState(null);

  const currentTileConfig = MAP_LAYERS[selectedLayer];
  const derivedFieldId = deriveFieldId(fieldDisplayName);
  const yearOptions = Array.from(
    { length: new Date().getFullYear() - 2025 + 1 },
    (_, index) => new Date().getFullYear() - index,
  );

  // Handle adding new point on map click
  const handleMapClick = (newPoint) => {
    if (!isDrawing) return;

    // Otherwise add the new point
    setPoints((prev) => [...prev, newPoint]);
  };

  const handleClosePolygon = useCallback(() => {
    if (!isDrawing || points.length < 3) {
      return;
    }
    setIsDrawing(false);
    setIsClosed(true);
  }, [isDrawing, points.length]);

  // Start new drawing mode
  const handleStartDrawing = () => {
    setPoints([]);
    setIsDrawing(true);
    setIsClosed(false);
  };

  // Reset to default sample points
  const handleResetPoints = () => {
    setPoints(DEFAULT_POINTS);
    setIsDrawing(false);
    setIsClosed(true);
  };

  // Clear all points
  const handleClearPoints = () => {
    setPoints([]);
    setIsDrawing(true);
    setIsClosed(false);
  };

  // Manually close the polygon (finish drawing)
  const handleFinishDrawing = () => {
    if (points.length >= 3) {
      setIsDrawing(false);
      setIsClosed(true);
    }
  };

  // Convert points array to LatLng tuples for Leaflet Polygon/Polyline
  const polygonPositions = points.map((p) => [p.lat, p.lng]);

  const handleSubmit = async () => {
    if (!derivedFieldId) {
      setSubmitError({
        message: 'Enter a field display name to generate a valid field code.',
        code: 'INVALID_FIELD_ID',
      });
      return;
    }
    if (!isClosed || points.length < 3) {
      setSubmitError({
        message: 'Finish drawing a closed field polygon before submitting for analysis.',
        code: 'INVALID_GEOMETRY',
      });
      return;
    }

    setSubmitting(true);
    setSubmitError(null);
    try {
      const payload = {
        field_id: derivedFieldId,
        geometry: pointsToPolygonGeoJson(points),
        year: analysisYear,
        season: 'june_october',
        sowing_date_hint: null,
        transplanting_date_hint: null,
        generate_artifacts: generateArtifacts,
      };
      const result = await analyzeField(payload);
      setFieldBoundaryPoints(points);
      setFieldDisplayName(fieldDisplayName.trim());
      setFieldId(derivedFieldId);
      setLatestRequestId(result.request_id);
      setLatestAnalysisSummary(result);
      setActiveField({
        id: derivedFieldId,
        name: fieldDisplayName.trim(),
      });
      navigate(
        `/dashboard?requestId=${encodeURIComponent(result.request_id)}&fieldId=${encodeURIComponent(derivedFieldId)}`,
        { state: { analysis: result } },
      );
    } catch (error) {
      const normalized = error instanceof ApiError
        ? error
        : new ApiError(error.message || 'Analysis request failed.', 'UNKNOWN_ERROR');
      setSubmitError(normalized);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      <SectionHeader
        title="My Agricultural Fields — Cauvery Delta Region"
        subtitle="Manage plot boundaries, view satellite vegetative index (NDVI), and monitor crop health in Tamil Nadu, India"
        action={
          <div className="flex items-center space-x-2">
            {isDrawing ? (
              <>
                <button
                  onClick={handleResetPoints}
                  className="flex items-center space-x-2 bg-slate-200 hover:bg-slate-300 text-slate-800 font-semibold text-xs py-2.5 px-4 rounded-xl transition-all cursor-pointer"
                >
                  <RefreshCw className="w-4 h-4" />
                  <span>Reset Default</span>
                </button>
                {points.length >= 3 && (
                  <button
                    onClick={handleFinishDrawing}
                    className="flex items-center space-x-2 bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs py-2.5 px-4 rounded-xl shadow-xs transition-all cursor-pointer"
                  >
                    <CheckCircle className="w-4 h-4" />
                    <span>Finish Drawing</span>
                  </button>
                )}
              </>
            ) : (
              <button
                onClick={handleStartDrawing}
                className="flex items-center space-x-2 bg-emerald-600 hover:bg-emerald-700 text-white font-medium text-xs py-2.5 px-4 rounded-xl shadow-xs transition-all cursor-pointer"
              >
                <Plus className="w-4 h-4" />
                <span>Draw New Field Boundary</span>
              </button>
            )}
          </div>
        }
      />

      <div className="bg-white rounded-2xl p-6 border border-slate-200/80 shadow-sm space-y-5">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <label className="block space-y-2">
            <span className="text-sm font-semibold text-slate-800">Field Display Name</span>
            <input
              type="text"
              value={fieldDisplayName}
              onChange={(event) => setFieldDisplayName(event.target.value)}
              placeholder="Enter a human-readable field name"
              className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-900 shadow-xs outline-none transition focus:border-emerald-500 focus:ring-2 focus:ring-emerald-100"
            />
          </label>

          <label className="block space-y-2">
            <span className="text-sm font-semibold text-slate-800">Backend Field Code</span>
            <input
              type="text"
              value={derivedFieldId}
              readOnly
              className="w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-semibold text-slate-700 shadow-xs outline-none"
            />
          </label>

          <label className="block space-y-2">
            <span className="text-sm font-semibold text-slate-800">Analysis Year</span>
            <select
              value={analysisYear}
              onChange={(event) => setAnalysisYear(Number(event.target.value))}
              className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-900 shadow-xs outline-none transition focus:border-emerald-500 focus:ring-2 focus:ring-emerald-100"
            >
              {yearOptions.map((year) => (
                <option key={year} value={year}>{year}</option>
              ))}
            </select>
          </label>
        </div>

        <label className="flex items-start gap-3 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
          <input
            type="checkbox"
            checked={generateArtifacts}
            onChange={(event) => setGenerateArtifacts(event.target.checked)}
            className="mt-1 h-4 w-4 rounded border-slate-300 text-emerald-700 focus:ring-emerald-500"
          />
          <span className="text-sm text-slate-700">
            Generate optional artifacts like stage timelines and crop summaries for this analysis.
          </span>
        </label>

        {submitError && (
          <div className="flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-900">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
            <div>
              <div className="font-semibold">{submitError.message}</div>
              <div className="text-xs text-red-700">
                {submitError.code}
                {submitError.requestId ? ` · Request ID ${submitError.requestId}` : ''}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Map View Container */}
      <div className="bg-white rounded-2xl p-4 border border-slate-200/80 shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center space-x-2">
            <MapPin className="w-4 h-4 text-emerald-600" />
            <span className="text-sm font-bold text-slate-800">Cauvery Delta GIS & Interactive Plot Drawer</span>
            <span className="text-[11px] font-semibold px-2.5 py-0.5 bg-emerald-50 text-emerald-700 rounded-lg border border-emerald-200/60">
              Locked Region: Cauvery Delta (Tamil Nadu)
            </span>
          </div>

          {/* Exclusive Layer Selector */}
          <div className="flex items-center space-x-1 bg-slate-100 p-1 rounded-xl border border-slate-200/80">
            <span className="text-xs font-semibold text-slate-500 px-2 flex items-center gap-1">
              <Layers className="w-3.5 h-3.5" />
              Map Mode:
            </span>
            <button
              onClick={() => setSelectedLayer('satellite')}
              className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                selectedLayer === 'satellite'
                  ? 'bg-emerald-600 text-white shadow-xs'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/60'
              }`}
            >
              <Globe className="w-3.5 h-3.5" />
              <span>Satellite Map</span>
            </button>
            <button
              onClick={() => setSelectedLayer('present')}
              className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                selectedLayer === 'present'
                  ? 'bg-emerald-600 text-white shadow-xs'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/60'
              }`}
            >
              <MapPin className="w-3.5 h-3.5" />
              <span>Present Map</span>
            </button>
          </div>
        </div>

        {/* Drawing Status Banner */}
        <div className="flex items-center justify-between bg-emerald-50 border border-emerald-200/70 rounded-xl px-4 py-2.5 text-xs text-emerald-900">
          <div className="flex items-center space-x-2 font-medium">
            <Info className="w-4 h-4 text-emerald-700 shrink-0" />
            {isDrawing ? (
              <span>
                <strong>Drawing Mode Active:</strong> Click on the map to place vertices ({points.length} point{points.length !== 1 ? 's' : ''} placed).
                {points.length >= 3 && (
                  <> Click the highlighted <strong>starting point (P1)</strong> to close the polygon, or press <em>"Finish Drawing"</em>.</>
                )}
                {points.length < 3 && (
                  <> Place at least 3 points to form a polygon.</>
                )}
              </span>
            ) : (
              <span>
                <strong>Field Boundary Finalized:</strong> {points.length} boundary vertices defined below. Click <em>"Draw New Field Boundary"</em> to redraw.
              </span>
            )}
          </div>
          {points.length > 0 && (
            <button
              onClick={handleClearPoints}
              className="flex items-center space-x-1 text-[11px] font-bold text-red-600 hover:text-red-700 bg-white px-2.5 py-1 rounded-lg border border-red-200 shadow-2xs transition-all cursor-pointer shrink-0 ml-3"
            >
              <Trash2 className="w-3 h-3" />
              <span>Clear All</span>
            </button>
          )}
        </div>

        {/* Leaflet Map Locked to Cauvery Delta Region */}
        <div className={`h-[500px] w-full rounded-xl overflow-hidden border border-slate-200 z-0 relative ${isDrawing ? 'cursor-crosshair' : ''}`}>
          <MapContainer
            center={CAUVERY_DELTA_CENTER}
            zoom={10}
            minZoom={9}
            maxZoom={16}
            maxBounds={CAUVERY_DELTA_BOUNDS}
            maxBoundsViscosity={1.0}
            scrollWheelZoom={true}
            className="h-full w-full"
          >
            <TileLayer
              key={currentTileConfig.id}
              attribution={currentTileConfig.attribution}
              url={currentTileConfig.url}
            />

            {/* Click Handler */}
            <MapClickHandler onMapClick={handleMapClick} isDrawing={isDrawing} />

            {/* Closed Polygon (when finalized or 3+ points while drawing) */}
            {isClosed && points.length >= 3 && (
              <Polygon
                positions={polygonPositions}
                pathOptions={{
                  color: '#10b981',
                  fillColor: '#10b981',
                  fillOpacity: 0.35,
                  weight: 3,
                }}
              />
            )}

            {/* Open Polyline while actively drawing (not yet closed) */}
            {!isClosed && points.length >= 2 && (
              <Polyline
                positions={polygonPositions}
                pathOptions={{
                  color: '#10b981',
                  dashArray: '6, 6',
                  weight: 3,
                }}
              />
            )}

            {/* Single line segment for 2 points while drawing */}
            {!isClosed && points.length === 1 && null}

            {/* Render Dots / Vertices */}
            {points.map((point, index) => (
              <CircleMarker
                key={index}
                center={[point.lat, point.lng]}
                radius={index === 0 && isDrawing && points.length >= 3 ? 12 : 9}
                eventHandlers={index === 0 && isDrawing && points.length >= 3 ? { click: handleClosePolygon } : undefined}
                pathOptions={{
                  color: index === 0 && isDrawing && points.length >= 3 ? '#fbbf24' : '#ffffff',
                  fillColor: index === 0 && isDrawing && points.length >= 3 ? '#f59e0b' : '#059669',
                  fillOpacity: 1,
                  weight: index === 0 && isDrawing && points.length >= 3 ? 3 : 2.5,
                }}
              >
                <Tooltip permanent direction="top" offset={[0, -10]} className="font-sans font-bold text-xs bg-slate-900 text-white rounded-md px-2 py-0.5 border-none">
                  {index === 0 && isDrawing && points.length >= 3 ? 'Click to Close' : `P${index + 1}`}
                </Tooltip>
              </CircleMarker>
            ))}
          </MapContainer>
        </div>
      </div>

      {/* Dynamic Coordinates Display Section Below Map */}
      <div className="bg-white rounded-2xl p-6 border border-slate-200/80 shadow-sm space-y-4">
        <div className="flex items-center justify-between border-b border-slate-100 pb-4">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-emerald-100 text-emerald-800 flex items-center justify-center font-bold shadow-xs">
              <Navigation className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-900 font-serif">
                Field Boundary Coordinates
              </h3>
              <p className="text-xs text-slate-500">
                Latitude & Longitude for each polygon vertex
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <span className={`text-xs font-semibold px-3 py-1 rounded-full border ${
              isClosed && points.length >= 3
                ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                : 'bg-amber-50 text-amber-700 border-amber-200'
            }`}>
              {isClosed && points.length >= 3
                ? `✓ Polygon Closed · ${points.length} Vertices`
                : isDrawing
                  ? `Drawing · ${points.length} Point${points.length !== 1 ? 's' : ''}`
                  : `${points.length} Point${points.length !== 1 ? 's' : ''}`
              }
            </span>
          </div>
        </div>

        {/* Dynamic Points Grid — renders a card for every placed point */}
        {points.length > 0 ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {points.map((pt, i) => (
              <div
                key={i}
                className="rounded-2xl p-4 border bg-emerald-50/40 border-emerald-200/80 shadow-xs transition-all hover:shadow-md hover:border-emerald-400"
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="w-7 h-7 rounded-lg text-xs font-black flex items-center justify-center bg-emerald-700 text-white">
                    P{i + 1}
                  </span>
                  <CheckCircle className="w-4 h-4 text-emerald-600" />
                </div>

                <div className="space-y-1 mt-3">
                  <div>
                    <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Latitude</p>
                    <p className="text-sm font-extrabold text-slate-800 font-mono">{pt.lat.toFixed(5)}° N</p>
                  </div>
                  <div className="pt-1">
                    <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Longitude</p>
                    <p className="text-sm font-extrabold text-slate-800 font-mono">{pt.lng.toFixed(5)}° E</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="py-8 text-center">
            <MousePointerClick className="w-8 h-8 text-slate-300 mx-auto mb-2" />
            <p className="text-sm font-medium text-slate-400">No points placed yet. Click on the map to start drawing.</p>
          </div>
        )}

        {/* Submit & View Analytics CTA Footer */}
        {points.length >= 3 && isClosed && (
          <div className="pt-4 border-t border-slate-100 flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="flex items-center space-x-2 text-xs text-slate-600 font-medium">
              <Send className="w-4 h-4 text-emerald-700 shrink-0" />
              <span>Submit these {points.length} boundary coordinates to run live Cauvery crop analysis from the FastAPI backend.</span>
            </div>
            <button
              type="button"
              onClick={handleSubmit}
              disabled={submitting}
              className="w-full sm:w-auto inline-flex items-center justify-center space-x-2.5 bg-emerald-700 hover:bg-emerald-800 disabled:opacity-70 text-white font-extrabold text-xs sm:text-sm py-3 px-8 rounded-xl shadow-md transition-all hover:scale-105 cursor-pointer group shrink-0"
            >
              {submitting ? (
                <>
                  <LoaderCircle className="w-4 h-4 animate-spin" />
                  <span>Submitting Analysis...</span>
                </>
              ) : (
                <>
                  <span>Submit and View Analytics</span>
                  <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                </>
              )}
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
