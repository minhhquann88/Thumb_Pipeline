use std::fs::{File, OpenOptions};
use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;
use std::time::Duration;

use tauri::path::BaseDirectory;
use tauri::{AppHandle, Manager, State};

struct BackendProcess(Mutex<Option<Child>>);

struct BackendCommand {
    program: PathBuf,
    args: Vec<String>,
    current_dir: Option<PathBuf>,
}

fn find_project_root(exe_dir: &Path) -> Option<PathBuf> {
    exe_dir.ancestors().find_map(|p| {
        let has_backend = p.join("backend").join("main.py").exists();
        let has_package = p.join("package.json").exists();
        if has_backend && has_package {
            Some(p.to_path_buf())
        } else {
            None
        }
    })
}

fn python_interpreter(project_root: &Path) -> PathBuf {
    let venv_python = project_root
        .join(".venv")
        .join("Scripts")
        .join("python.exe");
    if venv_python.exists() {
        return venv_python;
    }

    PathBuf::from("python")
}

fn python_backend_command(project_root: PathBuf) -> BackendCommand {
    BackendCommand {
        program: python_interpreter(&project_root),
        args: [
            "-m",
            "uvicorn",
            "backend.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8765",
        ]
        .into_iter()
        .map(String::from)
        .collect(),
        current_dir: Some(project_root),
    }
}

/// Đường dẫn bundle theo Tauri (NSIS/MSI/cả target/release sau build).
fn tauri_resource_backend(app: &AppHandle) -> Option<BackendCommand> {
    let path = app
        .path()
        .resolve("backend_server.exe", BaseDirectory::Resource)
        .ok()?;
    if path.is_file() {
        Some(BackendCommand {
            program: path,
            args: Vec::new(),
            current_dir: None,
        })
    } else {
        None
    }
}

fn bundled_backend_command(exe_dir: &Path) -> Option<BackendCommand> {
    let candidate = exe_dir.join("_internal").join("backend_server.exe");
    if candidate.exists() {
        Some(BackendCommand {
            program: candidate,
            args: Vec::new(),
            current_dir: None,
        })
    } else {
        None
    }
}

fn dist_backend_command(exe_dir: &Path) -> Option<BackendCommand> {
    exe_dir.ancestors().find_map(|p| {
        let candidate_flat = p.join("dist").join("backend_server.exe");
        if candidate_flat.exists() {
            Some(BackendCommand {
                program: candidate_flat,
                args: Vec::new(),
                current_dir: None,
            })
        } else {
            let candidate_nested = p
                .join("dist")
                .join("backend_server")
                .join("backend_server.exe");
            if candidate_nested.exists() {
                Some(BackendCommand {
                    program: candidate_nested,
                    args: Vec::new(),
                    current_dir: None,
                })
            } else {
                None
            }
        }
    })
}

fn release_dir_backend_command(exe_dir: &Path) -> Option<BackendCommand> {
    let candidate = exe_dir.join("backend_server.exe");
    if candidate.exists() {
        Some(BackendCommand {
            program: candidate,
            args: Vec::new(),
            current_dir: None,
        })
    } else {
        None
    }
}

fn resources_backend_command(exe_dir: &Path) -> Option<BackendCommand> {
    let candidate = exe_dir.join("resources").join("backend_server.exe");
    if candidate.exists() {
        Some(BackendCommand {
            program: candidate,
            args: Vec::new(),
            current_dir: None,
        })
    } else {
        None
    }
}

fn resolve_backend_command(
    current_exe: &Path,
    debug_mode: bool,
    app: Option<&AppHandle>,
) -> Result<BackendCommand, String> {
    let exe_dir = current_exe
        .parent()
        .ok_or("Khong tim duoc thu muc chua exe")?;

    if debug_mode {
        if let Some(project_root) = find_project_root(exe_dir) {
            return Ok(python_backend_command(project_root));
        }
    }

    if let Some(app) = app {
        if let Some(command) = tauri_resource_backend(app) {
            return Ok(command);
        }
    }

    // resources/ (bundle Tauri) TRUOC _internal/ — tranh backend cu trong _internal (build_release.bat)
    // trong khi ban moi nam trong resources -> thieu route /profiles -> HTTP 404.
    if let Some(command) = resources_backend_command(exe_dir) {
        return Ok(command);
    }

    if let Some(command) = bundled_backend_command(exe_dir) {
        return Ok(command);
    }

    if let Some(command) = release_dir_backend_command(exe_dir) {
        return Ok(command);
    }

    // Chi dev: dist/ tren cay thu muc. Release KHONG dung — tranh nham dist\ o folder giong ban build
    // (vi du Desktop\release\dist\) khi chay exe / sau cai NSIS.
    if debug_mode {
        if let Some(command) = dist_backend_command(exe_dir) {
            return Ok(command);
        }
    }

    Err(format!(
        "Khong tim thay backend. Dev mode can backend/main.py; release can _internal/backend_server.exe, backend_server.exe, resources/backend_server.exe, dist/backend_server.exe hoac dist/backend_server/backend_server.exe."
    ))
}

