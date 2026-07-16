import { Link } from "react-router-dom";

function Home() {
  return (
    <section className="page page-home">
      <h1 className="page-title centered">AI Agriculture Assistant</h1>

      <div className="home-grid">
        <Link className="tile" to="/soil">
          <span>Soil Fertility</span>
          <span className="tile-action">Open →</span>
        </Link>

        <Link className="tile" to="/disease">
          <span>Disease Detection</span>
          <span className="tile-action">Open →</span>
        </Link>
      </div>
    </section>
  );
}

export default Home;
