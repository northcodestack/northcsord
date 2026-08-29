"""
NorthCord Launcher TUI - Modern terminal UI for launching
"""

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Button, Label, ProgressBar, Static
from textual.containers import Container, Vertical, Horizontal
from textual.screen import Screen
from textual.reactive import reactive
import subprocess
import sys
from pathlib import Path

class LauncherScreen(Screen):
    """Main launcher screen"""
    
    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Static("🚀 NorthCord Launcher", classes="title"),
            Static("Discord, reimagined for the terminal.", classes="subtitle"),
            Vertical(
                Label("Status: Ready", id="status"),
                ProgressBar(total=100, id="progress"),
                Horizontal(
                    Button("Launch NorthCord", variant="primary", id="launch"),
                    Button("Setup Wizard", variant="default", id="setup"),
                    Button("Exit", variant="error", id="exit"),
                ),
                id="buttons"
            ),
            id="container"
        )
        yield Footer()
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "launch":
            self.launch_app()
        elif event.button.id == "setup":
            self.run_setup()
        elif event.button.id == "exit":
            self.app.exit()
    
    def launch_app(self):
        """Launch the main application"""
        status = self.query_one("#status")
        progress = self.query_one("#progress")
        
        status.update("🚀 Launching NorthCord...")
        progress.update(progress=50)
        
        # Run in background
        import threading
        def run():
            subprocess.run([sys.executable, "-m", "northcord"])
            self.app.call_from_thread(self.app.exit)
        
        threading.Thread(target=run, daemon=True).start()
    
    def run_setup(self):
        """Run setup wizard"""
        status = self.query_one("#status")
        status.update("🔑 Running setup wizard...")
        subprocess.run([sys.executable, "-m", "northcord", "--setup"])
        status.update("✅ Setup complete!")

class NorthCordLauncherApp(App):
    CSS = """
    #container {
        padding: 2;
        margin: 1;
        border: solid $primary;
        height: 100%;
    }
    .title {
        text-style: bold;
        color: $primary;
        padding: 1;
    }
    .subtitle {
        color: $text-muted;
        padding-bottom: 2;
    }
    #buttons {
        margin-top: 2;
        padding: 1;
    }
    Button {
        margin: 1;
    }
    #status {
        padding: 1;
        color: $text-muted;
    }
    """
    SCREENS = {"main": LauncherScreen}
    
    def on_mount(self) -> None:
        self.push_screen("main")

if __name__ == "__main__":
    app = NorthCordLauncherApp()
    app.run()
