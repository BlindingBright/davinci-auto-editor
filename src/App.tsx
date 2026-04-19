import { useState, useEffect, useRef } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import "./App.css";

function App() {
  const [logs, setLogs] = useState<string[]>([]);
  const [isEditing, setIsEditing] = useState(false);
  const [editComplete, setEditComplete] = useState(false);
  const [progress, setProgress] = useState(0);
  const [editCount, setEditCount] = useState(0);
  const [currentPhase, setCurrentPhase] = useState("");
  const logEndRef = useRef<HTMLDivElement>(null);

  const [paths, setPaths] = useState({
    aroll: "",
    broll: "",
    fpv: "",
    music: "",
  });

  const [config, setConfig] = useState({
    style: "hyper",
    mix_ratio: 50,
    max_duration: 30,
  });

  // V2.0 additions
  const [titleText, setTitleText] = useState("");
  const [autoRender, setAutoRender] = useState(false);
  const [renderPreset, setRenderPreset] = useState("youtube_1080");
  const [outputDir, setOutputDir] = useState("");

  useEffect(() => {
    const unlisten = listen<string>("log", (event) => {
      setLogs((prev) => [...prev, `[${new Date().toLocaleTimeString()}] ${event.payload}`]);
      
      // Progress heuristics based on log keywords
      const msg = event.payload.toLowerCase();
      if (msg.includes("transcribing")) { setProgress(10); setCurrentPhase("Analyzing Speech..."); }
      if (msg.includes("motion analysis") || msg.includes("analyzing fpv")) { setProgress(20); setCurrentPhase("Motion Analysis..."); }
      if (msg.includes("downloading music")) { setProgress(30); setCurrentPhase("Fetching Music..."); }
      if (msg.includes("building") || msg.includes("phase 1")) { setProgress(35); setCurrentPhase("Phase 1: Assembly"); }
      if (msg.includes("phase 2") || msg.includes("exporting")) { setProgress(45); setCurrentPhase("Phase 2: XML Export"); }
      if (msg.includes("phase 3") || msg.includes("injecting")) { setProgress(55); setCurrentPhase("Phase 3: Transitions"); }
      if (msg.includes("phase 4") || msg.includes("re-importing")) { setProgress(65); setCurrentPhase("Phase 4: Re-Import"); }
      if (msg.includes("phase 5") || msg.includes("vfx")) { setProgress(72); setCurrentPhase("Phase 5: VFX Polish"); }
      if (msg.includes("phase 6") || msg.includes("color grading")) { setProgress(80); setCurrentPhase("Phase 6: Color Grading"); }
      if (msg.includes("phase 7") || msg.includes("fusion title")) { setProgress(87); setCurrentPhase("Phase 7: Titles"); }
      if (msg.includes("phase 8") || msg.includes("auto-rendering")) { setProgress(92); setCurrentPhase("Phase 8: Rendering..."); }
      if (msg.includes("render") && msg.includes("progress")) {
        const pctMatch = msg.match(/(\d+)%/);
        if (pctMatch) setProgress(92 + Math.round(parseInt(pctMatch[1]) * 0.08));
      }
      if (msg.includes("finished successfully")) {
        setProgress(100);
        setCurrentPhase("Complete!");
        setIsEditing(false);
        setEditComplete(true);
      }
    });
    return () => { unlisten.then(u => u()); };
  }, []);

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  async function startEdit() {
    // Prevent standard web browsers from crashing when trying to call Tauri APIs
    if (!(window as any).__TAURI_INTERNALS__) {
      alert("STOP! You are trying to run the AI engine from your web browser (Chrome, Edge, etc.).\n\nThe web browser cannot connect to DaVinci Resolve. Please minimize your web browser and open the native 'DaVinci Auto-Editor' application window that popped up on your computer!");
      setLogs([
        "❌ CRITICAL ERROR: Running in Web Browser", 
        "You are operating the preview web page instead of the native app.",
        "Please minimize this browser window. Find the newly opened 'DaVinci Auto-Editor' window on your taskbar and click the button there."
      ]);
      return;
    }

    setIsEditing(true);
    setEditComplete(false);
    setProgress(2);
    setCurrentPhase("Initializing...");
    setLogs(["🚀 Initializing DaVinci Auto-Editor AI Engine V2..."]);
    try {
      await invoke("start_edit", {
        aRollPath: paths.aroll,
        bRollPath: paths.broll,
        fpvPath: paths.fpv,
        musicPath: paths.music,
        style: config.style,
        mixRatio: config.mix_ratio,
        maxDuration: config.max_duration,
        titleText: titleText,
        autoRender: autoRender,
        renderPreset: renderPreset,
        outputDir: outputDir,
      });
    } catch (e) {
      setLogs((prev) => [...prev, `❌ Critical Error: ${e}`]);
      setIsEditing(false);
    }
  }

  async function rerollEdit() {
    setEditCount((c) => c + 1);
    setLogs([`🎲 Rerolling edit #${editCount + 2}... Same footage, fresh vibes.`]);
    startEdit();
  }

  async function pickDirectory(key: 'aroll' | 'broll' | 'fpv') {
    if (!(window as any).__TAURI_INTERNALS__) return;
    const selected = await invoke<string | null>("select_directory");
    if (selected) setPaths((prev) => ({...prev, [key]: selected}));
  }

  async function pickFile() {
    if (!(window as any).__TAURI_INTERNALS__) return;
    const selected = await invoke<string | null>("select_file");
    if (selected) setPaths((prev) => ({...prev, music: selected}));
  }

  async function pickOutputDir() {
    if (!(window as any).__TAURI_INTERNALS__) return;
    const selected = await invoke<string | null>("select_directory");
    if (selected) setOutputDir(selected);
  }

  return (
    <div className="container">
      <div className="header-area">
        <div className="status-badge">
          <span className="status-dot"></span>
          AI ENGINE V2
        </div>
        <h1>DaVinci AI Editor</h1>
        <p className="subtitle">Automated Beat-Synced Cinema Engine — Now with Auto Color, Titles & Render</p>
      </div>

      {/* Footage Sources */}
      <div className="panel">
        <div className="section-title">📹 Footage Sources</div>
        <div className="grid">
          <div className="control-group">
            <label>A-Roll (Talking)</label>
            <div className="input-with-btn">
              <input id="aroll-path" type="text" placeholder="Select A-Roll folder..." value={paths.aroll} onChange={(e) => setPaths({...paths, aroll: e.target.value})} />
              <button className="btn-browse" onClick={() => pickDirectory('aroll')} title="Browse Folder">📁</button>
            </div>
          </div>
          <div className="control-group">
            <label>B-Roll (Action)</label>
            <div className="input-with-btn">
              <input id="broll-path" type="text" placeholder="Select B-Roll folder..." value={paths.broll} onChange={(e) => setPaths({...paths, broll: e.target.value})} />
              <button className="btn-browse" onClick={() => pickDirectory('broll')} title="Browse Folder">📁</button>
            </div>
          </div>
          <div className="control-group">
            <label>FPV (Drone)</label>
            <div className="input-with-btn">
              <input id="fpv-path" type="text" placeholder="Select FPV folder..." value={paths.fpv} onChange={(e) => setPaths({...paths, fpv: e.target.value})} />
              <button className="btn-browse" onClick={() => pickDirectory('fpv')} title="Browse Folder">📁</button>
            </div>
          </div>
          <div className="control-group">
            <label>Custom Music (Optional)</label>
            <div className="input-with-btn">
              <input id="music-path" type="text" placeholder="Leave blank for AI music" value={paths.music} onChange={(e) => setPaths({...paths, music: e.target.value})} />
              <button className="btn-browse" onClick={pickFile} title="Browse File">🎵</button>
            </div>
          </div>
        </div>
      </div>

      {/* Edit Configuration */}
      <div className="panel">
        <div className="section-title">⚙️ Edit Configuration</div>
        <div className="grid">
          <div className="control-group">
            <label>Editing Style</label>
            <select id="style-select" value={config.style} onChange={(e) => setConfig({...config, style: e.target.value})}>
              <option value="hyper">⚡ Hyper Montage (0.5-1s)</option>
              <option value="reel">🎬 Smart Reel (1-2s)</option>
              <option value="vlog">📹 Vlog Story (4-6s)</option>
              <option value="cinematic">🎥 Cinematic (8s+)</option>
            </select>
          </div>
          <div className="control-group">
            <label>Duration (Seconds)</label>
            <input id="duration-input" type="number" value={config.max_duration} onChange={(e) => setConfig({...config, max_duration: parseInt(e.target.value) || 30})} />
          </div>
          <div className="control-group">
            <label>A-Roll / FPV Mix %</label>
            <input id="mix-input" type="number" value={config.mix_ratio} onChange={(e) => setConfig({...config, mix_ratio: parseInt(e.target.value) || 50})} />
          </div>
          <div className="control-group">
            <label>Intro Title (Optional)</label>
            <input id="title-input" type="text" placeholder="e.g. My Epic Adventure" value={titleText} onChange={(e) => setTitleText(e.target.value)} />
          </div>
        </div>
      </div>

      {/* Render & Export */}
      <div className="panel">
        <div className="section-title">🎯 Render & Export</div>
        <div className="grid">
          <div className="control-group">
            <label className="toggle-label">
              <input id="render-toggle" type="checkbox" checked={autoRender} onChange={(e) => setAutoRender(e.target.checked)} />
              <span className="toggle-text">Auto-Render after assembly</span>
            </label>
          </div>
          {autoRender && (
            <>
              <div className="control-group">
                <label>Export Preset</label>
                <select id="preset-select" value={renderPreset} onChange={(e) => setRenderPreset(e.target.value)}>
                  <option value="youtube_1080">YouTube 1080p (H.265)</option>
                  <option value="youtube_4k">YouTube 4K (H.265)</option>
                  <option value="tiktok_vertical">TikTok/Reels 9:16</option>
                  <option value="instagram_square">Instagram 1:1</option>
                  <option value="prores_master">ProRes Master</option>
                </select>
              </div>
              <div className="control-group">
                <label>Output Directory</label>
                <div className="input-with-btn">
                  <input id="output-path" type="text" placeholder="~/Videos/DaVinci Auto-Editor" value={outputDir} onChange={(e) => setOutputDir(e.target.value)} />
                  <button className="btn-browse" onClick={pickOutputDir} title="Browse Folder">📂</button>
                </div>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Action Buttons */}
      <div className="panel action-panel">
        <div className="btn-row">
          <button id="start-btn" className="btn-primary" onClick={startEdit} disabled={isEditing}>
            {isEditing ? "⏳ ENGINE RUNNING..." : "🚀 CONSTRUCT TIMELINE"}
          </button>
          {editComplete && (
            <button id="reroll-btn" className="btn-reroll" onClick={rerollEdit} disabled={isEditing}>
              🎲 REROLL
            </button>
          )}
        </div>

        {isEditing && (
          <div className="progress-section">
            <div className="progress-label">
              <span>{currentPhase}</span>
              <span>{progress}%</span>
            </div>
            <div className="progress-container">
              <div className="progress-bar" style={{ width: `${progress}%` }}></div>
            </div>
          </div>
        )}
      </div>

      {/* AI Engine Output */}
      <div className="panel">
        <div className="section-title">🖥️ AI Engine Output</div>
        <div className="log-container">
          {logs.map((log, i) => (
            <div key={i} className={`log-entry ${log.includes("successfully") || log.includes("SUCCESS") || log.includes("✅") ? "success" : log.includes("Error") || log.includes("❌") ? "error" : log.includes("Warning") ? "warning" : ""}`}>
              {log}
            </div>
          ))}
          <div ref={logEndRef} />
        </div>
      </div>

      {/* Pipeline Phase Indicator */}
      {isEditing && (
        <div className="pipeline-indicator">
          {["Analyze", "Assemble", "Transitions", "VFX", "Color", "Titles", "Render"].map((phase, i) => {
            const phaseProgress = [10, 35, 55, 72, 80, 87, 92];
            const isActive = progress >= phaseProgress[i];
            const isCurrent = progress >= phaseProgress[i] && (i === phaseProgress.length - 1 || progress < phaseProgress[i + 1]);
            return (
              <div key={phase} className={`pipeline-step ${isActive ? "active" : ""} ${isCurrent ? "current" : ""}`}>
                <div className="step-dot"></div>
                <span>{phase}</span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default App;
