/**
 * HomePage.jsx — FitGenie AI Professional Fitness Dashboard & Conversational Coach.
 *
 * Implements Stage 7:
 *  1. Initial Profile Input with natural language generation
 *  2. Personalized Hero Section with extracted user profile chips
 *  3. Interactive 7-Day Weekly Workout Schedule (live updates on modification)
 *  4. Today's / Selected Day's Workout breakdown with exercises, sets, reps & coaching cues
 *  5. Daily Nutrition Planner (breakfast, lunch, dinner, snack, calorie targets)
 *  6. Conversational AI Coach with message history, quick-action chips, and modification summaries
 *  7. Responsible AI wellness disclaimer
 */

import React, { useState, useEffect, useRef } from "react";
import Disclaimer from "../components/Disclaimer";
import { checkHealth, generatePlan, modifyPlan, askCoach } from "../services/api";

const SAMPLE_INPUT =
  "I am 21 years old, male, 175 cm tall, 70 kg. My goal is weight loss. I am a beginner. I can exercise for 45 minutes per day. I have dumbbells at home. I prefer Indian vegetarian food. My budget is 3000 rupees per month.";

const DAY_NAMES = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];

/**
 * Returns fresh real-time date/time context and matches today's and tomorrow's
 * plan days dynamically from the user's generated 7-day plan.
 */
function getRealtimeContext(daysList = []) {
  const now = new Date();
  const dayIndex = now.getDay(); // 0 = Sunday, 1 = Monday, ..., 6 = Saturday
  const currentDayName = DAY_NAMES[dayIndex];

  // ISO date: YYYY-MM-DD
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const dateNum = String(now.getDate()).padStart(2, "0");
  const currentDate = `${year}-${month}-${dateNum}`;

  // Time: HH:MM and 12-hour format
  const hours24 = String(now.getHours()).padStart(2, "0");
  const minutes = String(now.getMinutes()).padStart(2, "0");
  const time12 = now.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
  const currentTime = `${hours24}:${minutes} (${time12})`;

  // Find today's plan by matching day_name
  let todayPlan = daysList.find(
    (d) => d.day_name && d.day_name.toLowerCase() === currentDayName.toLowerCase()
  );

  // Fallback to day mapping if day_name doesn't match:
  // Sunday -> Day 7, Monday -> Day 1, etc.
  if (!todayPlan && daysList.length > 0) {
    const targetDayNumber = dayIndex === 0 ? 7 : dayIndex;
    todayPlan =
      daysList.find((d) => d.day_number === targetDayNumber) ||
      (dayIndex === 0 ? daysList[6] : daysList[dayIndex - 1]) ||
      daysList[0];
  }

  // Calculate tomorrow dynamically (handles Sunday -> Monday wrap-around)
  const tomorrowDayIndex = (dayIndex + 1) % 7;
  const tomorrowDayName = DAY_NAMES[tomorrowDayIndex];

  let tomorrowPlan = daysList.find(
    (d) => d.day_name && d.day_name.toLowerCase() === tomorrowDayName.toLowerCase()
  );

  if (!tomorrowPlan && daysList.length > 0) {
    const targetTomorrowDayNumber = tomorrowDayIndex === 0 ? 7 : tomorrowDayIndex;
    tomorrowPlan =
      daysList.find((d) => d.day_number === targetTomorrowDayNumber) ||
      (tomorrowDayIndex === 0 ? daysList[6] : daysList[tomorrowDayIndex - 1]) ||
      daysList[0];
  }

  const currentDayIndexInList = daysList.indexOf(todayPlan);

  return {
    now,
    currentDate,
    currentDay: currentDayName,
    currentTime,
    todayPlan: todayPlan || {},
    tomorrowPlan: tomorrowPlan || {},
    currentDayIndexInList: currentDayIndexInList >= 0 ? currentDayIndexInList : 0,
  };
}

