# Earth Engine setup

1. Create or select a Google Cloud project, enable the Earth Engine API, and register the project for Earth Engine access.
2. Grant the development identity or deployment service account access to that project.
3. For local development, authenticate outside the API:

   ```powershell
   gcloud auth application-default login
   gcloud auth application-default set-quota-project YOUR_PROJECT_ID
   ```

4. Copy `.env.example` to the untracked `.env`, set `EARTH_ENGINE_PROJECT_ID`, and configure `DATABASE_URL`.

The server uses Application Default Credentials and never invokes `ee.Authenticate()` or opens a browser. For production, attach a service account/workload identity to the runtime. If a key file is unavoidable, mount it from a secret manager outside the repository and set `GOOGLE_APPLICATION_CREDENTIALS` to that path; never store credential contents or tokens in `.env`.

The live provider uses `COPERNICUS/S1_GRD`, `COPERNICUS/S2_SR_HARMONIZED`, and Earth Engine `computePixels` with a caller-defined 32×32 grid. See the official [computePixels reference](https://developers.google.com/earth-engine/apidocs/ee-data-computepixels) and [service-account guidance](https://developers.google.com/earth-engine/guides/service_account).
