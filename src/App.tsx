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
  const logEndRef = useRef<HTMLDivElement>(null);

  const [paths, setPaths] = useState({
    aroll: "E:\\Zoe\\SKE Ent\\Video\\A roll",
    broll: "E:\\Zoe\\SKE Ent\\Video\\B Roll",
    fpv: "E:\\Zoe\\SKE Ent\\Video\\Drone Footage",
    music: "",
  });

  const [config, setConfig] = useState({
    style: "hyper",
    mix_ratio: 50,
    max_duration: 30,
  });

  useEffect(() => {
    const unlisten = listen<string>("log", (event) => {
      setLogs((prev) => [...prev, `[${new Date().toLocaleTimeString()}] ${event.payload}`]);
      
      // Basic progress heuristics based on log keywords
      const msg = event.payload.toLowerCase();
      if (msg.includes("transcribing")) setProgress(20);
      if (msg.includes("motion analysis")) setProgress(40);
      if (msg.includes("downloading music")) setProgress(60);
      if (msg.includes("building") || msg.includes("phase 1")) setProgress(40);
      if (msg.includes("phase 2") || msg.includes("exporting")) setProgress(60);
      if (msg.includes("phase 3") || msg.includes("injecting")) setProgress(70);
      if (msg.includes("phase 4") || msg.includes("re-importing")) setProgress(85);
      if (msg.includes("phase 5") || msg.includes("vfx")) setProgress(95);
      if (msg.includes("finished successfully")) {
        setProgress(100);
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
    setProgress(5);
    setLogs(["Initializing DaVinci Resolve AI Engine..."]);
    try {
      await invoke("start_edit", {
        aRollPath: paths.aroll,
        bRollPath: paths.broll,
        fpvPath: paths.fpv,
        musicPath: paths.music,
        style: config.style,
        mixRatio: config.mix_ratio,
        maxDuration: config.max_duration,
      });
    } catch (e) {
      setLogs((prev) => [...prev, `Critical Error: ${e}`]);
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

  return (
    <div className="container">
      <div className="status-badge">AI AUTOMATION ACTIVE</div>
      <h1>DaVinci AI Editor</h1>
      <p className="subtitle">Automated Beat-Synced Cinema Engine</p>

      <div className="panel">
        <div className="section-title">Footage Sources</div>
        <div className="grid">
          <div className="control-group">
            <label>A-Roll (Talking)</label>
            <div className="input-with-btn">
              <input type="text" value={paths.aroll} onChange={(e) => setPaths({...paths, aroll: e.target.value})} />
              <button className="btn-browse" onClick={() => pickDirectory('aroll')} title="Browse Folder">📁</button>
            </div>
          </div>
          <div className="control-group">
            <label>B-Roll (Action)</label>
            <div className="input-with-btn">
              <input type="text" value={paths.broll} onChange={(e) => setPaths({...paths, broll: e.target.value})} />
              <button className="btn-browse" onClick={() => pickDirectory('broll')} title="Browse Folder">📁</button>
            </div>
          </div>
          <div className="control-group">
            <label>FPV (Drone)</label>
            <div className="input-with-btn">
              <input type="text" value={paths.fpv} onChange={(e) => setPaths({...paths, fpv: e.target.value})} />
              <button className="btn-browse" onClick={() => pickDirectory('fpv')} title="Browse Folder">📁</button>
            </div>
          </div>
          <div className="control-group">
            <label>Custom Music (Optional)</label>
            <div className="input-with-btn">
              <input type="text" placeholder="Leave blank for auto AI music" value={paths.music} onChange={(e) => setPaths({...paths, music: e.target.value})} />
              <button className="btn-browse" onClick={pickFile} title="Browse File">🎵</button>
            </div>
          </div>
        </div>
      </div>

      <div className="panel">
        <div className="section-title">Edit Configuration</div>
        <div className="grid">
          <div className="control-group">
            <label>Editing Style</label>
            <select value={config.style} onChange={(e) => setConfig({...config, style: e.target.value})}>
              <option value="hyper">Hyper Montage (0.5-1s cuts)</option>
              <option value="reel">Smart Reel (1-2s cuts)</option>
              <option value="vlog">Vlog Story (4-6s cuts)</option>
              <option value="cinematic">Cinematic (8s+ cuts)</option>
            </select>
          </div>
          <div className="control-group">
            <label>Duration (Seconds)</label>
            <input type="number" value={config.max_duration} onChange={(e) => setConfig({...config, max_duration: parseInt(e.target.value)})} />
          </div>
          <div className="control-group">
            <label>A-Roll / FPV Mix %</label>
            <input type="number" value={config.mix_ratio} onChange={(e) => setConfig({...config, mix_ratio: parseInt(e.target.value)})} />
          </div>
        </div>
        
        <div className="btn-row">
          <button className="btn-primary" onClick={startEdit} disabled={isEditing}>
            {isEditing ? "ENGINE RUNNING..." : "CONSTRUCT TIMELINE"}
          </button>
          {editComplete && (
            <button className="btn-reroll" onClick={rerollEdit} disabled={isEditing}>
              🎲 REROLL EDIT
            </button>
          )}
        </div>

        {isEditing && (
          <div className="progress-container">
            <div className="progress-bar" style={{ width: `${progress}%` }}></div>
          </div>
        )}
      </div>

      <div className="panel">
        <div className="section-title">AI Engine Output</div>
        <div className="log-container">
          {logs.map((log, i) => (
            <div key={i} className={`log-entry ${log.includes("successfully") ? "success" : log.includes("Error") ? "warning" : ""}`}>
              {log}
            </div>
          ))}
          <div ref={logEndRef} />
        </div>
      </div>
    </div>
  );
}

export default App;
