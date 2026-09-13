const ERROR_MESSAGES = {
  INVALID_GEOMETRY: ['Check the field boundary', 'Draw a closed field inside the supported Cauvery area and try again.'],
  INVALID_REQUEST: ['Check the entered values', 'One or more values are missing or outside the allowed range.'],
  FIELD_NOT_FOUND: ['Field not found', 'Run an analysis for this field before adding water records.'],
  FIELD_TOO_SMALL: ['Field boundary is too small', 'Draw a larger field boundary and try again.'],
  FIELD_TOO_LARGE: ['Field boundary is too large', 'Split the area into a smaller field boundary.'],
  FIELD_DOES_NOT_FIT_PATCH: ['Field shape is too wide', 'Draw a smaller field that fits within the supported analysis patch.'],
  TOO_MANY_VERTICES: ['Boundary is too detailed', 'Simplify the field outline and try again.'],
  INSUFFICIENT_SENTINEL1: ['Not enough radar observations', 'Try another season or wait for more usable satellite coverage.'],
  INSUFFICIENT_SENTINEL2: ['Not enough optical observations', 'Cloud-free imagery is insufficient for this field and season.'],
  HISTORICAL_WEATHER_UNAVAILABLE: ['Weather history is unavailable', 'The crop result is preserved, but water advice cannot be calculated yet.'],
  FORECAST_WEATHER_UNAVAILABLE: ['Forecast is unavailable', 'Current field results remain available; forecast-based timing may be limited.'],
  INVALID_WATER_PROFILE: ['Check the water profile', 'Soil and water values must be within the displayed ranges.'],
  DUPLICATE_IRRIGATION_EVENT: ['Irrigation is already recorded', 'This submission matches an existing irrigation entry.'],
  DUPLICATE_WATER_OBSERVATION: ['Observation is already recorded', 'This submission matches an existing field-water observation.'],
  OUTSIDE_SUPPORTED_ROI: ['Field is outside the supported area', 'Choose a field within the approved Cauvery Delta pilot region.'],
  ANALYSIS_NOT_FOUND: ['Analysis not found', 'This saved analysis may have been removed or the link is incorrect.'],
  MODEL_NOT_READY: ['Crop model is starting', 'Please wait a moment and try the analysis again.'],
  DATABASE_NOT_READY: ['Saved data is temporarily unavailable', 'The service cannot access stored field data right now. Try again shortly.'],
  DATABASE_WRITE_FAILED: ['Could not save the analysis', 'Nothing was silently discarded. Please try again.'],
  EARTH_ENGINE_NOT_READY: ['Satellite service is unavailable', 'Live satellite data could not be reached. Try again later.'],
  SATELLITE_DATA_UNAVAILABLE: ['Satellite data is not available', 'There are not enough usable observations for this field and season.'],
  CROP_INFERENCE_FAILED: ['Crop analysis could not finish', 'The crop result was not produced. Please retry the field analysis.'],
  AI_EXPLANATION_UNAVAILABLE: ['AI explanation is turned off', 'The scientific results and irrigation advice are still available below.'],
  AI_EXPLANATION_FAILED: ['Explanation could not be generated', 'The analysis is unchanged. You can try the explanation again later.'],
  NETWORK_ERROR: ['Cannot reach the server', 'Check that the backend is running and your connection is available.'],
};

export const presentError = (error, fallback = 'Something went wrong. Please try again.') => {
  const [title, message] = ERROR_MESSAGES[error?.code] || ['Unable to complete this action', error?.message || fallback];
  return { title, message, requestId: error?.requestId || null };
};

export const presentModuleStatus = (status) => ({
  completed: { label: 'Available', tone: 'success' },
  skipped: { label: 'Not needed', tone: 'neutral' },
  insufficient_data: { label: 'Needs more data', tone: 'warning' },
  failed: { label: 'Could not complete', tone: 'danger' },
}[status] || { label: 'Not available', tone: 'neutral' });

export const presentOverallStatus = (status) => ({
  completed: 'Analysis complete',
  partial: 'Complete with limitations',
  failed: 'Analysis could not complete',
}[status] || 'Analysis in progress');

export const presentAdvisoryAction = (action) => ({
  irrigate_now: 'Irrigate now',
  irrigate_soon: 'Irrigate within 2 days',
  monitor: 'Monitor the field',
  delay_for_rain: 'Wait for forecast rain',
  no_irrigation_required: 'No irrigation needed',
  unavailable: 'Advice unavailable',
}[action] || 'Advice unavailable');

export const formatNumber = (value, digits = 1, suffix = '') => (
  value === null || value === undefined || Number.isNaN(Number(value))
    ? 'Not available'
    : `${Number(value).toFixed(digits)}${suffix}`
);
