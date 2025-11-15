import React from "react";
import ReactDOM from "react-dom/client";
import { CopilotKit } from "@copilotkit/react-core";
import { CopilotPopup } from "@copilotkit/react-ui";
import "@copilotkit/react-ui/styles.css";

const App = () => {
  return (
    <CopilotKit url="http://localhost:8000/copilotkit">
      <div>
        <h1>Mini-ARGOS POC</h1>
        <p>Welcome to the Proof of Concept for Mini-ARGOS.</p>
      </div>
      <CopilotPopup />
    </CopilotKit>
  );
};

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
