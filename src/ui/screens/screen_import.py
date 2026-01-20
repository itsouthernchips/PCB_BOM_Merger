from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QFileDialog, QFrame, QMessageBox, QGraphicsDropShadowEffect)
from PyQt5.QtCore import pyqtSignal, Qt, QMimeData, QSettings, QStandardPaths
import pandas as pd
import os
import re

class DropZone(QFrame):
    file_dropped = pyqtSignal(str) 

    def __init__(self, title, icon_char, color):
        super().__init__()
        self.setObjectName("DropZone") 
        self.setAcceptDrops(True)
        
        # --- DIMENSIONS ---
        self.setFixedWidth(350)     
        self.setMinimumHeight(320)
        
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
        
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(15)

        # Icon
        lbl_icon = QLabel(icon_char)
        lbl_icon.setStyleSheet(f"font-size: 70px; color: {color}; border: none; background: transparent;")
        lbl_icon.setAlignment(Qt.AlignCenter)
        
        # Title
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("font-size: 18px; font-weight: bold; border: none; background: transparent;")
        lbl_title.setAlignment(Qt.AlignCenter)
        lbl_title.setWordWrap(True)
        
        # Status Label
        self.lbl_status = QLabel("Drag & Drop File Here\n- or -")
        self.lbl_status.setStyleSheet("color: #7f8c8d; font-style: italic; border: none; background: transparent;")
        self.lbl_status.setAlignment(Qt.AlignCenter)

        # Browse Button
        self.btn_browse = QPushButton("Browse File")
        self.btn_browse.setCursor(Qt.PointingHandCursor)
        self.btn_browse.setFixedWidth(140)
        self.btn_browse.setMinimumHeight(35)
        
        layout.addWidget(lbl_icon)
        layout.addWidget(lbl_title)
        layout.addWidget(self.lbl_status)
        layout.addWidget(self.btn_browse)
        self.setLayout(layout)

        # Shadow
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(Qt.lightGray)
        shadow.setOffset(0, 5)
        self.setGraphicsEffect(shadow)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
            self.setProperty("class", "hover")
            self.style().unpolish(self)
            self.style().polish(self)
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self.setProperty("class", "")
        self.style().unpolish(self)
        self.style().polish(self)

    def dropEvent(self, event):
        self.setProperty("class", "")
        self.style().unpolish(self)
        self.style().polish(self)
        
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        if files:
            self.file_dropped.emit(files[0])

    def set_file_active(self, filename):
        self.lbl_status.setText(f"Loaded:\n{filename}")
        self.lbl_status.setStyleSheet("color: #27ae60; font-weight: bold; border: none; background: transparent;")
        self.setProperty("class", "active") 
        self.style().unpolish(self)
        self.style().polish(self)

    def reset(self):
        self.lbl_status.setText("Drag & Drop File Here\n- or -")
        self.lbl_status.setStyleSheet("color: #7f8c8d; font-style: italic; border: none; background: transparent;")
        self.setProperty("class", "")
        self.style().unpolish(self)
        self.style().polish(self)


