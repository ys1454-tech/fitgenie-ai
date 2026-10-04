/**
 * Disclaimer.jsx — Responsible AI and wellness disclaimer component.
 * Displayed prominently on the home page and plan page.
 */

import React from "react";

function Disclaimer() {
  return (
    <div className="disclaimer">
      <p>
        ⚕️ <strong>Medical Disclaimer:</strong> FitGenie AI generates plans for
        general wellness and educational purposes only. Always consult a qualified
        healthcare provider, doctor, or certified fitness professional before
        starting any new exercise or nutrition program.
      </p>
    </div>
  );
}

export default Disclaimer;