/**
 * Deterministic intent classifier.
 * Distinguishes between:
 *  - PLAN MODIFICATION (verbs like make, change, replace, reduce, swap, shorten, etc.)
 *  - INFORMATIONAL QUESTIONS (what should I eat, what is my breakfast, what am I eating tomorrow, etc.)
 */
function isModificationRequest(text) {
  const lower = text.toLowerCase().trim();

  // Food alternative / unavailable food queries are informational coach questions, NOT plan modifications
  const isFoodAlternative =
    lower.includes("what can i eat") ||
    lower.includes("what can i have") ||
    lower.includes("what to eat") ||
    lower.includes("what should i eat") ||
    lower.includes("eat instead") ||
    lower.includes("have instead") ||
    lower.includes("instead of") ||
    lower.includes("alternative") ||
    lower.includes("don't have food") ||
    lower.includes("dont have food") ||
    lower.includes("don't have lunch") ||
    lower.includes("dont have lunch") ||
    lower.includes("don't have breakfast") ||
    lower.includes("dont have breakfast") ||
    lower.includes("don't have dinner") ||
    lower.includes("dont have dinner") ||
    lower.includes("don't have snack") ||
    lower.includes("dont have snack") ||
    lower.includes("don't have the food") ||
    lower.includes("dont have the food") ||
    lower.includes("don't have this food") ||
    lower.includes("dont have this food") ||
    lower.includes("don't have my planned") ||
    lower.includes("dont have my planned") ||
    lower.includes("don't have anything cooked") ||
    lower.includes("dont have anything cooked") ||
    lower.includes("nothing cooked") ||
    lower.includes("can't get this food") ||
    lower.includes("cant get this food") ||
    lower.includes("don't have these ingredients") ||
    lower.includes("dont have these ingredients") ||
    lower.includes("don't have the ingredients") ||
    lower.includes("dont have the ingredients") ||
    ((lower.includes("don't have") || lower.includes("dont have")) &&
      (lower.includes("eat") || lower.includes("food") || lower.includes("meal") || lower.includes("cooked") || lower.includes("plan") || lower.includes("lunch") || lower.includes("breakfast") || lower.includes("dinner") || lower.includes("snack") || lower.includes("diet")) &&
      !lower.includes("dumbbell") && !lower.includes("equipment") && !lower.includes("workout") && !lower.includes("exercise"));

  if (isFoodAlternative && !lower.includes("change my plan") && !lower.includes("update my plan") && !lower.includes("modify my plan")) {
    return false;
  }

  // Explicit modification keywords
  const modificationKeywords = [
    "make", "change", "replace", "reduce", "swap", "substitute",
    "shorten", "adjust", "switch", "remove", "delete", "decrease",
    "increase", "cut down", "drop", "don't have", "do not have",
    "dont have", "instead of", "update my plan", "modify my plan"
  ];

  // Specific informational phrases that must NEVER be treated as plan modifications
  if (
    lower.includes("what should i eat") ||
    lower.includes("what to eat") ||
    lower.includes("what is in my diet") ||
    lower.includes("what is my diet") ||
    lower.includes("what am i eating") ||
    lower.includes("what is my breakfast") ||
    lower.includes("what is my lunch") ||
    lower.includes("what is my dinner") ||
    lower.includes("what is my snack") ||
    lower.includes("what should i eat after") ||
    lower.includes("what is today's workout") ||
    lower.includes("what do i have today") ||
    lower.includes("i want to eat now") ||
    lower.includes("what am i having") ||
    lower.includes("what can i eat") ||
    lower.startsWith("what is my") ||
    lower.startsWith("how tall") ||
    lower.startsWith("how much do i weigh") ||
    lower.startsWith("what do i weigh") ||
    lower.startsWith("how old") ||
    lower.startsWith("what equipment") ||
    lower.startsWith("why is") ||
    lower.startsWith("how long is")
  ) {
    return false;
  }

  // Conversational & Question starters
  const nonModStarters = [
    "what", "when", "how", "tell me", "show me", "can i", "should i",
    "is today", "which", "do i have", "where", "why", "who",
    "hello", "hi", "hey", "good morning", "good afternoon", "good evening",
    "thanks", "thank you"
  ];

  const startsWithNonMod = nonModStarters.some((q) => lower.startsWith(q));
  const hasModKeyword = modificationKeywords.some((k) => lower.includes(k));

  if (startsWithNonMod && !hasModKeyword) {
    return false;
  }

  return hasModKeyword;
}

