import { useState } from "react";

const repository = "https://github.com/RoyaleCoach53/biosignal-lab";

export function installationCommands(platform, workflow) {
  const windows = platform === "windows";
  const python = windows ? ".\\.venv\\Scripts\\python.exe" : ".venv/bin/python";
  const launch = workflow === "dashboard"
    ? `${python} -m streamlit run app.py`
    : workflow === "cli"
      ? `${python} -m biosignal_lab.cli analyze --input examples/data/eeg_demo.csv --sfreq 250 --unit uv --time-column time_s --output local-results/eeg`
      : `${python} -c "from biosignal_lab import analyze; from biosignal_lab.simulate import synthetic_recording; print(analyze(synthetic_recording()).summary())"`;
  return [
    `git clone --branch v0.3.0 ${repository}.git`,
    "cd biosignal-lab",
    `${windows ? "py -3" : "python3"} -m venv .venv`,
    `${python} -m pip install -e ${workflow === "dashboard" ? '\".[app]\"' : "."}`,
    launch,
  ].join("\n");
}

export default function LocalWorkspace({ rtl = false }) {
  const [platform, setPlatform] = useState("unix");
  const [workflow, setWorkflow] = useState("dashboard");
  const [message, setMessage] = useState("");
  const commands = installationCommands(platform, workflow);
  async function copy() {
    try {
      await navigator.clipboard.writeText(commands);
      setMessage("Commands copied.");
    } catch {
      setMessage("Clipboard unavailable. Select the commands below to copy them.");
    }
  }
  return <section className="shell section local-workspace" id="install" aria-labelledby="install-heading">
    <header className="section-title">
      <p className="eyebrow"><i/>{rtl ? "على جهازك" : "YOUR LOCAL WORKSPACE"}</p>
      <h2 id="install-heading">{rtl ? "ابدأ تجربة قابلة للتكرار." : "Make the experiment your own."}</h2>
      <p>{rtl ? "شغّل لوحة التحكم أو واجهة الأوامر أو مكتبة بايثون على جهازك. تعليمات الأوامر بالإنجليزية." : "Run the dashboard, command line, or Python SDK on your own computer. Core analysis needs no API key or cloud account."}</p>
    </header>
    <div className="install-console" lang="en" dir="ltr">
      <div className="install-controls">
        <label>Operating system<select value={platform} onChange={event => {setPlatform(event.target.value); setMessage("");}}>
          <option value="unix">Linux / macOS</option><option value="windows">Windows PowerShell</option>
        </select></label>
        <label>Local workflow<select value={workflow} onChange={event => {setWorkflow(event.target.value); setMessage("");}}>
          <option value="dashboard">Interactive dashboard</option><option value="cli">Command line</option><option value="sdk">Python SDK</option>
        </select></label>
        <button type="button" onClick={copy}>Copy commands</button>
      </div>
      <pre tabIndex={0} aria-label="Installation commands"><code>{commands}</code></pre>
      <p className="install-status" role="status" aria-live="polite">{message}</p>
      <p>Requires Git and Python 3.10 or newer. These commands install the existing v0.3.0 release from source. Choose a new folder. CLI exports contain synthetic summaries; choose a new output name when keeping earlier results.</p>
      <p>The website above uses a fixed catalogue computed by Python at build time. Installing locally lets you analyze your own recordings and use the complete sampling and filter controls. Keep identifiable recordings on a host you trust.</p>
      <div className="install-links"><a href={`${repository}/blob/v0.3.0/README.md#install`}>Full installation guide</a><a href={`${repository}/blob/v0.3.0/docs/ARCHITECTURE.md`}>Python architecture</a><a href={`${repository}/blob/v0.3.0/docs/LIMITATIONS.md`}>Scientific boundaries</a></div>
    </div>
  </section>;
}
