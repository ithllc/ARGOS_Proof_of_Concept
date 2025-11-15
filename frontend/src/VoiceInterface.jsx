import React, { useState } from "react";

const VoiceInterface = () => {
  const [query, setQuery] = useState("");

  const submit = async () => {
    // Call backend to decompose and kick-off tasks
    await fetch("/api/decompose", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query }),
    });
    setQuery("");
  };

  return (
    <div>
      <h3>Voice / Text</h3>
      <textarea value={query} onChange={(e) => setQuery(e.target.value)} rows={4} cols={60} />
      <div>
        <button onClick={submit}>Run</button>
      </div>
    </div>
  );
};

export default VoiceInterface;
