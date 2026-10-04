/**
 * App.js — Root component for FitGenie AI.
 * Defines the application-wide routing and shared layout (header).
 */

import React from "react";
import { BrowserRouter as Router, Routes, Route, Link } from "react-router-dom";
import "./App.css";

import HomePage from "./pages/HomePage";

// Future pages — imported here when created in later stages
// import ProfilePage from "./pages/ProfilePage";
// import PlanPage    from "./pages/PlanPage";

function App() {
  return (
    <Router>
      {/* ── Global Navigation Bar ─────────────────────────────── */}
      <header className="navbar">
        <Link to="/" className="navbar-brand">
          💪 FitGenie AI
        </Link>
        <nav className="navbar-links">
          <Link to="/">Home</Link>
          {/* Profile and Plan links will be added in Stage 5 */}
        </nav>
      </header>

      {/* ── Page Content ─────────────────────────────────────── */}
      <main className="main-content">
        <Routes>
          <Route path="/" element={<HomePage />} />
          {/* Routes for later stages: */}
          {/* <Route path="/profile" element={<ProfilePage />} /> */}
          {/* <Route path="/plan"    element={<PlanPage />}    /> */}
        </Routes>
      </main>

      {/* ── Global Footer ─────────────────────────────────────── */}
      <footer className="footer">
        <p>
          FitGenie AI &copy; 2026 — Applied Generative AI Project &nbsp;|&nbsp;
          For educational purposes only.
        </p>
      </footer>
    </Router>
  );
}

export default App;