function getGreeting() {
  const hr = new Date().getHours();
  if (hr < 12) return "Good morning";
  if (hr < 17) return "Good afternoon";
  return "Good evening";
}

function HomePage() {
  // Backend connectivity status
  const [backendStatus, setBackendStatus] = useState("checking"); // "checking" | "online" | "offline"

  // Initial Plan Generation State
  const [userInput, setUserInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Active Plan Result: { session_id, plan_id, profile, plan }
  const [result, setResult] = useState(null);

  // Interactive Day Selection (0 to 6)
  const [selectedDayIndex, setSelectedDayIndex] = useState(0);

  // Conversational AI Coach State
  const [chatMessages, setChatMessages] = useState([]);
  const [chatInput, setChatInput] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const [chatError, setChatError] = useState(null);
  const [chatSuccess, setChatSuccess] = useState(null);

  const chatEndRef = useRef(null);

  // Check health on mount
  useEffect(() => {
    checkHealth()
      .then(() => setBackendStatus("online"))
      .catch(() => setBackendStatus("offline"));
  }, []);

  // Initialize chat when a plan is generated
  useEffect(() => {
    if (result && result.plan) {
      if (chatMessages.length === 0) {
        const rt = getRealtimeContext(result.plan?.days || []);
        setChatMessages([
          {
            id: 1,
            role: "assistant",
            text: `👋 Hi! Your personalized 7-day fitness and nutrition plan is active. Today is ${rt.currentDay}. Ask me what to eat now, what today's workout is, or request any adjustments!`,
            time: "Just now",
          },
        ]);
      }
    }
  }, [result]);

  // Auto-scroll chat to latest message
  useEffect(() => {
    if (chatEndRef.current) {
      chatEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [chatMessages, chatLoading]);

  // Generate Plan Handler
  const handleGenerate = async (e) => {
    if (e) e.preventDefault();
    const trimmed = userInput.trim();
    if (!trimmed) {
      setError("Please enter your fitness information before generating a plan.");
      return;
    }

    setLoading(true);
    setError(null);
    setChatError(null);
    setChatSuccess(null);

    try {
      const data = await generatePlan(trimmed);
      setResult(data);

      // Select today's day dynamically instead of assuming Monday (Day 1)
      const rt = getRealtimeContext(data.plan?.days || []);
      setSelectedDayIndex(rt.currentDayIndexInList >= 0 ? rt.currentDayIndexInList : 0);

      setChatMessages([
        {
          id: Date.now(),
          role: "assistant",
          text: `👋 Welcome! Your personalized 7-day plan "${data.plan?.plan_title || "Fitness & Nutrition"}" is ready. Today is ${rt.currentDay}. Tell me what changes you'd like to make or ask what to eat now!`,
          time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        },
      ]);
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

  // Conversational AI Coach / Modification Handler
  const executeChatMessage = async (requestText, forceModification = false) => {
    const trimmed = requestText.trim();
    if (!trimmed) {
      setChatError("Please enter a question or modification request.");
      return;
    }

    if (!result || !result.plan_id) {
      setChatError("No active plan found. Please generate a plan first.");
      return;
    }

    // Add user message to chat immediately
    const userMsgId = Date.now();
    const userMsg = {
      id: userMsgId,
      role: "user",
      text: trimmed,
      time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setChatMessages((prev) => [...prev, userMsg]);
    setChatInput("");
    setChatLoading(true);
    setChatError(null);
    setChatSuccess(null);

    // Compute fresh real-time date/time context for EVERY chat request
    const daysList = result?.plan?.days || [];
    const rt = getRealtimeContext(daysList);

    const isMod = forceModification || isModificationRequest(trimmed);

    if (isMod) {
      // ─── Plan Modification Workflow ───────────────────────────────
      try {
        const updatedData = await modifyPlan(result.plan_id, trimmed, rt.currentDay);

        // Update the active plan in dashboard state immediately
        setResult(updatedData);

        // Extract conversational response from backend modification_summary
        const summary =
          updatedData.plan?.modification_summary ||
          "I have updated your plan according to your request.";

        const assistantMsg = {
          id: Date.now() + 1,
          role: "assistant",
          text: summary,
          time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        };

        setChatMessages((prev) => [...prev, assistantMsg]);
        setChatSuccess("Plan updated successfully.");
      } catch (err) {
        console.error("Plan modification error:", err);
        const detail =
          err.response?.data?.detail ||
          err.message ||
          "Unable to update your plan right now. Please try again.";

        const errorAssistantMsg = {
          id: Date.now() + 1,
          role: "assistant",
          text: `⚠️ Sorry, I encountered an issue updating your plan: ${detail}`,
          time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
          isError: true,
        };

        setChatMessages((prev) => [...prev, errorAssistantMsg]);
        setChatError(`Unable to modify plan: ${detail}`);
      } finally {
        setChatLoading(false);
      }
    } else {
      // ─── Informational / Real-Time Date-Aware AI Coach ───────────
      try {
        const coachPayload = {
          user_request: trimmed,
          current_date: rt.currentDate,
          current_day: rt.currentDay,
          current_time: rt.currentTime,
          today_plan: rt.todayPlan,
          tomorrow_plan: rt.tomorrowPlan,
          profile: result.profile || {},
        };

        const coachResponse = await askCoach(coachPayload);

        const assistantMsg = {
          id: Date.now() + 1,
          role: "assistant",
          text: coachResponse.message,
          time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        };

        setChatMessages((prev) => [...prev, assistantMsg]);
      } catch (err) {
        console.error("AI Coach query error:", err);
        const detail =
          err.response?.data?.detail ||
          err.message ||
          "FitGenie AI Coach could not answer right now. Please try again.";

        const errorAssistantMsg = {
          id: Date.now() + 1,
          role: "assistant",
          text: `⚠️ ${detail}`,
          time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
          isError: true,
        };

        setChatMessages((prev) => [...prev, errorAssistantMsg]);
        setChatError(`AI Coach error: ${detail}`);
      } finally {
        setChatLoading(false);
      }
    }
  };

  const handleChatSubmit = (e) => {
    if (e) e.preventDefault();
    executeChatMessage(chatInput, false);
  };

  const handleUseSample = () => {
    setUserInput(SAMPLE_INPUT);
    setError(null);
  };

  const handleReset = () => {
    setResult(null);
    setError(null);
    setChatError(null);
    setChatSuccess(null);
    setChatMessages([]);
    setChatInput("");
    setSelectedDayIndex(0);
  };

  // Current active day for details view
  const daysList = result?.plan?.days || [];
  const currentDay = daysList[selectedDayIndex] || daysList[0] || null;

  return (
    <div className="dashboard-root">
      {/* ── Initial Generation Card (Shown if no plan generated yet) ── */}
      {!result && (
        <section className="welcome-setup-card">
          <div className="setup-hero">
            <div className="hero-badge">
              <span className="badge-sparkle">✨</span> Generative AI Fitness &amp; Nutrition
            </div>
            <h1 className="hero-main-title">
              Craft Your Personalized <span className="gradient-text">Fitness Routine</span>
            </h1>
            <p className="hero-desc">
              Describe your goals, schedule, equipment, dietary preferences, and budget in natural language.
              FitGenie AI will engineer a comprehensive 7-day workout and meal schedule tailored specifically to you.
            </p>

            {/* Backend Connectivity Badge */}
            <div className="status-badge-container">
              {backendStatus === "checking" && (
                <span className="badge badge-checking">⏳ Connecting to backend…</span>
              )}
              {backendStatus === "online" && (
                <span className="badge badge-online">✅ Backend Online • FastAPI &amp; Gemini</span>
              )}
              {backendStatus === "offline" && (
                <span className="badge badge-offline">
                  ⚠️ Backend offline — start FastAPI server on port 8000
                </span>
              )}
            </div>
          </div>

          <form className="generator-form" onSubmit={handleGenerate}>
            <div className="textarea-wrapper">
              <label className="form-label" htmlFor="user-profile-input">
                Tell FitGenie About Yourself
              </label>
              <textarea
                id="user-profile-input"
                className="generator-textarea"
                rows="5"
                placeholder={`e.g. ${SAMPLE_INPUT}`}
                value={userInput}
                onChange={(e) => {
                  setUserInput(e.target.value);
                  if (error) setError(null);
                }}
                disabled={loading}
              />
            </div>

            <div className="form-buttons-row">
              <button
                type="submit"
                className="btn-primary-glow"
                disabled={loading || backendStatus === "offline"}
              >
                {loading ? (
                  <span className="btn-loading-content">
                    <span className="spinner-sm"></span> Generating Your Plan…
                  </span>
                ) : (
                  <span>⚡ Generate My Plan</span>
                )}
              </button>

              <button
                type="button"
                className="btn-secondary-dark"
                onClick={handleUseSample}
                disabled={loading}
              >
                Fill Sample Profile
              </button>
            </div>
          </form>

          {/* Loading Banner */}
          {loading && (
            <div className="generator-loading-card">
              <div className="pulse-spinner"></div>
              <div className="loading-copy">
                <h4>Formulating your 7-day personalized blueprint…</h4>
                <p>Gemini is tailoring exercise sets, rest intervals, and nutrition to match your lifestyle.</p>
              </div>
            </div>
          )}

          {/* Error Banner */}
          {error && (
            <div className="error-card" role="alert">
              <span className="error-symbol">⚠️</span>
              <p>{error}</p>
            </div>
          )}
        </section>
      )}

      {/* ── Active Professional Fitness Dashboard ── */}
      {result && result.plan && (
        <div className="dashboard-layout" id="dashboard">
          {/* ── Personalized Hero Banner ─────────────────────────────── */}
          <section className="personalized-hero">
            <div className="hero-greeting-row">
              <div>
                <span className="hero-subheading">Personalized Fitness Dashboard</span>
                <h1 className="hero-greeting">{getGreeting()} 👋</h1>
                <p className="hero-status-tagline">
                  Your personalized <strong>{result.plan.plan_title || "7-Day Program"}</strong> is active and ready.
                </p>
              </div>

              <div className="hero-actions">
                <button
                  type="button"
                  className="btn-outline-dark btn-sm"
                  onClick={handleReset}
                  title="Start over with a new profile"
                >
                  🔄 New Plan
                </button>
              </div>
            </div>

            {/* Profile Metrics Chips Grid */}
            {result.profile && (
              <div className="profile-chips-grid">
                <div className="profile-chip">
                  <span className="chip-label">Goal</span>
                  <span className="chip-value chip-accent">{result.profile.fitness_goal || "Weight Loss"}</span>
                </div>
                <div className="profile-chip">
                  <span className="chip-label">Level</span>
                  <span className="chip-value">{result.profile.fitness_level || "Beginner"}</span>
                </div>
                <div className="profile-chip">
                  <span className="chip-label">Time</span>
                  <span className="chip-value">{result.profile.available_time ? `${result.profile.available_time} min/day` : "30 min"}</span>
                </div>
                <div className="profile-chip">
                  <span className="chip-label">Equipment</span>
                  <span className="chip-value">{result.profile.equipment || "Bodyweight"}</span>
                </div>
                <div className="profile-chip">
                  <span className="chip-label">Food</span>
                  <span className="chip-value">{result.profile.food_preference || "Standard"}</span>
                </div>
                <div className="profile-chip">
                  <span className="chip-label">Budget</span>
                  <span className="chip-value chip-accent">
                    {result.profile.budget != null ? `₹${result.profile.budget}/mo` : "Standard"}
                  </span>
                </div>
                <div className="profile-chip profile-chip-metrics">
                  <span className="chip-label">Stats</span>
                  <span className="chip-value">
                    {result.profile.age ? `${result.profile.age}y` : ""}
                    {result.profile.gender ? ` • ${result.profile.gender}` : ""}
                    {result.profile.height ? ` • ${result.profile.height}cm` : ""}
                    {result.profile.weight ? ` • ${result.profile.weight}kg` : ""}
                  </span>
                </div>
              </div>
            )}
          </section>

          {/* ── Weekly 7-Day Interactive Schedule ───────────────────── */}
          <section className="weekly-schedule-section" id="schedule">
            <div className="section-header-row">
              <div>
                <h2 className="section-heading">🗓️ Weekly Workout Schedule</h2>
                <p className="section-caption">Click on any day to inspect its full exercise and nutrition breakdown.</p>
              </div>
              {result.plan.modification_summary && (
                <div className="live-update-badge" title="Live update confirmation">
                  <span className="live-pulse"></span> Plan Updated
                </div>
              )}
            </div>

            <div className="schedule-cards-grid">
              {daysList.map((day, idx) => {
                const isSelected = selectedDayIndex === idx;
                const duration = day.workout?.duration_minutes || "—";
                return (
                  <button
                    key={day.day_number || idx}
                    type="button"
                    className={`schedule-day-card ${isSelected ? "schedule-day-card-active" : ""}`}
                    onClick={() => setSelectedDayIndex(idx)}
                  >
                    <div className="day-card-top">
                      <span className="day-tag">Day {day.day_number || idx + 1}</span>
                      <span className="day-time-pill">{duration}m</span>
                    </div>
                    <h3 className="day-title">{day.day_name}</h3>
                    <p className="day-workout-name">{day.workout?.title || "Workout Session"}</p>
                    <div className="day-focus-pill">🎯 {day.workout?.focus_area || "General Fitness"}</div>
                  </button>
                );
              })}
            </div>
          </section>

          {/* ── Main Dashboard 2-Column Grid (Workout/Nutrition + AI Coach) ── */}
          <div className="dashboard-content-grid">
            {/* Left Column: Today's / Selected Day Routine */}
            <div className="left-content-column">
              {/* Today's Workout Card */}
              {currentDay && (
                <section className="dashboard-card today-workout-card" id="workout">
                  <div className="card-top-bar">
                    <div>
                      <span className="badge-highlight">
                        SELECTED DAY • DAY {currentDay.day_number} ({currentDay.day_name})
                      </span>
                      <h2 className="workout-main-title">🏋️ {currentDay.workout?.title || "Workout Routine"}</h2>
                    </div>
                    <div className="workout-meta-pills">
                      <span className="pill-metric">⏱️ {currentDay.workout?.duration_minutes || 30} mins</span>
                      <span className="pill-metric">🎯 {currentDay.workout?.focus_area || "Full Body"}</span>
                    </div>
                  </div>

                  {/* Exercises List */}
                  <div className="exercises-container">
                    <h3 className="sub-heading">Exercises</h3>
                    {currentDay.workout?.exercises && currentDay.workout.exercises.length > 0 ? (
                      <div className="exercises-grid">
                        {currentDay.workout.exercises.map((ex, exIdx) => (
                          <div key={exIdx} className="exercise-row-card">
                            <div className="ex-main-info">
                              <span className="ex-number">{exIdx + 1}</span>
                              <div>
                                <h4 className="ex-title">{ex.name}</h4>
                                {ex.instructions && (
                                  <p className="ex-cue">💡 {ex.instructions}</p>
                                )}
                              </div>
                            </div>
                            <div className="ex-stats">
                              <span className="stat-sets-reps">
                                {ex.sets ? `${ex.sets} sets × ` : ""}
                                {ex.reps_or_duration || "10-12 reps"}
                              </span>
                              {ex.rest_seconds && (
                                <span className="stat-rest">Rest: {ex.rest_seconds}s</span>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="no-data-msg">Rest &amp; recovery day or light mobility exercises.</p>
                    )}
                  </div>

                  {/* Daily Coaching Cue */}
                  {currentDay.daily_notes && (
                    <div className="coaching-notes-box">
                      <span className="notes-icon">💡</span>
                      <div>
                        <strong>Coaching Cue &amp; Notes:</strong>
                        <p>{currentDay.daily_notes}</p>
                      </div>
                    </div>
                  )}
                </section>
              )}

              {/* Nutrition Planner Card */}
              {currentDay && currentDay.nutrition && (
                <section className="dashboard-card nutrition-card" id="nutrition">
                  <div className="card-top-bar">
                    <div>
                      <span className="badge-highlight">NUTRITION BLUEPRINT</span>
                      <h2 className="workout-main-title">🥗 Meals for {currentDay.day_name}</h2>
                    </div>
                    {currentDay.nutrition.daily_calories_target && (
                      <span className="pill-calorie">
                        🔥 Target: <strong>{currentDay.nutrition.daily_calories_target}</strong>
                      </span>
                    )}
                  </div>

                  <div className="meals-grid">
                    {currentDay.nutrition.breakfast && (
                      <div className="meal-box">
                        <div className="meal-box-header">
                          <span className="meal-icon">🌅</span>
                          <h4>Breakfast</h4>
                        </div>
                        <p className="meal-text">{currentDay.nutrition.breakfast}</p>
                      </div>
                    )}

                    {currentDay.nutrition.lunch && (
                      <div className="meal-box">
                        <div className="meal-box-header">
                          <span className="meal-icon">☀️</span>
                          <h4>Lunch</h4>
                        </div>
                        <p className="meal-text">{currentDay.nutrition.lunch}</p>
                      </div>
                    )}

                    {currentDay.nutrition.dinner && (
                      <div className="meal-box">
                        <div className="meal-box-header">
                          <span className="meal-icon">🌙</span>
                          <h4>Dinner</h4>
                        </div>
                        <p className="meal-text">{currentDay.nutrition.dinner}</p>
                      </div>
                    )}

                    {currentDay.nutrition.snack && (
                      <div className="meal-box">
                        <div className="meal-box-header">
                          <span className="meal-icon">🍎</span>
                          <h4>Snack / Shake</h4>
                        </div>
                        <p className="meal-text">{currentDay.nutrition.snack}</p>
                      </div>
                    )}
                  </div>
                </section>
              )}
            </div>

            {/* Right Column: Conversational FitGenie AI Coach Panel */}
            <aside className="right-coach-column" id="ai-coach">
              <div className="coach-panel-card">
                <div className="coach-header">
                  <div className="coach-identity">
                    <div className="coach-avatar">⚡</div>
                    <div>
                      <h3 className="coach-name">FitGenie AI Coach</h3>
                      <span className="coach-status">
                        <span className="pulse-dot"></span> Online • Gemini
                      </span>
                    </div>
                  </div>
                  <span className="coach-badge">Interactive</span>
                </div>

                <p className="coach-tagline">
                  Tell me how you'd like to adjust your plan. Ask to reduce time, swap exercises, change meals, or lower intensity.
                </p>

                {/* Chat Message Stream */}
                <div className="chat-messages-container">
                  {chatMessages.map((msg) => (
                    <div
                      key={msg.id}
                      className={`chat-bubble-row ${msg.role === "user" ? "bubble-row-user" : "bubble-row-assistant"}`}
                    >
                      {msg.role === "assistant" && <div className="chat-avatar-mini">⚡</div>}
                      <div className={`chat-bubble ${msg.role === "user" ? "bubble-user" : "bubble-assistant"} ${msg.isError ? "bubble-error" : ""}`}>
                        <div className="bubble-author">
                          {msg.role === "assistant" ? "FitGenie" : "You"}
                          <span className="bubble-time">{msg.time}</span>
                        </div>
                        <div className="bubble-text">{msg.text}</div>
                      </div>
                      {msg.role === "user" && <div className="chat-avatar-mini user-avatar-mini">👤</div>}
                    </div>
                  ))}

                  {/* Typing / Loading Indicator in Chat */}
                  {chatLoading && (
                    <div className="chat-bubble-row bubble-row-assistant">
                      <div className="chat-avatar-mini">⚡</div>
                      <div className="chat-bubble bubble-assistant bubble-typing">
                        <div className="typing-dots">
                          <span></span>
                          <span></span>
                          <span></span>
                        </div>
                        <span className="typing-label">FitGenie is responding…</span>
                      </div>
                    </div>
                  )}

                  <div ref={chatEndRef} />
                </div>

                {/* Quick Action Chips */}
                <div className="quick-actions-wrapper">
                  <span className="quick-label">💬 Ask Coach:</span>
                  <div className="quick-buttons-row">
                    <button
                      type="button"
                      className="quick-chip"
                      disabled={chatLoading}
                      onClick={() => executeChatMessage("What should I eat now?", false)}
                    >
                      🥗 What to eat now?
                    </button>
                    <button
                      type="button"
                      className="quick-chip"
                      disabled={chatLoading}
                      onClick={() => executeChatMessage("What is my workout today?", false)}
                    >
                      🏋️ Today's workout?
                    </button>
                    <button
                      type="button"
                      className="quick-chip"
                      disabled={chatLoading}
                      onClick={() => executeChatMessage("What am I eating tomorrow?", false)}
                    >
                      🌅 Tomorrow's meals?
                    </button>
                  </div>
                </div>

                <div className="quick-actions-wrapper" style={{ marginTop: "0.25rem" }}>
                  <span className="quick-label">⚡ Quick Adjustments:</span>
                  <div className="quick-buttons-row">
                    <button
                      type="button"
                      className="quick-chip"
                      disabled={chatLoading}
                      onClick={() => executeChatMessage("Make Wednesday's workout only 20 minutes.", true)}
                    >
                      Reduce Wednesday to 20m
                    </button>
                    <button
                      type="button"
                      className="quick-chip"
                      disabled={chatLoading}
                      onClick={() => executeChatMessage("I don't have dumbbells on Friday. Replace the exercises with bodyweight exercises.", true)}
                    >
                      Friday Bodyweight Only
                    </button>
                    <button
                      type="button"
                      className="quick-chip"
                      disabled={chatLoading}
                      onClick={() => executeChatMessage("Make today's workout easier.", true)}
                    >
                      Make today easier
                    </button>
                    <button
                      type="button"
                      className="quick-chip"
                      disabled={chatLoading}
                      onClick={() => executeChatMessage("Change Saturday's breakfast.", true)}
                    >
                      Change Saturday Breakfast
                    </button>
                  </div>
                </div>

                {/* Chat Input Bar */}
                <form className="chat-input-bar" onSubmit={handleChatSubmit}>
                  <input
                    type="text"
                    className="chat-text-input"
                    placeholder="Tell me what you'd like to change..."
                    value={chatInput}
                    onChange={(e) => {
                      setChatInput(e.target.value);
                      if (chatError) setChatError(null);
                    }}
                    disabled={chatLoading}
                  />
                  <button
                    type="submit"
                    className="chat-send-btn"
                    disabled={chatLoading || !chatInput.trim()}
                    title="Send modification request"
                  >
                    {chatLoading ? "…" : "Send ➔"}
                  </button>
                </form>

                {/* Chat Feedback Banners */}
                {chatSuccess && (
                  <div className="chat-feedback chat-feedback-success">
                    ✅ {chatSuccess}
                  </div>
                )}
                {chatError && (
                  <div className="chat-feedback chat-feedback-error">
                    ⚠️ {chatError}
                  </div>
                )}
              </div>
            </aside>
          </div>
        </div>
      )}

      {/* ── Medical / Wellness Disclaimer ─────────────────────── */}
      <Disclaimer />
    </div>
  );
}

export default HomePage;
