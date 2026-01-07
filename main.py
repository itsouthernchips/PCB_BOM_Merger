import sys
import ctypes  # <--- REQUIRED FOR TASKBAR ICON
from PyQt5.QtWidgets import QApplication
from src.ui.main_window import MainWindow
from src.ui.styles import apply_modern_theme

def main():
    # --- WINDOWS TASKBAR ICON FIX ---
    # This ID string forces Windows to treat this as a standalone app
    if sys.platform == 'win32':
        myappid = 'company.bom.segregator.v2' 
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    # --------------------------------

    app = QApplication(sys.argv)
    
    apply_modern_theme(app)
    
    window = MainWindow()
    window.showMaximized() 
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()