class ImportScreen(QWidget):
    next_clicked = pyqtSignal()             
    skip_mapping_clicked = pyqtSignal(dict) 

    def __init__(self):
        super().__init__()
        self.bom_df = None
        self.xy_df = None
        # [UPDATED] Settings for paths
        self.settings = QSettings("SCCPL", "BOM_Segregator_V2")
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(50, 40, 50, 50)
        layout.setSpacing(20)
        
        # --- TITLE ---
        header = QLabel("PCB Production Setup")
        header.setStyleSheet("font-size: 26px; font-weight: bold; color: #2c3e50;")
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)
        
        sub_header = QLabel("Upload your Bill of Materials and Centroid Data to begin.")
        sub_header.setStyleSheet("font-size: 14px; color: #7f8c8d;")
        sub_header.setAlignment(Qt.AlignCenter)
        layout.addWidget(sub_header)

        # --- CARDS LAYOUT ---
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(40)
        cards_layout.addStretch()

        # === COLUMN 1: BOM ===
        col_bom = QVBoxLayout()
        col_bom.setSpacing(10)
        
        self.drop_bom = DropZone("Bill of Materials\n(BOM)", "📄", "#3498db")
        self.drop_bom.btn_browse.clicked.connect(self.load_bom_dialog)
        self.drop_bom.file_dropped.connect(self.process_bom_file)
        
        # Download BOM Template Button
        self.btn_dl_bom = QPushButton("Download BOM Template (.xlsx)")
        self.btn_dl_bom.setCursor(Qt.PointingHandCursor)
        self.btn_dl_bom.setFixedHeight(40)
        self.btn_dl_bom.setStyleSheet("""
            QPushButton {
                background-color: white;
                color: #3498db;
                border: 1px solid #3498db;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #f0f8ff; }
        """)
        self.btn_dl_bom.clicked.connect(self.download_bom_template)

        col_bom.addWidget(self.drop_bom)
        col_bom.addWidget(self.btn_dl_bom)
        cards_layout.addLayout(col_bom)


        # === COLUMN 2: XY ===
        col_xy = QVBoxLayout()
        col_xy.setSpacing(10)

        self.drop_xy = DropZone("XY / Pick & Place\n(Centroid)", "⌖", "#e74c3c")
        self.drop_xy.btn_browse.clicked.connect(self.load_xy_dialog)
        self.drop_xy.file_dropped.connect(self.process_xy_file)
        
        # Download XY Template Button
        self.btn_dl_xy = QPushButton("Download XY Template (.xlsx)")
        self.btn_dl_xy.setCursor(Qt.PointingHandCursor)
        self.btn_dl_xy.setFixedHeight(40)
        self.btn_dl_xy.setStyleSheet("""
            QPushButton {
                background-color: white;
                color: #e74c3c;
                border: 1px solid #e74c3c;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #fff0f0; }
        """)
        self.btn_dl_xy.clicked.connect(self.download_xy_template)

        col_xy.addWidget(self.drop_xy)
        col_xy.addWidget(self.btn_dl_xy)
        cards_layout.addLayout(col_xy)

        cards_layout.addStretch() 
        layout.addLayout(cards_layout)

        # --- ACTION BAR ---
        action_layout = QHBoxLayout()
        
        self.btn_reset = QPushButton("Reset All")
        self.btn_reset.setFixedWidth(120)
        self.btn_reset.setMinimumHeight(40)
        self.btn_reset.clicked.connect(self.reset_state)
        
        self.btn_process = QPushButton("Start Processing >>")
        self.btn_process.setProperty("class", "primary")
        self.btn_process.setMinimumHeight(50)
        self.btn_process.setMinimumWidth(220)
        self.btn_process.clicked.connect(self.validate_and_proceed)

        action_layout.addWidget(self.btn_reset)
        action_layout.addStretch()
        action_layout.addWidget(self.btn_process)
        
        layout.addStretch() 
        layout.addLayout(action_layout)
        
        self.setLayout(layout)

    # --- LOGIC ---
    def _get_default_docs(self):
        return QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation)

    def load_bom_dialog(self):
        # [UPDATED] Use Settings
        default_dir = self.settings.value("upload_dir", self._get_default_docs())
        path, _ = QFileDialog.getOpenFileName(self, "Open BOM", default_dir, "Data Files (*.csv *.xlsx *.xls *.txt)")
        if path: self.process_bom_file(path)

    def load_xy_dialog(self):
        default_dir = self.settings.value("upload_dir", self._get_default_docs())
        path, _ = QFileDialog.getOpenFileName(self, "Open XY", default_dir, "Data Files (*.csv *.xlsx *.xls *.txt)")
        if path: self.process_xy_file(path)

    def process_bom_file(self, path):
        try:
            self.bom_df = self._read_file(path)
            self.drop_bom.set_file_active(os.path.basename(path))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Invalid BOM File:\n{str(e)}")

    def process_xy_file(self, path):
        try:
            self.xy_df = self._read_file(path)
            self.drop_xy.set_file_active(os.path.basename(path))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Invalid XY File:\n{str(e)}")

    def reset_state(self):
        self.bom_df = None
        self.xy_df = None
        self.drop_bom.reset()
        self.drop_xy.reset()

    def _read_file(self, path):
        ext = path.split('.')[-1].lower()
        if ext == 'csv' or ext == 'txt':
            return pd.read_csv(path, sep=',', dtype=str).fillna("")
        elif ext in ['xlsx', 'xls']:
            return pd.read_excel(path, dtype=str).fillna("")
        raise ValueError("Unsupported format")

    # --- EXCEL TEMPLATE GENERATION ---
    def download_bom_template(self):
        # [UPDATED] Reordered: Mounting Type before Points
        headers = ["Part.No.", "Description", "Location", "Quantity", "Mounting Type", "Points"]
        widths = [20, 35, 30, 10, 15, 10] 
        
        # [UPDATED] Use Settings
        default_dir = self.settings.value("download_dir", self._get_default_docs())
        default_path = os.path.join(default_dir, "BOM_Template.xlsx")
        self._generate_excel_template(default_path, headers, widths)

    def download_xy_template(self):
        headers = ["Location", "Center-X", "Center-Y", "Rotation", "Layer"]
        widths = [20, 15, 15, 15, 15]
        
        default_dir = self.settings.value("download_dir", self._get_default_docs())
        default_path = os.path.join(default_dir, "XY_Template.xlsx")
        self._generate_excel_template(default_path, headers, widths)

    def _generate_excel_template(self, default_name, headers, widths):
        path, _ = QFileDialog.getSaveFileName(self, "Save Template", default_name, "Excel Files (*.xlsx)")
        if not path:
            return

        try:
            writer = pd.ExcelWriter(path, engine='xlsxwriter')
            workbook = writer.book
            
            df = pd.DataFrame(columns=headers)
            df.to_excel(writer, sheet_name='Sheet1', index=False, startrow=0)
            
            worksheet = writer.sheets['Sheet1']
            
            header_fmt = workbook.add_format({
                'bold': True,
                'bg_color': '#BDD7EE',
                'border': 1,
                'align': 'center',
                'valign': 'vcenter'
            })
            
            for i, (col_name, width) in enumerate(zip(headers, widths)):
                worksheet.write(0, i, col_name, header_fmt)
                worksheet.set_column(i, i, width)
                
            writer.close()
            QMessageBox.information(self, "Success", f"Template saved to:\n{path}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not save template:\n{str(e)}")

    def validate_and_proceed(self):
        if self.bom_df is None or self.xy_df is None:
            QMessageBox.warning(self, "Incomplete", "Please upload both BOM and XY files.")
            return

        # --- SMART SKIP LOGIC ---
        def clean_header(h): return re.sub(r"[^a-zA-Z0-9]", "", str(h).lower())
        
        bom_map = {clean_header(c): c for c in self.bom_df.columns}
        xy_map  = {clean_header(c): c for c in self.xy_df.columns}

        reqs = {
            "Part No.":    (["partno", "partnumber", "part", "component"], bom_map),
            "Description": (["description", "desc", "value", "comment"], bom_map),
            "Quantity":    (["quantity", "qty"], bom_map),
            "BOM Location Col":(["location", "designator", "refdes", "ref", "reference"], bom_map),
            "Points": (["points", "pins", "leads", "pads", "solderpoints"], bom_map),
            "Mounting Type": (["mountingtype", "mount", "type", "tech", "technology", "package"], bom_map),

            "Center-X":    (["centerx", "midx", "refx", "x", "xmm", "xmil"], xy_map),
            "Center-Y":    (["centery", "midy", "refy", "y", "ymm", "ymil"], xy_map),
            "Rotation":    (["rotation", "rot", "angle"], xy_map),
            "Layer":       (["layer", "side", "layers"], xy_map),
            "XY Location Col": (["location", "designator", "refdes", "ref", "reference"], xy_map)
        }

        found_map = {}
        missing = False
        for key, (aliases, source_map) in reqs.items():
            match = next((source_map[a] for a in aliases if a in source_map), None)
            if match: found_map[key] = match
            else: missing = True

        if not missing:
            self.skip_mapping_clicked.emit(found_map)
        else:
            self.next_clicked.emit()