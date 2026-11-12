# Release checklist (manual, before announcing a release)

Use a clean Windows 10/11 user account without Python or Ollama.

1. Download `Agora-Setup-x.y.z.exe` from the GitHub release. SmartScreen warns; **More info → Run anyway**. The installer must not ask for administrator rights.
2. Select "Add Agora to PATH". Finish the installer.
3. Start Agora from the Start menu: it opens in Windows Terminal (or a 160×45 console), and the setup wizard opens.
4. Wizard:
   - diagnostics shows RAM, GPU and disk;
   - the recommended configuration matches the GPU;
   - "Download and run installer" installs Ollama, and the wizard continues by itself;
   - "Apply recommended" sets the variables and restarts Ollama;
   - models download with progress, and `Esc` cancels then resumes;
   - Done shows `100% GPU` and the context window.
5. Mark a PDF and a DOCX. `Enter` shows their text. Run a prompt, and the run finishes with a final answer.
6. New console: `agora doctor` works (PATH), exit code 0.
7. Uninstall from "Installed apps": the program folder and shortcut are gone, while `~/.agora` and the Ollama models remain.
