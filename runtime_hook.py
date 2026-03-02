"""
Runtime hook for PyInstaller - fixes paths for templates, static files, and uploads dir.
This runs before the main application code when executing as a bundled .exe
"""
import sys
import os

# When running as a PyInstaller bundle, sys._MEIPASS contains the temp extraction path
if hasattr(sys, '_MEIPASS'):
    # Add the bundle directory to the path so our app modules are found
    bundle_dir = sys._MEIPASS
    sys.path.insert(0, bundle_dir)
    
    # Set an env var so the app knows where bundled assets are
    os.environ['MEIPASS_DIR'] = bundle_dir
    
# Create uploads directory next to the .exe (or in current working dir)
if hasattr(sys, '_MEIPASS'):
    # Running as .exe - create uploads next to the exe file
    exe_dir = os.path.dirname(sys.executable)
else:
    exe_dir = os.path.dirname(os.path.abspath(__file__))

uploads_dir = os.path.join(exe_dir, 'uploads')
os.makedirs(uploads_dir, exist_ok=True)
