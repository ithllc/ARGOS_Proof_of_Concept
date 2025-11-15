import React from "react";
import ReactDOM from "react-dom/client";
import Dashboard from './Dashboard';
import { CopilotKit } from "@copilotkit/react-core";
import { CopilotPopup } from "@copilotkit/react-ui";
import "@copilotkit/react-ui/styles.css";

const App = () => {
  return (
    <CopilotKit url="/api/copilotkit">
      <Dashboard />
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