fn backend_command(app: &AppHandle) -> Result<BackendCommand, String> {
    let current_exe =
        std::env::current_exe().map_err(|e| format!("Khong lay duoc duong dan exe: {e}"))?;
    resolve_backend_command(
        &current_exe,
        cfg!(debug_assertions),
        Some(app),
    )
}

fn spawn_backend(backend_command: BackendCommand) -> Result<Child, String> {
    let log_dir = std::env::current_exe()
        .ok()
        .and_then(|p| p.parent().map(|d| d.to_path_buf()))
        .unwrap_or_else(|| PathBuf::from("."));
    let log_path = log_dir.join("backend.log");

    let stdout = File::create(&log_path).map_err(|e| format!("Khong tao duoc backend.log: {e}"))?;
    let stderr = OpenOptions::new()
        .create(true)
        .append(true)
        .open(&log_path)
        .map_err(|e| format!("Khong mo duoc backend.log: {e}"))?;

    let mut command = Command::new(&backend_command.program);
    command
        .args(&backend_command.args)
        .stdout(Stdio::from(stdout))
        .stderr(Stdio::from(stderr));

    if let Some(current_dir) = &backend_command.current_dir {
        command.current_dir(current_dir);
    }

    let mut child = command.spawn().map_err(|e| {
        format!(
            "Khong khoi dong duoc backend: {} {} ({e})",
            backend_command.program.display(),
            backend_command.args.join(" ")
        )
    })?;

    std::thread::sleep(Duration::from_millis(400));
    if let Ok(Some(status)) = child.try_wait() {
        return Err(format!(
            "Backend thoat ngay (ma {}). Xem backend.log canh file exe.",
            status.code().map(|c| c.to_string()).unwrap_or_else(|| "?".into())
        ));
    }

    Ok(child)
}

#[tauri::command]
fn restart_backend(app: AppHandle, state: State<BackendProcess>) -> Result<String, String> {
    // Kill process cũ
    let mut guard = state.0.lock().map_err(|_| "lock poisoned".to_string())?;
    if let Some(mut child) = guard.take() {
        let _ = child.kill();
        let _ = child.wait();
    }

    // Respawn
    let cmd = backend_command(&app)?;
    let child = spawn_backend(cmd)?;
    *guard = Some(child);
    Ok("Backend restarted".to_string())
}


pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .manage(BackendProcess(Mutex::new(None)))
        .invoke_handler(tauri::generate_handler![restart_backend])
        .setup(|app| {
            let backend_command = backend_command(app.handle())?;
            let backend = spawn_backend(backend_command)?;
            let state = app.state::<BackendProcess>();
            *state.0.lock().expect("backend process lock poisoned") = Some(backend);
            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::CloseRequested { .. } = event {
                let state: State<BackendProcess> = window.app_handle().state();
                let backend = state
                    .0
                    .lock()
                    .expect("backend process lock poisoned")
                    .take();
                if let Some(mut child) = backend {
                    let _ = child.kill();
                }
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    use std::time::{SystemTime, UNIX_EPOCH};

    fn temp_project_root() -> PathBuf {
        let suffix = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .expect("clock before unix epoch")
            .as_nanos();
        let root = std::env::temp_dir().join(format!("thumb-pipeline-test-{suffix}"));
        fs::create_dir_all(root.join("backend")).expect("create backend dir");
        fs::write(root.join("backend").join("main.py"), "app = object()\n")
            .expect("write backend main");
        fs::write(root.join("package.json"), "{}\n").expect("write package json");
        root
    }

    #[test]
    fn debug_backend_command_uses_python_source_instead_of_stale_dist_exe() {
        let root = temp_project_root();
        fs::create_dir_all(root.join("dist").join("backend_server")).expect("create dist dir");
        fs::write(
            root.join("dist")
                .join("backend_server")
                .join("backend_server.exe"),
            "stale",
        )
        .expect("write stale backend exe");
        let current_exe = root
            .join("src-tauri")
            .join("target")
            .join("debug")
            .join("thumb_pipeline_desktop.exe");

        let command =
            resolve_backend_command(&current_exe, true, None).expect("resolve debug backend");

        assert_eq!(command.current_dir.as_deref(), Some(root.as_path()));
        assert_eq!(command.program, PathBuf::from("python"));
        assert_eq!(
            command.args,
            [
                "-m",
                "uvicorn",
                "backend.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                "8765"
            ]
            .map(String::from)
            .to_vec()
        );

        fs::remove_dir_all(root).expect("remove temp project");
    }

    #[test]
    fn release_backend_command_uses_resources_next_to_exe() {
        let root = temp_project_root();
        let release_dir = root.join("src-tauri").join("target").join("release");
        fs::create_dir_all(release_dir.join("resources")).expect("create resources dir");
        let backend_exe = release_dir.join("resources").join("backend_server.exe");
        fs::write(&backend_exe, "backend").expect("write backend exe");
        let current_exe = release_dir.join("thumb_pipeline_desktop.exe");
        fs::write(&current_exe, "").expect("write fake app exe");

        let command =
            resolve_backend_command(&current_exe, false, None).expect("resolve release backend");

        assert_eq!(command.program, backend_exe);
        assert_eq!(command.current_dir, None);
        assert!(command.args.is_empty());

        fs::remove_dir_all(root).expect("remove temp project");
    }
}
