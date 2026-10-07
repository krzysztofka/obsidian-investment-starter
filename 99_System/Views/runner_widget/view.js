/**
 * DataviewJS View: Resilient Interactive Pipeline & Import Runner
 *
 * Designed specifically for Obsidian Desktop with Dataview.
 * Persists running process state, streaming logs, and execution status across
 * Dataview reactive re-renders triggered by vault markdown file modifications.
 *
 * Usage in Markdown:
 *   ```dataviewjs
 *   await dv.view("99_System/Views/runner_widget");
 *   ```
 */

// 1. Initialize or connect to persistent global state in window
if (!window.__vaultPipelineRunner) {
    window.__vaultPipelineRunner = {
        isRunning: false,
        activeCmd: "",
        proc: null,
        startTime: null,
        statusText: "Idle",
        statusColor: null,
        logs: "",
        listeners: new Set(),
        pollTimer: null
    };
}
const state = window.__vaultPipelineRunner;

// Purge any disconnected listeners from previous Dataview re-renders
for (const listener of Array.from(state.listeners)) {
    if (listener.isDead && listener.isDead()) {
        state.listeners.delete(listener);
    }
}

// 2. Inject CSS styles once
const styleId = "pipeline-runner-styles-v2";
if (!document.getElementById(styleId)) {
    const styleEl = document.createElement("style");
    styleEl.id = styleId;
    styleEl.textContent = `
        .pipeline-runner-widget {
            border: 1px solid var(--background-modifier-border);
            border-radius: 8px;
            padding: 16px;
            margin: 14px 0;
            background: var(--background-secondary);
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
        }
        .pr-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
            flex-wrap: wrap;
            gap: 8px;
        }
        .pr-title {
            font-weight: 600;
            font-size: 1.05em;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .pr-badge {
            font-size: 0.75em;
            padding: 2px 8px;
            border-radius: 12px;
            background: var(--interactive-accent);
            color: var(--text-on-accent);
            font-weight: 500;
        }
        .pr-badge.running {
            background: #f59e0b;
            color: #000;
            animation: pr-pulse 1.5s infinite;
        }
        @keyframes pr-pulse {
            0% { opacity: 1; }
            50% { opacity: 0.6; }
            100% { opacity: 1; }
        }
        .pr-buttons {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-bottom: 12px;
        }
        .pr-btn {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 6px 12px;
            border-radius: 6px;
            font-size: 0.88em;
            font-weight: 500;
            cursor: pointer;
            border: 1px solid var(--interactive-accent);
            background: var(--background-primary);
            color: var(--text-normal);
            transition: all 0.15s ease;
            user-select: none;
        }
        .pr-btn:hover:not(:disabled) {
            background: var(--interactive-accent);
            color: var(--text-on-accent);
        }
        .pr-btn.primary {
            background: var(--interactive-accent);
            color: var(--text-on-accent);
            font-weight: 600;
        }
        .pr-btn.primary:hover:not(:disabled) {
            opacity: 0.9;
        }
        .pr-btn.stop {
            border-color: #ef4444;
            color: #ef4444;
            background: transparent;
            font-weight: 600;
        }
        .pr-btn.stop:hover:not(:disabled) {
            background: #ef4444;
            color: #fff;
        }
        .pr-btn.small {
            padding: 3px 8px;
            font-size: 0.78em;
            border-color: var(--background-modifier-border);
        }
        .pr-btn:disabled {
            opacity: 0.45;
            cursor: not-allowed;
        }
        .pr-console-bar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: 10px;
            margin-bottom: 6px;
            font-size: 0.82em;
        }
        .pr-console-tools {
            display: flex;
            gap: 6px;
        }
        .pr-console {
            background: #09090b;
            color: #f4f4f5;
            font-family: var(--font-monospace, monospace);
            font-size: 0.82em;
            padding: 12px;
            border-radius: 6px;
            height: 280px;
            overflow-y: auto;
            white-space: pre-wrap;
            word-break: break-word;
            border: 1px solid rgba(255, 255, 255, 0.12);
        }
        .pr-status-bar {
            display: flex;
            justify-content: space-between;
            font-size: 0.8em;
            color: var(--text-muted);
            margin-top: 8px;
        }
    `;
    document.head.appendChild(styleEl);
}

