/**
 * HomePage.jsx — FitGenie AI Plan Generation & Conversational Modification Page.
 *
 * Implements Stage 5 & Stage 6 User Flow:
 *  1. Header & introduction
 *  2. Natural-language fitness profile input area
 *  3. "Generate My Plan" action with loading & error states
 *  4. Extracted Profile display card
 *  5. 7-Day Fitness & Nutrition Plan cards with workout and meal breakdowns
 *  6. Stage 6: Conversational "Modify Your Plan" section with instant plan update
 *  7. Responsible wellness disclaimer
 */

import React, { useState, useEffect } from "react";
import Disclaimer from "../components/Disclaimer";
import { checkHealth, generatePlan, modifyPlan } from "../services/api";

const SAMPLE_INPUT =
  "I am 21 years old, male, 175 cm tall, 70 kg. My goal is weight loss. I am a beginner. I can exercise for 45 minutes per day. I have dumbbells at home. I prefer Indian vegetarian food. My budget is 3000 rupees per month.";

function HomePage() {
  // Backend connectivity status
  const [backendStatus, setBackendStatus] = useState("checking"); // "checking" | "online" | "offline"

  // Generation state
  const [userInput, setUserInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Result from API: { session_id, plan_id, profile, plan }
  const [result, setResult] = useState(null);

  // Stage 6 Modification state
  const [modifyInput, setModifyInput] = useState("");
  const [modifyLoading, setModifyLoading] = useState(false);
  const [modifyError, setModifyError] = useState(null);
  const [modifySuccess, setModifySuccess] = useState(null);

  // Check health on mount
  useEffect(() => {
    checkHealth()
      .then(() => setBackendStatus("online"))
      .catch(() => setBackendStatus("offline"));
  }, []);

  const handleGenerate = async (e) => {
    if (e) e.preventDefault();
    const trimmed = userInput.trim();
    if (!trimmed) {
      setError("Please enter your fitness information before generating a plan.");
      return;
    }

    setLoading(true);
    setError(null);
    setModifyError(null);
    setModifySuccess(null);

    try {
      const data = await generatePlan(trimmed);
      setResult(data);
    } catch (err) {
      console.error("Plan generation error:", err);
      const detail =
        err.response?.data?.detail ||
        err.message ||
        "Failed to communicate with the backend. Please ensure the server is running.";
      setError(`Unable to generate plan: ${detail}`);
    } finally {
      setLoading(false);
    }
  };

  const handleModify = async (e) => {
    if (e) e.preventDefault();
    const trimmed = modifyInput.trim();
    if (!trimmed) {
      setModifyError("Please enter your plan modification request.");
      return;
    }

    if (!result || !result.plan_id) {
      setModifyError("No active plan found to modify.");
      return;
    }

    setModifyLoading(true);
    setModifyError(null);
    setModifySuccess(null);

    try {
      const updatedData = await modifyPlan(result.plan_id, trimmed);
      setResult(updatedData);
      setModifySuccess("Plan updated successfully.");
      setModifyInput("");
    } catch (err) {
      console.error("Plan modification error:", err);
      const detail =
        err.response?.data?.detail ||
        err.message ||
        "Failed to modify plan. Please try again.";
      setModifyError(`Unable to modify plan: ${detail}`);
    } finally {
      setModifyLoading(false);
    }
  };

  const handleUseSample = () => {
    setUserInput(SAMPLE_INPUT);
    setError(null);
  };

  const handleReset = () => {
    setResult(null);
    setError(null);
    setModifyError(null);
    setModifySuccess(null);
    setModifyInput("");
  };

  return (
    <div className="page home-page">
      {/* ── Header Section ─────────────────────────────────────── */}
      <header className="hero">
        <h1 className="hero-title">💪 FitGenie AI</h1>
        <p className="hero-subtitle">Personalized Fitness &amp; Nutrition Planning</p>
        <p className="hero-description">
          Describe your fitness goals, daily schedule, available equipment, dietary preferences, and budget in plain English. FitGenie will automatically extract your profile and craft a tailored 7-day workout and meal plan.
        </p>

        {/* Backend Status Indicator */}
        <div className="status-badge">
          {backendStatus === "checking" && (
            <span className="badge badge-checking">⏳ Checking backend connection…</span>
          )}
          {backendStatus === "online" && (
            <span className="badge badge-online">✅ Backend online</span>
          )}
          {backendStatus === "offline" && (
            <span className="badge badge-offline">
              ⚠️ Backend offline — start FastAPI server at http://127.0.0.1:8000
            </span>
          )}
        </div>
      </header>

      {/* ── Input Section ──────────────────────────────────────── */}
      <section className="input-card">
        <h2 className="section-title">Tell Us About Yourself</h2>
        <p className="input-hint">
          Include your age, gender, height, weight, goal, workout time, equipment, dietary preferences, and budget.
        </p>

        <form onSubmit={handleGenerate}>
          <textarea
            className="input-textarea"
            rows="6"
            placeholder={`e.g. ${SAMPLE_INPUT}`}
            value={userInput}
            onChange={(e) => {
              setUserInput(e.target.value);
              if (error) setError(null);
            }}
            disabled={loading || modifyLoading}
          />

          <div className="form-actions">
            <button
              type="submit"
              className="btn btn-primary"
              disabled={loading || modifyLoading || backendStatus === "offline"}
            >
              {loading ? "Generating your personalized plan..." : "Generate My Plan →"}
            </button>

            <button
              type="button"
              className="btn btn-secondary"
              onClick={handleUseSample}
              disabled={loading || modifyLoading}
            >
              Fill Sample Profile
            </button>

            {result && (
              <button
                type="button"
                className="btn btn-outline"
                onClick={handleReset}
                disabled={loading || modifyLoading}
              >
                Create New Plan
              </button>
            )}
          </div>
        </form>

        {/* Loading Indicator */}
        {loading && (
          <div className="loading-banner">
            <div className="spinner"></div>
            <div className="loading-text">
              <strong>Generating your personalized plan...</strong>
              <p>Extracting your profile and formulating a balanced 7-day routine.</p>
            </div>
          </div>
        )}

        {/* Error Banner */}
        {error && (
          <div className="error-banner" role="alert">
            <span className="error-icon">⚠️</span>
            <span>{error}</span>
          </div>
        )}
      </section>

      {/* ── Results Section ────────────────────────────────────── */}
      {result && (
        <section className="results-container">
          {/* Profile Card */}
          {result.profile && (
            <div className="profile-card">
              <div className="card-header">
                <h2>👤 Extracted User Profile</h2>
                <span className="session-tag">Session: {result.session_id?.slice(0, 8)}…</span>
              </div>
              <div className="profile-grid">
                <div className="profile-item">
                  <span className="profile-label">Age</span>
                  <span className="profile-val">{result.profile.age ? `${result.profile.age} yrs` : "—"}</span>
                </div>
                <div className="profile-item">
                  <span className="profile-label">Gender</span>
                  <span className="profile-val">{result.profile.gender || "—"}</span>
                </div>
                <div className="profile-item">
                  <span className="profile-label">Height</span>
                  <span className="profile-val">{result.profile.height ? `${result.profile.height} cm` : "—"}</span>
                </div>
                <div className="profile-item">
                  <span className="profile-label">Weight</span>
                  <span className="profile-val">{result.profile.weight ? `${result.profile.weight} kg` : "—"}</span>
                </div>
                <div className="profile-item">
                  <span className="profile-label">Fitness Goal</span>
                  <span className="profile-val highlight">{result.profile.fitness_goal || "—"}</span>
                </div>
                <div className="profile-item">
                  <span className="profile-label">Fitness Level</span>
                  <span className="profile-val">{result.profile.fitness_level || "—"}</span>
                </div>
                <div className="profile-item">
                  <span className="profile-label">Available Time</span>
                  <span className="profile-val">{result.profile.available_time ? `${result.profile.available_time} min/day` : "—"}</span>
                </div>
                <div className="profile-item">
                  <span className="profile-label">Equipment</span>
                  <span className="profile-val">{result.profile.equipment || "Bodyweight"}</span>
                </div>
                <div className="profile-item">
                  <span className="profile-label">Food Preference</span>
                  <span className="profile-val">{result.profile.food_preference || "—"}</span>
                </div>
                <div className="profile-item">
                  <span className="profile-label">Food Restrictions</span>
                  <span className="profile-val">{result.profile.food_restrictions || "None"}</span>
                </div>
                <div className="profile-item">
                  <span className="profile-label">Budget</span>
                  <span className="profile-val highlight">{result.profile.budget != null ? `${result.profile.budget}` : "—"}</span>
                </div>
              </div>
            </div>
          )}

          {/* Plan Section */}
          {result.plan && (
            <div className="plan-section">
              <div className="plan-header-card">
                <h2 className="plan-title">📋 {result.plan.plan_title || "7-Day Personalized Plan"}</h2>
                {result.plan.summary && <p className="plan-summary">{result.plan.summary}</p>}
                {result.plan.modification_summary && (
                  <div className="modification-badge">
                    ✨ <strong>Latest Modification:</strong> {result.plan.modification_summary}
                  </div>
                )}
              </div>

              {/* 7 Days Grid / Cards */}
              <div className="days-container">
                {result.plan.days &&
                  result.plan.days.map((day) => (
                    <div key={day.day_number || day.day_name} className="day-card">
                      <div className="day-header">
                        <span className="day-badge">Day {day.day_number}</span>
                        <h3 className="day-name">{day.day_name}</h3>
                      </div>

                      <div className="day-content-grid">
                        {/* Workout Sub-section */}
                        <div className="section-block workout-block">
                          <h4 className="block-title">🏋️ Workout: {day.workout?.title || "Routine"}</h4>
                          {day.workout && (
                            <>
                              <div className="meta-row">
                                {day.workout.duration_minutes && (
                                  <span className="meta-pill">⏱️ {day.workout.duration_minutes} mins</span>
                                )}
                                {day.workout.focus_area && (
                                  <span className="meta-pill">🎯 {day.workout.focus_area}</span>
                                )}
                              </div>

                              {day.workout.exercises && day.workout.exercises.length > 0 && (
                                <ul className="exercise-list">
                                  {day.workout.exercises.map((ex, idx) => (
                                    <li key={idx} className="exercise-item">
                                      <div className="ex-header">
                                        <strong className="ex-name">{ex.name}</strong>
                                        <span className="ex-reps">{ex.sets ? `${ex.sets} sets × ` : ""}{ex.reps_or_duration}</span>
                                      </div>
                                      {ex.rest_seconds && (
                                        <span className="ex-rest">Rest: {ex.rest_seconds}s</span>
                                      )}
                                      {ex.instructions && (
                                        <p className="ex-instructions">{ex.instructions}</p>
                                      )}
                                    </li>
                                  ))}
                                </ul>
                              )}
                            </>
                          )}
                        </div>

                        {/* Nutrition Sub-section */}
                        <div className="section-block nutrition-block">
                          <h4 className="block-title">🥗 Nutrition</h4>
                          {day.nutrition && (
                            <div className="meals-list">
                              {day.nutrition.breakfast && (
                                <div className="meal-item">
                                  <span className="meal-type">🌅 Breakfast:</span>
                                  <span className="meal-desc">{day.nutrition.breakfast}</span>
                                </div>
                              )}
                              {day.nutrition.lunch && (
                                <div className="meal-item">
                                  <span className="meal-type">☀️ Lunch:</span>
                                  <span className="meal-desc">{day.nutrition.lunch}</span>
                                </div>
                              )}
                              {day.nutrition.dinner && (
                                <div className="meal-item">
                                  <span className="meal-type">🌙 Dinner:</span>
                                  <span className="meal-desc">{day.nutrition.dinner}</span>
                                </div>
                              )}
                              {day.nutrition.snack && (
                                <div className="meal-item">
                                  <span className="meal-type">🍎 Snack:</span>
                                  <span className="meal-desc">{day.nutrition.snack}</span>
                                </div>
                              )}
                              {day.nutrition.daily_calories_target && (
                                <div className="calorie-target">
                                  <span>🔥 Target: <strong>{day.nutrition.daily_calories_target}</strong></span>
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      </div>

                      {/* Daily Notes */}
                      {day.daily_notes && (
                        <div className="daily-notes">
                          💡 <strong>Tip / Notes:</strong> {day.daily_notes}
                        </div>
                      )}
                    </div>
                  ))}
              </div>
            </div>
          )}

          {/* ── Stage 6: Conversational Plan Modification Section ── */}
          <section className="modify-card">
            <h2 className="section-title">💬 Modify Your Plan</h2>
            <p className="input-hint">
              Tell FitGenie what you want to change in plain English. For example: <em>"Make Wednesday's workout only 20 minutes."</em>, <em>"Replace paneer with tofu on Tuesday."</em>, or <em>"I only have bodyweight exercises for Friday."</em>
            </p>

            <form onSubmit={handleModify}>
              <textarea
                className="input-textarea modify-textarea"
                rows="3"
                placeholder={'e.g. "Make Wednesday\'s workout only 20 minutes."'}
                value={modifyInput}
                onChange={(e) => {
                  setModifyInput(e.target.value);
                  if (modifyError) setModifyError(null);
                  if (modifySuccess) setModifySuccess(null);
                }}
                disabled={modifyLoading || loading}
              />

              <div className="form-actions">
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={modifyLoading || loading || backendStatus === "offline"}
                >
                  {modifyLoading ? "Updating your personalized plan..." : "Modify Plan ⚡"}
                </button>

                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => {
                    setModifyInput("Make Wednesday's workout only 20 minutes.");
                    if (modifyError) setModifyError(null);
                    if (modifySuccess) setModifySuccess(null);
                  }}
                  disabled={modifyLoading || loading}
                >
                  Example: 20-min Wednesday
                </button>
              </div>
            </form>

            {/* Modification Loading State */}
            {modifyLoading && (
              <div className="loading-banner">
                <div className="spinner"></div>
                <div className="loading-text">
                  <strong>Updating your personalized plan...</strong>
                  <p>Applying adjustments to the requested days while preserving your existing routine.</p>
                </div>
              </div>
            )}

            {/* Modification Success State */}
            {modifySuccess && (
              <div className="success-banner" role="status">
                <span className="success-icon">✅</span>
                <span>{modifySuccess}</span>
              </div>
            )}

            {/* Modification Error State */}
            {modifyError && (
              <div className="error-banner" role="alert">
                <span className="error-icon">⚠️</span>
                <span>{modifyError}</span>
              </div>
            )}
          </section>
        </section>
      )}

      {/* ── Disclaimer ───────────────────────────────────────── */}
      <Disclaimer />
    </div>
  );
}

export default HomePage;
