import { useState, useEffect, useRef } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import "./App.css";

const isTauri = () => !!(window as any).__TAURI_INTERNALS__;

type Style = "hyper" | "reel" | "vlog" | "cinematic";

const STYLES: { id: Style; emoji: string; name: string; desc: string }[] = [
  { id: "hyper",     emoji: "\u26A1", name: "Hyper",     desc: "0.5\u20131s cuts" },
  { id: "reel",      emoji: "\uD83C\uDFAF", name: "Reel",      desc: "1\u20132s cuts" },
  { id: "vlog",      emoji: "\uD83C\uDFA5", name: "Vlog",      desc: "4\u20136s cuts" },
  { id: "cinematic", emoji: "\uD83C\uDFAC", name: "Cinematic", desc: "8s+ cuts" },
];

function colorClass(line: string) {
  const l = line.toLowerCase();
  if (l.includes("error") || l.includes("critical") || l.includes("failed")) return "line-error";
  if (l.includes("success") || l.includes("complete") || l.includes("done")) return "line-success";
  if (l.startsWith("[") || l.includes("phase") || l.includes("===")) return "line-info";
  return "";
}

export default function App() {
  const [paths, setPaths] = useState({
    aroll: "E:\\Zoe\\SKE Ent\\Video\\A roll",
    broll: "E:\\Zoe\\SKE Ent\\Video\\B Roll",
    fpv:   "E:\\Zoe\\SKE Ent\\Video\\Drone Footage",
    music: "",
  });

  const [config, setConfig] = useState<{ style: Style; mix_ratio: number; max_duration: number }>({
    style: "hyper",
    mix_ratio: 50,
    max_duration: 30,
  });

  const [logs, setLogs] = useState<string[]>([]);
  const [isEditing, setIsEditing] = useState(false);
  const [editComplete, setEditComplete] = useState(false);
  const [progress, setProgress] = useState(0);
  const [editCount, setEditCount] = useState(0);
  const logEndRef = useRef<HTMLDivElement>(null);

  // Stream logs from Rust via Tauri events
  useEffect(() => {
    const unlisten = listen<string>("log", (event) => {
      const ts = new Date().toLocaleTimeString();
      setLogs((prev) => [...prev, `[${ts}] ${event.payload}`]);
      const msg = event.payload.toLowerCase();
      if (msg.includes("transcribing"))                             setProgress(20);
      if (msg.includes("motion analysis"))                          setProgress(35);
      if (msg.includes("downloading music"))                        setProgress(50);
      if (msg.includes("building") || msg.includes("phase 1"))     setProgress(55);
      if (msg.includes("phase 2") || msg.includes("exporting"))    setProgress(65);
      if (msg.includes("phase 3") || msg.includes("injecting"))    setProgress(75);
      if (msg.includes("phase 4") || msg.includes("re-importing")) setProgress(88);
      if (msg.includes("phase 5") || msg.includes("vfx"))          setProgress(95);
      if (msg.includes("finished successfully")) {
        setProgress(100);
        setIsEditing(false);
        setEditComplete(true);
      }
    });
    return () => { unlisten.then((u) => u()); };
  }, []);

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  async function pickDirectory(key: "aroll" | "broll" | "fpv") {
    if (!isTauri()) return;
    const selected = await invoke<string | null>("select_directory");
    if (selected) setPaths((prev) => ({ ...prev, [key]: selected }));
  }

  async function pickFile() {
    if (!isTauri()) return;
    const selected = await invoke<string | null>("select_file");
    if (selected) setPaths((prev) => ({ ...prev, music: selected }));
  }

  async function startEdit() {
    if (!isTauri()) {
      setLogs(["ERROR: Not running inside the native app. Open the DaVinci Auto-Editor window."]);
      return;
    }
    setIsEditing(true);
    setEditComplete(false);
    setProgress(5);
    setLogs(["Initializing DaVinci Resolve AI Engine..."]);
    try {
      await invoke("start_edit", {
        aRollPath:   paths.aroll,
        bRollPath:   paths.broll,
        fpvPath:     paths.fpv,
        musicPath:   paths.music,
        style:       config.style,
        mixRatio:    config.mix_ratio,
        maxDuration: config.max_duration,
      });
    } catch (e) {
      setLogs((prev) => [...prev, `Critical Error: ${e}`]);
      setIsEditing(false);
    }
  }

  async function rerollEdit() {
    setEditCount((c) => c + 1);
    setLogs([`Rerolling edit #${editCount + 2}...`]);
    await startEdit();
  }

  const canRun = !isEditing && !!(paths.aroll || paths.broll || paths.fpv);

  return (
    <div className="app">
      {/* Header */}
      <header className="header">
        <div className="header-icon">{"\uD83C\uDFAC"}</div>
        <div className="header-text">
          <h1>DaVinci Auto-Editor AI</h1>
          <p>Automated Beat-Synced Cinema Engine</p>
        </div>
        <span className="header-badge">AI-POWERED</span>
      </header>

      <div className="main-grid">
        {/* Footage Sources */}
        <div className="card">
          <div className="card-title"><span className="dot" />Footage Sources</div>
          <div className="folder-pickers">
            {(["aroll", "broll", "fpv"] as const).map((key) => {
              const labels = { aroll: "A-Roll", broll: "B-Roll", fpv: "FPV" };
              const ph = { aroll: "Select A-Roll folder\u2026", broll: "Select B-Roll folder\u2026", fpv: "Select FPV / Drone folder\u2026" };
              return (
                <div className="folder-row" key={key}>
                  <span className="folder-label">{labels[key]}</span>
                  <div className={`folder-input-wrap ${paths[key] ? "has-value" : ""}`}
                    onClick={() => pickDirectory(key)} title={paths[key] || ph[key]}>
                    <span className="folder-icon">{"\uD83D\uDCC1"}</span>
                    <span className={`folder-path ${paths[key] ? "" : "placeholder"}`}>{paths[key] || ph[key]}</span>
                    {paths[key] && (
                      <button className="clear-btn"
                        onClick={(e) => { e.stopPropagation(); setPaths((p) => ({ ...p, [key]: "" })); }}>{"\u2715"}</button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Edit Style */}
        <div className="card">
          <div className="card-title"><span className="dot" />Edit Style</div>
          <div className="style-buttons">
            {STYLES.map((s) => (
              <button key={s.id} className={`style-btn ${config.style === s.id ? "active" : ""}`}
                onClick={() => setConfig((c) => ({ ...c, style: s.id }))}>
                <span className="style-emoji">{s.emoji}</span>
                <span className="style-name">{s.name}</span>
                <span className="style-desc">{s.desc}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Parameters */}
        <div className="card">
          <div className="card-title"><span className="dot" />Parameters</div>
          <div className="param-row">
            <div className="param-label"><span>Max Duration</span><span className="param-value">{config.max_duration}s</span></div>
            <input type="range" min={10} max={600} step={5} value={config.max_duration}
              onChange={(e) => setConfig((c) => ({ ...c, max_duration: +e.target.value }))} />
          </div>
          <div className="param-row">
            <div className="param-label"><span>A-Roll / B-Roll Mix</span><span className="param-value">{config.mix_ratio}% / {100 - config.mix_ratio}%</span></div>
            <input type="range" min={10} max={90} step={5} value={config.mix_ratio}
              onChange={(e) => setConfig((c) => ({ ...c, mix_ratio: +e.target.value }))} />
          </div>
        </div>

        {/* Music */}
        <div className="card">
          <div className="card-title"><span className="dot" />Music Track</div>
          <div className="music-row">
            <div className={`folder-input-wrap ${paths.music ? "has-value" : ""}`}
              style={{ flex: 1 }} onClick={pickFile} title={paths.music || "Auto-fetch NCS track"}>
              <span className="folder-icon">{"\uD83C\uDFB5"}</span>
              <span className={`folder-path ${paths.music ? "" : "placeholder"}`}>
                {paths.music || "Auto-fetch NCS track based on style\u2026"}
              </span>
              {paths.music && (
                <button className="clear-btn"
                  onClick={(e) => { e.stopPropagation(); setPaths((p) => ({ ...p, music: "" })); }}>{"\u2715"}</button>
              )}
            </div>
            {!paths.music && <span className="auto-badge">AUTO</span>}
          </div>
          <p style={{ marginTop: 12, fontSize: 11, color: "var(--text-muted)", lineHeight: 1.6 }}>
            Leave blank to auto-download a royalty-free track via yt-dlp.
          </p>
        </div>

        {/* Action Buttons */}
        <div className="card full-width construct-wrap">
          <div className="btn-row">
            <button className="construct-btn" onClick={startEdit} disabled={!canRun}>
              {isEditing ? <><span className="spinner" /> BUILDING TIMELINE&hellip;</> : <>{"\u26A1"} CONSTRUCT TIMELINE</>}
            </button>
            {editComplete && (
              <button className="reroll-btn" onClick={rerollEdit} disabled={isEditing}>
                {"\uD83C\uDFB2"} REROLL EDIT
              </button>
            )}
          </div>
          {(isEditing || progress > 0) && (
            <div className="progress-track">
              <div className="progress-fill" style={{ width: `${progress}%` }} />
            </div>
          )}
        </div>

        {/* Console */}
        <div className="card full-width console-wrap">
          <div className="console-header">
            <div className="console-dots"><span /><span /><span /></div>
            <span className={`console-status ${isEditing ? "active" : ""}`}>
              {isEditing ? "\u25CF RUNNING" : logs.length > 0 ? "\u25CF DONE" : "\u25CB IDLE"}
            </span>
          </div>
          <div className="console-output">
            {logs.map((line, i) => {
              const cls = colorClass(line);
              return cls
                ? <span key={i} className={cls}>{line}{"\n"}</span>
                : <span key={i}>{line}{"\n"}</span>;
            })}
            <div ref={logEndRef} />
          </div>
        </div>
      </div>
    </div>
  );
}
