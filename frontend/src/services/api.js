/**
 * api.js — FitGenie AI API Service
 *
 * All HTTP calls to the FastAPI backend go through this file.
 * The base URL is read from the .env file (REACT_APP_API_URL).
 */

import axios from "axios";

// Base URL loaded from .env — defaults to localhost:8000 in development
const API_BASE_URL = process.env.REACT_APP_API_URL || "http://localhost:8000";

// Axios instance with shared configuration
// Timeout is 90 seconds — Gemini plan generation/modification can take 20-40 seconds
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 90000,
});

// ─── Health ────────────────────────────────────────────────────────────────

/**
 * Check whether the FastAPI backend is reachable.
 * @returns {Promise<{status: string, message: string, version: string}>}
 */
export const checkHealth = async () => {
  const response = await apiClient.get("/api/health");
  return response.data;
};

// ─── Sessions ─────────────────────────────────────────────────────────────

/**
 * Retrieve a saved session (including its latest plan) by session ID.
 * @param {string} sessionId
 * @returns {Promise<object>} Session object with embedded plan
 */
export const getSession = async (sessionId) => {
  const response = await apiClient.get(`/api/sessions/${sessionId}`);
  return response.data;
};

/**
 * Retrieve the most recently saved plan for a session.
 * @param {string} sessionId
 */
export const getLatestPlan = async (sessionId) => {
  const response = await apiClient.get(`/api/sessions/${sessionId}/plan`);
  return response.data;
};

// ─── Plan Generation ───────────────────────────────────────────────────────

/**
 * Send a natural-language fitness description and receive:
 *   - extracted profile
 *   - 7-day fitness + nutrition plan
 *   - session_id and plan_id for retrieval
 *
 * Calls POST /api/plans/generate
 *
 * @param {string} userInput - Natural language fitness profile description
 * @returns {Promise<{session_id: string, plan_id: string, profile: object, plan: object}>}
 */
export const generatePlan = async (userInput) => {
  const response = await apiClient.post("/api/plans/generate", {
    user_input: userInput,
  });
  return response.data;
};

/**
 * Send a conversational modification request for an existing plan.
 *
 * Calls POST /api/plans/{plan_id}/modify
 *
 * @param {string} planId      - ID of the plan to modify
 * @param {string} userRequest - The user's modification request (e.g. "Make Wednesday's workout only 20 minutes.")
 * @param {string|null} currentDay - Optional day of week (e.g. "Sunday") to resolve 'today'
 * @returns {Promise<{session_id: string, plan_id: string, profile: object, plan: object}>}
 */
export const modifyPlan = async (planId, userRequest, currentDay = null) => {
  const payload = { user_request: userRequest };
  if (currentDay) {
    payload.current_day = currentDay;
  }
  const response = await apiClient.post(`/api/plans/${planId}/modify`, payload);
  return response.data;
};

// ─── Real-Time AI Coach Chat (Stage 7 Fix) ───────────────────────────────

/**
 * Ask the real-time aware FitGenie AI Coach an informational or diet/workout question.
 * Uses current date/time context and existing plan without modifying or persisting anything.
 *
 * Calls POST /api/coach/chat
 *
 * @param {object} payload - { user_request, current_date, current_day, current_time, today_plan, tomorrow_plan, profile }
 * @returns {Promise<{message: string}>}
 */
export const askCoach = async (payload) => {
  const response = await apiClient.post("/api/coach/chat", payload);
  return response.data;
};

// ─── Substitution (Stage 7) ───────────────────────────────────────────────

/**
 * Request a substitution for a specific exercise or food item.
 * @param {string} itemType      - "exercise" or "food"
 * @param {string} itemName      - The item to replace (e.g., "squats", "oats")
 * @param {object} userProfile
 * @param {string} sessionId
 */
export const substituteItem = async (itemType, itemName, userProfile, sessionId) => {
  // TODO: implement in Stage 7
  throw new Error("substituteItem — not yet implemented (Stage 7)");
};
