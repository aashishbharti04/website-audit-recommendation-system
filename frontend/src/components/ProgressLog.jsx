import React, { useEffect, useRef } from "react";

export default function ProgressLog({ events, pct, status }) {
  const endRef = useRef(null);
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [events]);

  if (!events.length) return null;

  return (
    <div className="card">
      <div className="proghead">
        <h2>Live progress</h2>
        <span className={`status ${status}`}>{status}</span>
      </div>
      <div className="bar"><div className="fill" style={{ width: `${pct}%` }} /></div>
      <div className="log">
        {events.map((e, i) => (
          <div key={i} className={`logline ${e.status}`}>
            <span className="dot" />
            <span>{e.message}</span>
          </div>
        ))}
        <div ref={endRef} />
      </div>
    </div>
  );
}
