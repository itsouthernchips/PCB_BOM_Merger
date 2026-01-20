from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QStackedWidget, 
                             QMessageBox, QFileDialog, QAction, QMenuBar)
from PyQt5.QtCore import Qt, QSettings, QStandardPaths
from PyQt5.QtGui import QIcon
import os
import sys

# Screens & Logic
from src.ui.screens.screen_import import ImportScreen
from src.ui.screens.screen_mapping import MappingScreen
from src.ui.screens.screen_dashboard import DashboardScreen
from src.core.excel_writer import generate_production_files
from src.core.logic_engine import perform_merge_v2

# --- RESOURCE HELPER ---
def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BOM Segregator V2")
        self.resize(1000, 700) 
        
        # --- SETTINGS INIT ---
        # This allows us to save/load folder paths across sessions
        self.settings = QSettings("SCCPL", "BOM_Segregator_V2")
        
        # Load Icon
        icon_path = resource_path(os.path.join("assets", "logo.ico"))
        if not os.path.exists(icon_path):
             icon_path = resource_path(os.path.join("assets", "logo.png"))
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        # --- MENU BAR ---
        self.create_menu_bar()
        
        # Central Widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        
        # Stacked Widget
        self.stack = QStackedWidget()
        self.layout.addWidget(self.stack)
        
        # Initialize Screens
        self.screen_import = ImportScreen()     # Index 0
        self.screen_mapping = MappingScreen()   # Index 1
        self.screen_dashboard = DashboardScreen() # Index 2
        
        self.stack.addWidget(self.screen_import)
        self.stack.addWidget(self.screen_mapping)
        self.stack.addWidget(self.screen_dashboard)
        
        # --- CONNECTIONS ---
        self.screen_import.next_clicked.connect(self.go_to_mapping)
        self.screen_import.skip_mapping_clicked.connect(self.handle_auto_process)
        self.screen_mapping.back_clicked.connect(lambda: self.stack.setCurrentIndex(0))
        self.screen_mapping.next_clicked.connect(self.run_process)
        self.screen_dashboard.back_clicked.connect(lambda: self.stack.setCurrentIndex(1))
        self.screen_dashboard.export_clicked.connect(self.perform_final_export)

    def create_menu_bar(self):
        menubar = self.menuBar()
        
        # -- FILE MENU --
        file_menu = menubar.addMenu('File')
        
        reset_action = QAction('Reset Project (Ctrl+N)', self)
        reset_action.setShortcut('Ctrl+N')
        reset_action.triggered.connect(self.reset_app)
        file_menu.addAction(reset_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction('Exit (Ctrl+Q)', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # -- SETTINGS MENU [NEW] --
        settings_menu = menubar.addMenu('Settings')
        
        set_up_action = QAction('Set Default Upload Folder...', self)
        set_up_action.triggered.connect(self.set_upload_folder)
        settings_menu.addAction(set_up_action)
        
        set_dl_action = QAction('Set Default Download Folder...', self)
        set_dl_action.triggered.connect(self.set_download_folder)
        settings_menu.addAction(set_dl_action)

        # Style
        menubar.setStyleSheet("""
            QMenuBar { background-color: white; color: #2c3e50; }
            QMenuBar::item:selected { background-color: #BDD7EE; color: #2c3e50; }
            QMenu { background-color: white; color: #2c3e50; border: 1px solid #dcdcdc; }
            QMenu::item:selected { background-color: #BDD7EE; }
        """)

    # --- SETTINGS LOGIC ---
    def _get_default_documents(self):
        return QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation)

    def set_upload_folder(self):
        current = self.settings.value("upload_dir", self._get_default_documents())
        folder = QFileDialog.getExistingDirectory(self, "Select Default Upload Folder", current)
        if folder:
            self.settings.setValue("upload_dir", folder)
            QMessageBox.information(self, "Settings Saved", f"Default Upload Folder set to:\n{folder}")

    def set_download_folder(self):
        current = self.settings.value("download_dir", self._get_default_documents())
        folder = QFileDialog.getExistingDirectory(self, "Select Default Download Folder", current)
        if folder:
            self.settings.setValue("download_dir", folder)
            QMessageBox.information(self, "Settings Saved", f"Default Download Folder set to:\n{folder}")

    # --- APP LOGIC ---
    def reset_app(self):
        on_later_screen = self.stack.currentIndex() > 0
        has_files_loaded = (self.screen_import.bom_df is not None) or (self.screen_import.xy_df is not None)

        if on_later_screen or has_files_loaded:
            reply = QMessageBox.question(self, 'Reset Project?', "This will clear all loaded files.", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.screen_import.reset_state()
                self.stack.setCurrentIndex(0)
        else:
            self.screen_import.reset_state()
            self.stack.setCurrentIndex(0)

    def go_to_mapping(self):
        bom_cols = list(self.screen_import.bom_df.columns)
        xy_cols = list(self.screen_import.xy_df.columns)
        self.screen_mapping.populate_dropdowns(bom_cols, xy_cols)
        self.stack.setCurrentIndex(1)

    def handle_auto_process(self, auto_map):
        bom_cols = list(self.screen_import.bom_df.columns)
        xy_cols = list(self.screen_import.xy_df.columns)
        self.screen_mapping.populate_dropdowns(bom_cols, xy_cols)
        self.screen_mapping.load_mapping(auto_map)
        self.run_process(auto_map)

    def run_process(self, mapping):
        try:
            bom_df = self.screen_import.bom_df
            xy_df = self.screen_import.xy_df
            self.final_df = perform_merge_v2(bom_df, xy_df, mapping)
            self.screen_dashboard.set_data(self.final_df)
            self.stack.setCurrentIndex(2)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Processing Failed:\n{str(e)}")

    def perform_final_export(self, df):
        options = QFileDialog.Options()
        
        # [UPDATED] Use the Saved Download Directory
        default_dir = self.settings.value("download_dir", self._get_default_documents())
        default_path = os.path.join(default_dir, "Production_Output.xlsx")
        
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Output", default_path, "Excel Files (*.xlsx)", options=options)
        if not file_path: return
        if not file_path.lower().endswith('.xlsx'): file_path += '.xlsx'

        try:
            generate_production_files(df, file_path)
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Information)
            msg.setWindowTitle("Success")
            msg.setText("Files Generated Successfully!")
            msg.setInformativeText(f"Saved to: {file_path}")
            btn_open = msg.addButton("Open Folder", QMessageBox.ActionRole)
            msg.addButton(QMessageBox.Ok)
            msg.exec_()
            if msg.clickedButton() == btn_open:
                folder = os.path.dirname(file_path)
                os.startfile(folder)
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to write file:\n{str(e)}")

    def closeEvent(self, event):
        has_files = (self.screen_import.bom_df is not None) or (self.screen_import.xy_df is not None)
        if has_files:
            reply = QMessageBox.question(self, 'Confirm Exit', "You have loaded files. Are you sure you want to exit?\nAny unsaved progress will be lost.", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.Yes: event.accept()
            else: event.ignore()
        else:
            event.accept()