// 3. Environment & Node detection
let childProcess = null;
try {
    if (typeof require !== "undefined") {
        childProcess = require("child_process");
    } else if (window && window.require) {
        childProcess = window.require("child_process");
    }
} catch (e) {
    childProcess = null;
}

let vaultPath = ".";
try {
    if (app && app.vault && app.vault.adapter && app.vault.adapter.basePath) {
        vaultPath = app.vault.adapter.basePath;
    }
} catch (e) {
    vaultPath = ".";
}

const canExecute = !!(childProcess && (childProcess.spawn || childProcess.exec));

// 4. Load initial logs from 99_System/runner.log if memory is blank
if (!state.logs && app && app.vault && app.vault.adapter) {
    app.vault.adapter.read("99_System/runner.log").then(content => {
        if (!state.logs && content) {
            state.logs = content.slice(-15000);
            notifyListeners();
        }
    }).catch(() => {
        if (!state.logs) {
            state.logs = "Console ready. Click any action above to run pipeline directly from Obsidian.\n";
            notifyListeners();
        }
    });
} else if (!state.logs) {
    state.logs = "Console ready. Click any action above to run pipeline directly from Obsidian.\n";
}

// Helper: Broadcast state changes to all active views
function notifyListeners() {
    for (const listener of Array.from(state.listeners)) {
        if (listener.isDead && listener.isDead()) {
            state.listeners.delete(listener);
        } else {
            try {
                listener.update();
            } catch (e) {}
        }
    }
}

// 5. Construct DOM elements
const container = dv.el("div", "", { cls: "pipeline-runner-widget" });

const header = document.createElement("div");
header.className = "pr-header";

const titleBox = document.createElement("div");
titleBox.className = "pr-title";

const badge = document.createElement("span");
badge.className = `pr-badge ${state.isRunning ? "running" : ""}`;
badge.textContent = state.isRunning ? "⚡ Running" : (canExecute ? "Direct Execution" : "Copy Mode");

titleBox.innerHTML = `<span>⚡ Pipeline Action Center</span>`;
titleBox.appendChild(badge);
header.appendChild(titleBox);

const pathBox = document.createElement("div");
pathBox.style.fontSize = "0.82em";
pathBox.style.color = "var(--text-muted)";
pathBox.innerHTML = `Root: <code>${vaultPath === "." ? "Vault Root" : vaultPath}</code>`;
header.appendChild(pathBox);

const buttonsContainer = document.createElement("div");
buttonsContainer.className = "pr-buttons";

const consoleBar = document.createElement("div");
consoleBar.className = "pr-console-bar";

const statusText = document.createElement("span");
statusText.style.fontWeight = "500";
statusText.textContent = state.statusText || "Ready";
if (state.statusColor) statusText.style.color = state.statusColor;

const toolsContainer = document.createElement("div");
toolsContainer.className = "pr-console-tools";

const reloadLogBtn = document.createElement("button");
reloadLogBtn.className = "pr-btn small";
reloadLogBtn.textContent = "🔄 Reload Log";
reloadLogBtn.onclick = () => {
    if (app && app.vault && app.vault.adapter) {
        app.vault.adapter.read("99_System/runner.log").then(content => {
            state.logs = content ? content.slice(-25000) : "Log file is empty.\n";
            notifyListeners();
        }).catch(() => {
            state.logs += "\n[No 99_System/runner.log file found on disk]\n";
            notifyListeners();
        });
    }
};

const clearLogBtn = document.createElement("button");
clearLogBtn.className = "pr-btn small";
clearLogBtn.textContent = "🗑️ Clear Console";
clearLogBtn.onclick = () => {
    state.logs = "Console cleared.\n";
    notifyListeners();
};

