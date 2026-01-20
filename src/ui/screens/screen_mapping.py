from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, 
                             QLabel, QComboBox, QPushButton, QGroupBox, QMessageBox)
from PyQt5.QtCore import pyqtSignal, Qt

class MappingScreen(QWidget):
    next_clicked = pyqtSignal(dict)
    back_clicked = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.mapping_widgets = {} 
        self.bom_columns = []
        self.xy_columns = []
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(20)
        
        # --- HEADER ---
        header = QLabel("Step 2: Map Columns")
        header.setStyleSheet("font-size: 18px; font-weight: bold; color: #2c3e50;")
        layout.addWidget(header)

        # ==========================================
        # SECTION 1: CRITICAL SYNC KEYS
        # ==========================================
        sync_group = QGroupBox("1. Synchronization Keys (Critical)")
        sync_group.setStyleSheet("""
            QGroupBox { 
                border: 2px solid #3498db; 
                border-radius: 8px; 
                margin-top: 20px;
                font-size: 14px;
                color: #2980b9;
                background-color: #f0f8ff;
            }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
        """)
        sync_layout = QGridLayout()
        sync_layout.setVerticalSpacing(15)
        
        sync_layout.addWidget(QLabel("Target Field"), 0, 0)
        sync_layout.addWidget(QLabel("Source File"), 0, 1)
        sync_layout.addWidget(QLabel("Select Column"), 0, 2)
        sync_layout.addWidget(QLabel("Status"), 0, 3)

        self._add_row(sync_layout, 1, "BOM Location Col", "BOM", is_critical=True)
        self._add_row(sync_layout, 2, "XY Location Col", "XY", is_critical=True)
        
        sync_group.setLayout(sync_layout)
        layout.addWidget(sync_group)

        # ==========================================
        # SECTION 2: DATA FIELDS
        # ==========================================
        data_group = QGroupBox("2. Data Fields")
        data_layout = QHBoxLayout()
        
        # --- LEFT: XY DATA ---
        left_widget = QWidget()
        left_grid = QGridLayout()
        left_grid.addWidget(QLabel("<b>XY Data Points</b>"), 0, 0, 1, 3)
        
        self._add_row(left_grid, 1, "Center-X", "XY")
        self._add_row(left_grid, 2, "Center-Y", "XY")
        self._add_row(left_grid, 3, "Layer", "XY")
        self._add_row(left_grid, 4, "Rotation", "XY")
        
        left_widget.setLayout(left_grid)
        
        # --- RIGHT: BOM DATA ---
        right_widget = QWidget()
        right_grid = QGridLayout()
        right_grid.addWidget(QLabel("<b>BOM Data Points</b>"), 0, 0, 1, 3)
        
        self._add_row(right_grid, 1, "Part No.", "BOM")
        self._add_row(right_grid, 2, "Description", "BOM")
        self._add_row(right_grid, 3, "Quantity", "BOM")
        # [UPDATED] Added new fields
        self._add_row(right_grid, 4, "Points", "BOM")
        self._add_row(right_grid, 5, "Mounting Type", "BOM")
        
        right_widget.setLayout(right_grid)

        data_layout.addWidget(left_widget)
        # Vertical Separator
        line = QLabel()
        line.setFixedWidth(2)
        line.setStyleSheet("background-color: #e0e0e0;")
        data_layout.addWidget(line)
        data_layout.addWidget(right_widget)
        
        data_group.setLayout(data_layout)
        layout.addWidget(data_group)

        # --- NAVIGATION ---
        layout.addStretch()
        nav_layout = QHBoxLayout()
        
        self.btn_back = QPushButton("<< Back")
        self.btn_back.clicked.connect(self.back_clicked.emit)
        
        self.btn_next = QPushButton("Validate & Process >>")
        self.btn_next.setProperty("class", "primary") 
        self.btn_next.clicked.connect(self.finalize_mapping)
        
        nav_layout.addWidget(self.btn_back)
        nav_layout.addStretch()
        nav_layout.addWidget(self.btn_next)
        
        layout.addLayout(nav_layout)
        self.setLayout(layout)

    def _add_row(self, grid, row_idx, field_name, source, is_critical=False):
        lbl = QLabel(field_name)
        if is_critical:
            lbl.setStyleSheet("font-weight: bold; color: #2c3e50;")
        
        badge = QLabel(source)
        color = "#2c3e50" if source == "BOM" else "#c0392b"
        badge.setStyleSheet(f"color: white; background-color: {color}; padding: 3px 8px; border-radius: 4px; font-weight: bold;")
        badge.setFixedWidth(50)
        badge.setAlignment(Qt.AlignCenter)

        combo = QComboBox()
        combo.setMinimumWidth(200)
        
        status_lbl = QLabel("")
        status_lbl.setFixedWidth(30)
        
        combo.currentIndexChanged.connect(lambda: self._update_status(combo, status_lbl))

        grid.addWidget(lbl, row_idx, 0)
        grid.addWidget(badge, row_idx, 1)
        grid.addWidget(combo, row_idx, 2)
        grid.addWidget(status_lbl, row_idx, 3)

        self.mapping_widgets[field_name] = (combo, status_lbl, source)

    def _update_status(self, combo, label):
        text = combo.currentText()
        if text and text != "-- Select Column --":
            label.setText("✅")
        else:
            label.setText("❌")

    def populate_dropdowns(self, bom_cols, xy_cols):
        self.bom_columns = bom_cols
        self.xy_columns = xy_cols

        for field, (combo, status_lbl, source) in self.mapping_widgets.items():
            combo.blockSignals(True) 
            combo.clear()
            combo.addItem("-- Select Column --")
            
            choices = self.bom_columns if source == "BOM" else self.xy_columns
            combo.addItems(choices)
            
            self._auto_select(combo, field, choices)
            self._update_status(combo, status_lbl)
            combo.blockSignals(False)

    def _auto_select(self, combo, target_field, choices):
        t_clean = target_field.lower().replace("-", "").replace(".", "").replace(" ", "")
        if "location" in t_clean: t_clean = "designator"

        for index, choice in enumerate(choices):
            c_clean = choice.lower().replace("-", "").replace(".", "").replace(" ", "")
            if t_clean == c_clean or t_clean in c_clean:
                combo.setCurrentIndex(index + 1)
                return

    def load_mapping(self, mapping_dict):
        for field, (combo, status_lbl, source) in self.mapping_widgets.items():
            if field in mapping_dict:
                target_value = mapping_dict[field]
                index = combo.findText(target_value)
                if index >= 0:
                    combo.setCurrentIndex(index)
                    self._update_status(combo, status_lbl)

    def finalize_mapping(self):
        final_map = {}
        for field, (combo, _, _) in self.mapping_widgets.items():
            selected = combo.currentText()
            final_map[field] = selected if selected != "-- Select Column --" else None
        
        if not final_map.get("BOM Location Col") or not final_map.get("XY Location Col"):
            QMessageBox.warning(self, "Validation Error", "The 'Synchronization Keys' (Location Columns) are mandatory.")
            return

        self.next_clicked.emit(final_map)