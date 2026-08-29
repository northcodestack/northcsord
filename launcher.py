#!/usr/bin/env python3
"""
NorthCord Launcher - Double-click to run!
Handles environment setup, dependency checks, and auto-launch.
"""

import os
import sys
import subprocess
import platform
import json
from pathlib import Path


# Override print to be safe on environments (like CP1252/Windows) that don't support UTF-8 by default
def print(*args, **kwargs):
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    try:
        import builtins
        builtins.print(*args, **kwargs)
    except UnicodeEncodeError:
        new_args = []
        encoding = getattr(sys.stdout, 'encoding', 'ascii') or 'ascii'
        for arg in args:
            if isinstance(arg, str):
                new_args.append(arg.encode(encoding, errors='replace').decode(encoding))
            else:
                new_args.append(arg)
        try:
            import builtins
            builtins.print(*new_args, **kwargs)
        except Exception:
            pass

class NorthCordLauncher:
    def __init__(self):
        self.root_dir = Path(__file__).parent
        self.venv_dir = self.root_dir / "venv"
        self.is_windows = platform.system() == "Windows"
        
    def run(self):
        """Main launcher logic"""
        print("="*60)
        print("  🚀 NorthCord Launcher")
        print("  Discord, reimagined for the terminal.")
        print("="*60)
        
        # Check Python
        if not self.check_python():
            return
            
        # Check/Create virtual environment
        if not self.setup_venv():
            return
            
        # Install dependencies
        if not self.install_deps():
            return
            
        # Check token
        if not self.check_token():
            return
            
        # Launch application
        self.launch_app()
    
    def check_python(self):
        """Check Python version"""
        required_version = (3, 10)
        current_version = sys.version_info
        
        if current_version < required_version:
            print(f"❌ Python {required_version[0]}.{required_version[1]}+ required")
            print(f"   Current: {current_version.major}.{current_version.minor}")
            return False
        
        print(f"✅ Python {current_version.major}.{current_version.minor}")
        return True
    
    def setup_venv(self):
        """Create and setup virtual environment"""
        if not self.venv_dir.exists():
            print("📦 Creating virtual environment...")
            try:
                subprocess.run(
                    [sys.executable, "-m", "venv", str(self.venv_dir)],
                    check=True
                )
                print("✅ Virtual environment created")
            except Exception as e:
                print(f"❌ Failed to create venv: {e}")
                return False
        
        # Activate venv for subsequent commands
        if self.is_windows:
            self.python_exe = self.venv_dir / "Scripts" / "python.exe"
            self.pip_exe = self.venv_dir / "Scripts" / "pip.exe"
        else:
            self.python_exe = self.venv_dir / "bin" / "python"
            self.pip_exe = self.venv_dir / "bin" / "pip"
        
        if not self.python_exe.exists():
            print("❌ Virtual environment corrupted")
            return False
            
        print("✅ Virtual environment ready")
        return True
    
    def install_deps(self):
        """Install dependencies"""
        req_file = self.root_dir / "requirements.txt"
        if not req_file.exists():
            print("❌ requirements.txt not found")
            return False
        
        # Check if core dependencies are already installed
        try:
            result = subprocess.run(
                [str(self.python_exe), "-c", "import textual, requests, websocket, cryptography, miniaudio"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                print("✅ Core dependencies already installed")
                return True
        except:
            pass
        
        print("📦 Installing dependencies...")
        try:
            subprocess.run(
                [str(self.pip_exe), "install", "-r", str(req_file)],
                check=True
            )
            print("✅ All dependencies installed successfully")
            return True
        except Exception:
            print("⚠️ Direct requirements installation failed. Installing packages individually...")

        # Individual package fallback
        with open(req_file, "r", encoding="utf-8") as f:
            deps = [line.strip() for line in f if line.strip() and not line.startswith("#")]

        optional_deps = ["pyaudio", "opuslib"]
        installed_core = True

        for dep in deps:
            dep_name = dep.split(">=")[0].split("<=")[0].split("==")[0].strip()
            print(f"📦 Installing {dep_name}...")
            try:
                subprocess.run(
                    [str(self.pip_exe), "install", dep],
                    check=True
                )
                print(f"✅ Installed {dep_name}")
            except Exception as e:
                if dep_name.lower() in optional_deps:
                    print(f"⚠️ Failed to install optional dependency '{dep_name}': {e}")
                    print("   Application will run with limited capabilities for this feature.")
                else:
                    print(f"❌ Failed to install required dependency '{dep_name}': {e}")
                    installed_core = False

        return installed_core
            
    def get_config_path(self) -> Path:
        """Resolve the default system config path for NorthCord"""
        if os.name == "nt":
            base = Path(os.environ.get("APPDATA", Path.home() / ".config"))
        else:
            base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
        return base / "northcord" / "config.json"
    
    def check_token(self):
        """Check if token exists, run setup if needed"""
        config_file = self.get_config_path()
        local_config = self.root_dir / "data" / "config.json"
        
        # Check system config path first, then fallback to local data dir
        selected_config = None
        if config_file.exists():
            selected_config = config_file
        elif local_config.exists():
            selected_config = local_config
            
        if not selected_config:
            print("🔑 No configuration found. Running setup...")
            return self.run_setup()
        
        # Check if token is valid
        try:
            with open(selected_config, "r", encoding="utf-8") as f:
                config = json.load(f)
                token = config.get("token", "")
                if not token or len(token) < 10 or token.startswith("test_"):
                    print("🔑 Token not configured. Running setup...")
                    return self.run_setup()
                return True
        except:
            return self.run_setup()
    
    def run_setup(self):
        """Run setup wizard"""
        try:
            # Change directory to project root before running to ensure imports work
            subprocess.run(
                [str(self.python_exe), "-m", "northcord", "--setup"],
                cwd=str(self.root_dir),
                check=True
            )
            return True
        except Exception as e:
            print(f"❌ Setup failed: {e}")
            return False
    
    def launch_app(self):
        """Launch the main application"""
        print("\n🚀 Launching NorthCord...")
        try:
            # Launch in same terminal window
            subprocess.run(
                [str(self.python_exe), "-m", "northcord"],
                cwd=str(self.root_dir),
                check=True
            )
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
        except Exception as e:
            print(f"❌ Failed to launch: {e}")
            input("Press Enter to exit...")

if __name__ == "__main__":
    try:
        launcher = NorthCordLauncher()
        launcher.run()
    except KeyboardInterrupt:
        try:
            import os
            os.system('cls' if os.name == 'nt' else 'clear')
        except:
            pass
        sys.exit(0)