const copyLogBtn = document.createElement("button");
copyLogBtn.className = "pr-btn small";
copyLogBtn.textContent = "📋 Copy Output";
copyLogBtn.onclick = () => {
    if (navigator.clipboard) {
        navigator.clipboard.writeText(state.logs).then(() => {
            statusText.textContent = "Logs copied to clipboard!";
            setTimeout(updateStatusUI, 2500);
        });
    }
};

const stopBtn = document.createElement("button");
stopBtn.className = "pr-btn small stop";
stopBtn.textContent = "⏹️ Stop Process";
stopBtn.style.display = state.isRunning ? "inline-flex" : "none";
stopBtn.onclick = () => {
    if (state.proc) {
        try {
            if (process.platform === "win32") {
                childProcess.exec(`taskkill /pid ${state.proc.pid} /f /t`);
            } else {
                state.proc.kill("SIGTERM");
            }
        } catch (e) {}
    }
    state.isRunning = false;
    state.proc = null;
    state.statusText = "⏹️ Process cancelled by user";
    state.statusColor = "var(--text-error)";
    state.logs += "\n\n[⏹️ Process terminated by user]\n";
    notifyListeners();
};

toolsContainer.appendChild(reloadLogBtn);
toolsContainer.appendChild(clearLogBtn);
toolsContainer.appendChild(copyLogBtn);
toolsContainer.appendChild(stopBtn);

consoleBar.appendChild(statusText);
consoleBar.appendChild(toolsContainer);

const consoleBox = document.createElement("div");
consoleBox.className = "pr-console";
consoleBox.textContent = state.logs;

const statusBar = document.createElement("div");
statusBar.className = "pr-status-bar";
statusBar.innerHTML = `
    <span id="pr-time-info">${state.isRunning && state.startTime ? `Running since ${new Date(state.startTime).toLocaleTimeString()}` : "Idle"}</span>
    <span>Log: <code>99_System/runner.log</code></span>
`;

// Action buttons configuration
const actions = [
    { label: "🚀 Run Full Pipeline (--all)", args: ["--all"], cmd: "python run.py --all", primary: true },
    { label: "📥 Import Broker CSVs (--import)", args: ["--import"], cmd: "python run.py --import", primary: false },
    { label: "💱 Update FX Rates (--update-rates)", args: ["--update-rates"], cmd: "python run.py --update-rates", primary: false },
    { label: "🌐 Sync Macro Dashboard (--macro)", args: ["--macro"], cmd: "python run.py --macro", primary: false },
    { label: "📊 Sync ETF Holdings (--sync-etfs)", args: ["--sync-etfs"], cmd: "python run.py --sync-etfs", primary: false },
    { label: "🚨 Evaluate Alerts (--alerts)", args: ["--alerts"], cmd: "python run.py --alerts", primary: false },
    { label: "📜 Update History (--history)", args: ["--history"], cmd: "python run.py --history", primary: false },
];

const actionButtonElements = [];

actions.forEach(action => {
    const btn = document.createElement("button");
    btn.className = `pr-btn ${action.primary ? "primary" : ""}`;
    btn.textContent = action.label;
    btn.title = `Execute: ${action.cmd}`;
    btn.disabled = state.isRunning;
    btn.onclick = () => runPipelineAction(action);
    buttonsContainer.appendChild(btn);
    actionButtonElements.push(btn);
});

// UI Updater function
function updateStatusUI() {
    badge.className = `pr-badge ${state.isRunning ? "running" : ""}`;
    badge.textContent = state.isRunning ? "⚡ Running" : (canExecute ? "Direct Execution" : "Copy Mode");

    statusText.textContent = state.statusText;
    if (state.statusColor) statusText.style.color = state.statusColor;
    else statusText.style.color = "inherit";

    stopBtn.style.display = state.isRunning ? "inline-flex" : "none";
    actionButtonElements.forEach(btn => btn.disabled = state.isRunning);

    consoleBox.textContent = state.logs;
    consoleBox.scrollTop = consoleBox.scrollHeight;

    const timeInfo = statusBar.querySelector("#pr-time-info");
    if (timeInfo) {
        if (state.isRunning && state.startTime) {
            const elapsed = Math.floor((Date.now() - state.startTime) / 1000);
            timeInfo.textContent = `Running: ${state.activeCmd} (${elapsed}s elapsed)`;
        } else {
            timeInfo.textContent = "Idle";
        }
    }
}

