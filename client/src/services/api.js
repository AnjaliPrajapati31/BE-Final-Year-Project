import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 180000,
});

export class ApiError extends Error {
  constructor(message, code, requestId, status) {
    super(message);
    this.name = 'ApiError';
    this.code = code || 'UNKNOWN_ERROR';
    this.requestId = requestId || null;
    this.status = status || 500;
  }
}

const unwrapEnvelope = async (requestPromise) => {
  try {
    const response = await requestPromise;
    if (!response?.data?.success) {
      const payload = response?.data || {};
      throw new ApiError(
        payload.message || 'Request failed.',
        payload.error?.code,
        payload.error?.request_id,
        response?.status,
      );
    }
    return response.data.data;
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    if (error.response?.data) {
      const payload = error.response.data;
      throw new ApiError(
        payload.message || 'Request failed.',
        payload.error?.code,
        payload.error?.request_id,
        error.response.status,
      );
    }
    throw new ApiError(error.message || 'Network request failed.', 'NETWORK_ERROR', null, 0);
  }
};

export const deriveFieldId = (displayName) => {
  const sanitized = (displayName || '')
    .trim()
    .replace(/[^A-Za-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '')
    .toUpperCase();
  if (!sanitized) {
    return '';
  }
  return sanitized.slice(0, 100);
};

export const pointsToPolygonGeoJson = (points) => {
  const ring = points.map((point) => [Number(point.lng), Number(point.lat)]);
  if (ring.length < 3) {
    throw new Error('At least three points are required to build a polygon.');
  }
  const [firstLng, firstLat] = ring[0];
  const [lastLng, lastLat] = ring[ring.length - 1];
  if (firstLng !== lastLng || firstLat !== lastLat) {
    ring.push([firstLng, firstLat]);
  }
  return {
    type: 'Polygon',
    coordinates: [ring],
  };
};

export const extractBoundaryPoints = (geometry) => {
  if (!geometry?.type || !geometry?.coordinates) {
    return [];
  }
  const ring = geometry.type === 'Polygon'
    ? geometry.coordinates?.[0]
    : geometry.coordinates?.[0]?.[0];
  if (!Array.isArray(ring)) {
    return [];
  }
  return ring
    .slice(0, -1)
    .map((coordinate) => ({ lng: coordinate[0], lat: coordinate[1] }));
};

export const analyzeField = async (payload) => unwrapEnvelope(
  api.post('/api/v1/fields/analyze', payload),
);

export const getAnalysis = async (requestId) => unwrapEnvelope(
  api.get(`/api/v1/analyses/${requestId}`),
);

export const getFieldHistory = async (fieldId, { limit = 20, offset = 0 } = {}) => unwrapEnvelope(
  api.get(`/api/v1/fields/${encodeURIComponent(fieldId)}/analyses`, {
    params: { limit, offset },
  }),
);

export const getHealth = async () => unwrapEnvelope(api.get('/health'));

export const getReadiness = async () => unwrapEnvelope(api.get('/health/ready'));

export default api;
