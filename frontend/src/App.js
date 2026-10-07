/**
 * App.js — Root component for FitGenie AI.
 * Defines the application layout, navigation bar, and routing.
 */

import React from "react";
import { BrowserRouter as Router, Routes, Route, Link } from "react-router-dom";
import "./App.css";

import HomePage from "./pages/HomePage";

function App() {
  return (
    <Router>
      <div className="app-container">
        {/* ── Global Top Navigation Bar ─────────────────────────────── */}
        <header className="navbar">
          <div className="navbar-container">
            <Link to="/" className="navbar-brand">
              <span className="brand-icon">FG</span>
              <span className="brand-text">FitGenie <span className="brand-accent">AI</span></span>
            </Link>

            <nav className="navbar-links">
              <a href="#dashboard" className="nav-item">Dashboard</a>
              <a href="#workout" className="nav-item">Today's Workout</a>
              <a href="#schedule" className="nav-item">Weekly Schedule</a>
              <a href="#nutrition" className="nav-item">Nutrition</a>
              <a href="#ai-coach" className="nav-item nav-item-coach">AI Coach</a>
            </nav>

            <div className="navbar-profile">
              <div className="profile-indicator">
                <span className="profile-avatar">FG</span>
                <span className="profile-status-dot"></span>
              </div>
            </div>
          </div>
        </header>

        {/* ── Page Content ─────────────────────────────────────── */}
        <main className="main-content">
          <Routes>
            <Route path="/" element={<HomePage />} />
          </Routes>
        </main>

        {/* ── Global Footer ─────────────────────────────────────── */}
        <footer className="footer">
          <div className="footer-container">
            <p>
              <strong>FitGenie AI</strong> &copy; 2026 — Personalized Fitness &amp; Nutrition System Powered by Generative AI.
            </p>
            <p className="footer-sub">
              Demonstration &amp; Educational Project &nbsp;|&nbsp; Built with Google Gemini &amp; FastAPI.
            </p>
          </div>
        </footer>
      </div>
    </Router>
  );
}

export default App;