// 6. Action Execution Logic
function runPipelineAction(action) {
    if (!canExecute) {
        // Fallback: copy to clipboard
        if (navigator.clipboard) {
            navigator.clipboard.writeText(action.cmd).then(() => {
                state.statusText = `Copied to clipboard: ${action.cmd}`;
                state.statusColor = "var(--text-accent)";
                state.logs += `\n📋 Copied to clipboard:\n${action.cmd}\nPaste into your terminal to run.\n`;
                notifyListeners();
            });
        }
        return;
    }

    if (state.isRunning) return;

    state.isRunning = true;
    state.activeCmd = action.cmd;
    state.startTime = Date.now();
    state.statusText = `Running: ${action.cmd}...`;
    state.statusColor = "var(--text-warning)";
    state.logs += `\n========================================================================\n🚀 Starting: ${action.cmd}\n🕒 Started : ${new Date().toLocaleTimeString()}\n========================================================================\n`;

    notifyListeners();

    // Start timer to update elapsed seconds
    if (state.pollTimer) clearInterval(state.pollTimer);
    state.pollTimer = setInterval(() => {
        if (state.isRunning) {
            const elapsed = Math.floor((Date.now() - state.startTime) / 1000);
            state.statusText = `Running: ${state.activeCmd} (${elapsed}s)...`;
            notifyListeners();
        } else {
            clearInterval(state.pollTimer);
            state.pollTimer = null;
        }
    }, 1000);

    try {
        const env = Object.assign({}, process.env, { PYTHONUNBUFFERED: "1" });
        const spawnArgs = ["-u", "run.py", ...action.args];

        const proc = childProcess.spawn("python", spawnArgs, {
            cwd: vaultPath,
            env: env,
            shell: true
        });
        state.proc = proc;

        proc.stdout.on("data", data => {
            state.logs += data.toString("utf-8");
            // Prevent runaway string length
            if (state.logs.length > 80000) {
                state.logs = state.logs.slice(-50000);
            }
            notifyListeners();
        });

        proc.stderr.on("data", data => {
            state.logs += data.toString("utf-8");
            if (state.logs.length > 80000) {
                state.logs = state.logs.slice(-50000);
            }
            notifyListeners();
        });

        proc.on("close", code => {
            const duration = ((Date.now() - state.startTime) / 1000).toFixed(2);
            state.isRunning = false;
            state.proc = null;
            if (state.pollTimer) {
                clearInterval(state.pollTimer);
                state.pollTimer = null;
            }

            if (code === 0) {
                state.statusText = `✅ Completed in ${duration}s`;
                state.statusColor = "var(--text-success)";
                state.logs += `\n[Process completed successfully in ${duration}s]\n`;
            } else {
                state.statusText = `❌ Failed (exit code ${code}) in ${duration}s`;
                state.statusColor = "var(--text-error)";
                state.logs += `\n[Process failed with exit code ${code} after ${duration}s]\n`;
            }
            notifyListeners();
        });

        proc.on("error", err => {
            state.isRunning = false;
            state.proc = null;
            state.statusText = `❌ Error: ${err.message}`;
            state.statusColor = "var(--text-error)";
            state.logs += `\n[Failed to launch python: ${err.message}]\n`;
            notifyListeners();
        });

    } catch (err) {
        state.isRunning = false;
        state.proc = null;
        state.statusText = `❌ Failed: ${err.message}`;
        state.statusColor = "var(--text-error)";
        state.logs += `\n[Exception: ${err.message}]\n`;
        notifyListeners();
    }
}

// 7. Register this instance in state.listeners with liveness check
const currentListener = {
    isDead: () => !container.isConnected,
    update: updateStatusUI
};
state.listeners.add(currentListener);

// Assemble widget
container.appendChild(header);
container.appendChild(buttonsContainer);
container.appendChild(consoleBar);
container.appendChild(consoleBox);
container.appendChild(statusBar);

// Initial paint
updateStatusUI();
