import { useState } from "react";

import { predictSoil } from "../services/api.js";

const fields = [
  "N",
  "P",
  "K",
  "pH",
  "EC",
  "OC",
  "S",
  "Zn",
  "Fe",
  "Cu",
  "Mn",
  "B",
];

const initialValues = fields.reduce((accumulator, field) => {
  accumulator[field] = "";
  return accumulator;
}, {});

function Soil() {
  const [form, setForm] = useState(initialValues);
  const [prediction, setPrediction] = useState("No Prediction Yet");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  function handleChange(event) {
    const { name, value } = event.target;
    setForm((current) => ({ ...current, [name]: value }));
  }

  async function handlePredict(event) {
    event.preventDefault();
    setLoading(true);
    setMessage("");

    try {
      const payload = Object.fromEntries(
        fields.map((field) => [field, Number(form[field])]),
      );
      const response = await predictSoil(payload);
      setPrediction(response?.data?.prediction ?? "No Prediction Yet");
      setMessage(response?.message ?? "");
    } catch (error) {
      setPrediction("No Prediction Yet");
      setMessage(error instanceof Error ? error.message : "Request failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="page">
      <h1 className="page-title">Soil Fertility Prediction</h1>

      <form className="soil-form" onSubmit={handlePredict}>
        {fields.map((field) => (
          <label className="field" key={field}>
            <span className="field-label">{field}</span>
            <input
              className="input"
              name={field}
              value={form[field]}
              onChange={handleChange}
              type="text"
            />
          </label>
        ))}

        <button className="button" type="submit" disabled={loading}>
          {loading ? "Predicting..." : "Predict"}
        </button>

        <div className="result-box">
          <div className="result-label">Prediction</div>
          <div className="result-value">{prediction}</div>
          {message ? <div className="result-message">{message}</div> : null}
        </div>
      </form>
    </section>
  );
}

export default Soil;
