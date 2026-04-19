use rfd::FileDialog;
use tauri_plugin_shell::ShellExt;

#[tauri::command]
fn select_directory() -> Option<String> {
    FileDialog::new()
        .pick_folder()
        .map(|path| path.display().to_string())
}

#[tauri::command]
fn select_file() -> Option<String> {
    FileDialog::new()
        .add_filter("Audio", &["mp3", "wav", "m4a", "webm", "flac", "ogg"])
        .pick_file()
        .map(|path| path.display().to_string())
}

use tauri::{AppHandle, Manager, Emitter};
use tauri_plugin_shell::process::CommandEvent;
use std::path::PathBuf;

fn get_python_dir(app: &AppHandle) -> Result<PathBuf, String> {
    let mut dir = app.path().resolve("python", tauri::path::BaseDirectory::Resource).unwrap_or_else(|_| PathBuf::from("python"));
    if !dir.join("main.py").exists() {
        if let Ok(cwd) = std::env::current_dir() {
            let dev_path = cwd.join("../python");
            if dev_path.join("main.py").exists() {
                dir = dev_path.canonicalize().unwrap_or(dev_path);
                // Windows canonicalize adds \\?\ which can break some commands
                let path_str = dir.to_str().unwrap_or("").replace("\\\\?\\", "");
                dir = PathBuf::from(path_str);
            }
        }
    }
    Ok(dir)
}

#[tauri::command]
async fn init_setup(app: AppHandle) -> Result<String, String> {
    app.emit("log", "Checking for Python 3 installation...").unwrap_or_default();
    let python_check = app.shell().command("python").arg("--version").output().await;
    
    if python_check.is_err() || !python_check.as_ref().unwrap().status.success() {
        app.emit("log", "Python not found. Downloading Python 3.11 Installer...").unwrap_or_default();
        
        let py_installer_path = std::env::temp_dir().join("python-3.11.9-amd64.exe");
        let py_installer_str = py_installer_path.to_str().unwrap();
        
        let download_cmd = format!("Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe' -OutFile '{}'", py_installer_str);
        
        app.shell().command("powershell").arg("-Command").arg(&download_cmd).output().await.map_err(|e| e.to_string())?;
        
        app.emit("log", "Installing Python Silently. This might require Admin 'Yes'...").unwrap_or_default();
        let install_cmd = format!("Start-Process -FilePath '{}' -ArgumentList '/quiet InstallAllUsers=0 PrependPath=1 Include_test=0' -Wait -NoNewWindow", py_installer_str);
        app.shell().command("powershell").arg("-Command").arg(&install_cmd).output().await.map_err(|e| e.to_string())?;
        
        app.emit("log", "Python installed successfully!").unwrap_or_default();
    }

    app.emit("log", "Configuring DaVinci Resolve Environment Variables...").unwrap_or_default();
    let env_cmd = "[Environment]::SetEnvironmentVariable('RESOLVE_SCRIPT_API', '%PROGRAMDATA%\\Blackmagic Design\\DaVinci Resolve\\Support\\Developer\\Scripting\\Modules', 'User')";
    app.shell().command("powershell").arg("-Command").arg(env_cmd).output().await.ok();

    let python_dir = get_python_dir(&app)?;
    let venv_dir = python_dir.join("venv");
    
    if !venv_dir.exists() {
        app.emit("log", "Setting up local Python Virtual Environment for ML...").unwrap_or_default();
        
        app.shell().command("python").arg("-m").arg("venv").arg(venv_dir.to_str().unwrap()).output().await.map_err(|e| format!("Venv Error: {}", e))?;
        
        app.emit("log", "Downloading Machine Learning Packages...").unwrap_or_default();
        let pip_exe = venv_dir.join("Scripts").join("pip.exe");
        let req_txt = python_dir.join("requirements.txt");
        
        let pip_cmd = app.shell().command(pip_exe.to_str().unwrap()).arg("install").arg("-r").arg(req_txt.to_str().unwrap());
        let (mut rx, mut _child) = pip_cmd.spawn().map_err(|e| format!("Pip Spawn Error: {}", e))?;
        
        while let Some(event) = rx.recv().await {
            match event {
                CommandEvent::Stdout(line) => { app.emit("log", String::from_utf8_lossy(&line)).unwrap_or_default(); }
                CommandEvent::Stderr(line) => { app.emit("log", format!("[Err] {}", String::from_utf8_lossy(&line))).unwrap_or_default(); }
                _ => {}
            }
        }
        
        app.emit("log", "ML Packages fully installed!").unwrap_or_default();
    }
    
    app.emit("log", "Ready for Editing!").unwrap_or_default();
    Ok("Setup Complete".to_string())
}

#[tauri::command]
async fn start_edit(app: AppHandle, a_roll_path: String, b_roll_path: String, fpv_path: String, music_path: String, style: String, mix_ratio: u32, max_duration: u32, title_text: String, auto_render: bool, render_preset: String, output_dir: String) -> Result<String, String> {
    let python_dir = get_python_dir(&app)?;
    let venv_dir = python_dir.join("venv");

    app.emit("log", "🚀 Launching DaVinci Resolve AI Engine V2...").unwrap_or_default();
    let p_exe = venv_dir.join("Scripts").join("python.exe");
    let main_py = python_dir.join("main.py");
    
    let mut command = app.shell().command(p_exe.to_str().unwrap())
        .arg("-u")
        .arg(main_py.to_str().unwrap())
        .arg("--aroll").arg(&a_roll_path)
        .arg("--broll").arg(&b_roll_path)
        .arg("--fpv").arg(&fpv_path)
        .arg("--style").arg(&style)
        .arg("--mix_ratio").arg(&mix_ratio.to_string())
        .arg("--max_duration").arg(&max_duration.to_string());
        
    if !music_path.is_empty() {
        command = command.arg("--music_path").arg(&music_path);
    }

    // V2.0: Title text
    if !title_text.is_empty() {
        command = command.arg("--title").arg(&title_text);
    }

    // V2.0: Auto-render
    if auto_render {
        command = command.arg("--render")
            .arg("--render_preset").arg(&render_preset);
        if !output_dir.is_empty() {
            command = command.arg("--output_dir").arg(&output_dir);
        }
    }
        
    let (mut rx, mut _child) = command.spawn().map_err(|e| format!("Spawn Error: {}", e))?;
    
    while let Some(event) = rx.recv().await {
        match event {
            CommandEvent::Stdout(line) => { app.emit("log", String::from_utf8_lossy(&line)).unwrap_or_default(); }
            CommandEvent::Stderr(line) => { app.emit("log", format!("[Err] {}", String::from_utf8_lossy(&line))).unwrap_or_default(); }
            _ => {}
        }
    }
    
    app.emit("log", "✅ Pipeline complete!").unwrap_or_default();
    Ok("Finished pipeline".to_string())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_shell::init())
        .invoke_handler(tauri::generate_handler![select_directory, select_file, init_setup, start_edit])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
