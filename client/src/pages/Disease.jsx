import { useEffect, useState } from "react";

import { predictDisease } from "../services/api.js";

function Disease() {
  const [preview, setPreview] = useState("");
  const [selectedFile, setSelectedFile] = useState(null);
  const [prediction, setPrediction] = useState(null);
  const [confidence, setConfidence] = useState(null);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  function handleFileChange(event) {
    const file = event.target.files?.[0];

    if (!file) {
      setSelectedFile(null);
      setPreview("");
      return;
    }

    setSelectedFile(file);
    setPreview(URL.createObjectURL(file));
  }

  useEffect(() => {
    return () => {
      if (preview) {
        URL.revokeObjectURL(preview);
      }
    };
  }, [preview]);

  async function handlePredict(event) {
    event.preventDefault();
    setLoading(true);
    setMessage("");
    setPrediction(null);
    setConfidence(null);

    try {
      if (!selectedFile) {
        setMessage("Choose an image first");
        return;
      }

      const response = await predictDisease(selectedFile);
      const data = response?.data;
      setPrediction(data?.disease ?? "No Prediction");
      setConfidence(data?.confidence ?? null);
      setMessage(response?.message ?? "");
    } catch (error) {
      setPrediction(null);
      setConfidence(null);
      setMessage(error instanceof Error ? error.message : "Request failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="page">
      <h1 className="page-title">Plant Disease Detection</h1>

      <form className="disease-form" onSubmit={handlePredict}>
        <label className="upload-box">
          <span className="field-label">Image Upload</span>
          <span className="upload-hint">Choose a file</span>
          <input
            className="file-input"
            type="file"
            accept="image/*"
            onChange={handleFileChange}
          />
        </label>

        <div className="preview-box">
          {preview ? (
            <img className="preview-image" src={preview} alt="Preview" />
          ) : (
            <span className="preview-placeholder">Image Preview</span>
          )}
        </div>

        <button className="button" type="submit" disabled={loading}>
          {loading ? "Predicting..." : "Predict"}
        </button>

        <div className="result-box">
          <div className="result-label">Prediction</div>
          {prediction ? (
            <>
              <div className="result-value">{prediction}</div>
              {confidence !== null && (
                <div className="result-message">Confidence: {confidence}%</div>
              )}
            </>
          ) : (
            <div className="result-value">No Prediction Yet</div>
          )}
          {message ? <div className="result-message">{message}</div> : null}
        </div>
      </form>
    </section>
  );
}

export default Disease;
