from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
                             QTableWidgetItem, QLabel, QPushButton, QHeaderView, 
                             QTabWidget, QAbstractItemView, QMessageBox, QFrame)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QColor
import pandas as pd

class DashboardScreen(QWidget):
    back_clicked = pyqtSignal()
    export_clicked = pyqtSignal(object) 

    def __init__(self):
        super().__init__()
        self.full_df = pd.DataFrame()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # --- HEADER ---
        header_layout = QHBoxLayout()
        title_lbl = QLabel("Production Dashboard")
        title_lbl.setStyleSheet("font-size: 20px; font-weight: bold; color: #2c3e50;")
        
        self.lbl_subtitle = QLabel("Preview of final output. 'Exceptions' can be edited.")
        self.lbl_subtitle.setStyleSheet("color: #7f8c8d; font-style: italic;")
        
        header_layout.addWidget(title_lbl)
        header_layout.addStretch()
        header_layout.addWidget(self.lbl_subtitle)
        layout.addLayout(header_layout)

        # --- TABS ---
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #bdc3c7; top: -1px; }
            QTabBar::tab {
                background: #ecf0f1;
                border: 1px solid #bdc3c7;
                padding: 8px 15px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                font-weight: bold;
                color: #7f8c8d;
                min-width: 100px;
            }
            QTabBar::tab:selected {
                background: #BDD7EE; 
                border-bottom-color: #BDD7EE;
                color: #2c3e50;
            }
        """)

        # Define Tabs
        self.tables = {}
        tab_defs = [
            ("Internal BOM", "Internal BOM"),
            ("XY Data", "XY Data"),
            ("BOM Top", "BOM Top"),
            ("BOM Bottom", "BOM Bottom"),
            ("XY Top", "XY Top"),
            ("XY Bottom", "XY Bottom"),
            ("Summary", "Summary"),
            ("Exceptions", "Exceptions Report")
        ]

        for key, title in tab_defs:
            tab = QWidget()
            t_layout = QVBoxLayout(tab)
            t_layout.setContentsMargins(0,0,0,0)
            
            is_editable = (key == "Exceptions")
            table = self._create_table(editable=is_editable)
            
            if is_editable:
                table.itemChanged.connect(self.handle_exception_edit)
            
            self.tables[key] = table
            t_layout.addWidget(table)
            self.tabs.addTab(tab, title)

        layout.addWidget(self.tabs)

        # --- FOOTER ---
        footer = QHBoxLayout()
        
        btn_back = QPushButton("<< Adjust Mapping")
        btn_back.setFixedWidth(180)
        btn_back.clicked.connect(self.back_clicked.emit)
        
        self.btn_refresh = QPushButton("Reprocess Changes")
        self.btn_refresh.setFixedWidth(180)
        self.btn_refresh.setCursor(Qt.PointingHandCursor)
        self.btn_refresh.setStyleSheet("color: #d35400; border: 1px solid #d35400;")
        self.btn_refresh.clicked.connect(self.reprocess_data)
        
        btn_export = QPushButton("Export to Excel >>")
        btn_export.setFixedWidth(200)
        btn_export.setProperty("class", "primary")
        btn_export.clicked.connect(self.finalize_export)
        
        footer.addWidget(btn_back)
        footer.addStretch()
        footer.addWidget(self.btn_refresh)
        footer.addStretch()
        footer.addWidget(btn_export)
        
        layout.addLayout(footer)
        self.setLayout(layout)

    def _create_table(self, editable=False):
        table = QTableWidget()
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setSelectionMode(QAbstractItemView.SingleSelection)
        table.verticalHeader().setVisible(False)
        
        table.setStyleSheet("""
            QTableWidget {
                gridline-color: #ecf0f1;
                border: none;
            }
            QTableWidget::item {
                padding-left: 5px;
                padding-right: 5px;
            }
        """)
        
        font = QFont()
        font.setPointSize(10)
        table.setFont(font)
        
        header = table.horizontalHeader()
        header.setStyleSheet("""
            QHeaderView::section {
                background-color: #BDD7EE;
                color: #2c3e50;
                font-weight: bold;
                border: 1px solid #bdc3c7;
                padding: 4px;
                height: 35px;
            }
        """)
        header.setStretchLastSection(True)

        if not editable:
            table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        else:
            table.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed)
            
        return table

    def set_data(self, df):
        self.full_df = df.copy()
        
        if "_id" not in self.full_df.columns:
            self.full_df["_id"] = range(len(self.full_df))

        if "Remarks" not in self.full_df.columns:
            self.full_df["Remarks"] = ""
            
        if 'Layer' in self.full_df.columns:
            self.full_df['Layer_Classified'] = self.full_df['Layer'].apply(self._classify_layer)
        else:
            self.full_df['Layer_Classified'] = "Unknown"

        self.refresh_views()
        self._validate_mounting_types()

    def _validate_mounting_types(self):
        if "Mounting Type" not in self.full_df.columns: return

        invalid_types = self.full_df[
            (~self.full_df["Mounting Type"].isin(["SMD", "THT"])) & 
            (self.full_df["Mounting Type"] != "")
        ]["Mounting Type"].unique()

        if len(invalid_types) > 0:
            QMessageBox.warning(self, "Invalid Data Detected", 
                f"Strict Warning: The 'Mounting Type' column contains invalid values.\n\n"
                f"Found: {', '.join(invalid_types)}\n\n"
                "Allowed values are strictly 'SMD' or 'THT'.\n"
                "Please fix this in the source file or the Summary Report will be inaccurate.")

    def _classify_layer(self, val):
        s = str(val).strip().lower()
        if s in ['b', 'bottom', 'bot', 'bottomlayer', 'bottom layer', 'back', 'solder']: return 'Bottom'
        if s in ['t', 'top', 'toplayer', 'top layer', 'front', 'component']: return 'Top'
        return 'Unknown'

    def _group_bom_data(self, df, calc_total_points=False):
        if df.empty: return df
        
        df = df.copy()  # Ensure we work with a copy, not a view
        fill_cols = ['Part Number', 'Description', 'Points', 'Mounting Type']
        for c in fill_cols:
            if c in df.columns: df[c] = df[c].fillna('')

        valid_group_cols = [c for c in fill_cols if c in df.columns]
        if not valid_group_cols: return df

        agg_rules = {}
        if 'Location' in df.columns: agg_rules['Location'] = lambda x: ', '.join(sorted(x.astype(str)))
        elif 'Ref Des' in df.columns: agg_rules['Ref Des'] = lambda x: ', '.join(sorted(x.astype(str)))
        else: agg_rules['Designator'] = lambda x: ', '.join(sorted(x.astype(str)))

        if 'BOM_Order' in df.columns: agg_rules['BOM_Order'] = 'min'

        grouped = df.groupby(valid_group_cols).agg(agg_rules).reset_index()
        
        for potential in ['Ref Des', 'Designator']:
            if potential in grouped.columns:
                grouped.rename(columns={potential: 'Location'}, inplace=True)

        if 'Location' in grouped.columns:
            grouped['Quantity'] = grouped['Location'].apply(lambda x: len(str(x).split(',')))
            
        if calc_total_points and 'Points' in grouped.columns:
            grouped['Total Points'] = 0
            def calc_pts(row):
                try:
                    p = float(str(row['Points']).strip())
                    q = float(row['Quantity'])
                    return int(p * q)
                except:
                    return 0 
            grouped['Total Points'] = grouped.apply(calc_pts, axis=1)
        
        return grouped

    def refresh_views(self):
        df = self.full_df
        df_top_all = df[df['Layer_Classified'] == 'Top'].copy()
        df_bot_all = df[df['Layer_Classified'] == 'Bottom'].copy()

        # 1. Internal BOM [UPDATED ORDER]
        df_internal = df[df['Status'] != 'XY_ONLY'].copy()
        df_int_grp = self._group_bom_data(df_internal, calc_total_points=True)
        # Part Number, Description, Location, Quantity, Mounting Type, Points
        cols_int = ['Sl No.', 'Part Number', 'Description', 'Location', 'Quantity', 'Mounting Type', 'Points']
        self._fill_table("Internal BOM", df_int_grp, cols_int, add_sl=True)

        # 2. XY Data
        df_xy = df[df['Status'] != 'BOM_ONLY'].copy()
        disp_xy = df_xy.rename(columns={'Ref Des': 'Location', 'Ref X': 'X', 'Ref Y': 'Y'})
        self._fill_table("XY Data", disp_xy, ['X', 'Y', 'Location', 'Rotation', 'Layer'])

        # 3. BOM Top [UPDATED ORDER]
        df_btop = df_top_all[df_top_all['Status'] != 'XY_ONLY'].copy()
        df_btop_grp = self._group_bom_data(df_btop, calc_total_points=True)
        df_btop_grp['Layer'] = "TopLayer"
        # Part Number, Description, Location, Quantity, Mounting Type, Points, Total Points
        cols_final = ['Sl No.', 'Part Number', 'Description', 'Location', 'Quantity', 'Mounting Type', 'Points', 'Total Points', 'Layer']
        self._fill_table("BOM Top", df_btop_grp, cols_final, add_sl=True)

        # 4. BOM Bottom [UPDATED ORDER]
        df_bbot = df_bot_all[df_bot_all['Status'] != 'XY_ONLY'].copy()
        df_bbot_grp = self._group_bom_data(df_bbot, calc_total_points=True)
        df_bbot_grp['Layer'] = "BottomLayer"
        self._fill_table("BOM Bottom", df_bbot_grp, cols_final, add_sl=True)

        # 5. XY Top
        df_xyt = df_top_all[df_top_all['Status'] != 'BOM_ONLY'].copy()
        df_xyt['Layer'] = "TopLayer"
        disp_xyt = df_xyt.rename(columns={'Ref Des': 'Location', 'Ref X': 'X', 'Ref Y': 'Y'})
        self._fill_table("XY Top", disp_xyt, ['Sl No.', 'Part Number', 'Location', 'X', 'Y', 'Rotation', 'Description', 'Layer'], add_sl=True)

        # 6. XY Bottom
        df_xyb = df_bot_all[df_bot_all['Status'] != 'BOM_ONLY'].copy()
        df_xyb['Layer'] = "BottomLayer"
        disp_xyb = df_xyb.rename(columns={'Ref Des': 'Location', 'Ref X': 'X', 'Ref Y': 'Y'})
        self._fill_table("XY Bottom", disp_xyb, ['Sl No.', 'Part Number', 'Location', 'X', 'Y', 'Rotation', 'Description', 'Layer'], add_sl=True)

        # 7. Summary
        self._populate_summary(df)

        # 8. Exceptions
        mask_error = (df['Status'] != 'MATCHED') & (df['Is Ignored'] == False)
        df_errors = df[mask_error].copy()
        df_errors['Issue Type'] = "Unknown Error"
        df_errors.loc[df_errors['Status'] == 'XY_ONLY', 'Issue Type'] = 'On Board, Not in BOM'
        df_errors.loc[df_errors['Status'] == 'BOM_ONLY', 'Issue Type'] = 'In BOM, Not on Board'
        
        if 'Ref Des' in df_errors.columns:
            df_errors.rename(columns={'Ref Des': 'Location'}, inplace=True)

        self._fill_table("Exceptions", df_errors, ['Location', 'Issue Type', 'Part Number', 'Layer', 'Description', 'Remarks'])

    def _populate_summary(self, df):
        valid_mask = df['Status'] != 'XY_ONLY'
        df_clean = df[valid_mask].copy()

        summary_data = []
        for mount_type in ["SMD", "THT"]:
            type_mask = df_clean['Mounting Type'] == mount_type
            df_type = df_clean[type_mask]
            
            # Top Layer - Group by Part Number
            df_top = df_type[df_type['Layer_Classified'] == 'Top']
            df_top_grouped = self._group_bom_data(df_top, calc_total_points=True)
            top_line_items = len(df_top_grouped)
            top_qty = pd.to_numeric(df_top_grouped['Quantity'], errors='coerce').fillna(0).sum()
            top_points = pd.to_numeric(df_top_grouped['Total Points'], errors='coerce').fillna(0).sum()
            
            # Bottom Layer - Group by Part Number
            df_bottom = df_type[df_type['Layer_Classified'] == 'Bottom']
            df_bottom_grouped = self._group_bom_data(df_bottom, calc_total_points=True)
            bot_line_items = len(df_bottom_grouped)
            bot_qty = pd.to_numeric(df_bottom_grouped['Quantity'], errors='coerce').fillna(0).sum()
            bot_points = pd.to_numeric(df_bottom_grouped['Total Points'], errors='coerce').fillna(0).sum()
            
            # Totals
            total_line_items = top_line_items + bot_line_items
            total_qty = top_qty + bot_qty
            total_points = top_points + bot_points
            
            summary_data.append({
                "Type": f"{mount_type} - Top",
                "Line Items": top_line_items,
                "Components": int(top_qty),
                "Total Points": int(top_points)
            })
            summary_data.append({
                "Type": f"{mount_type} - Bottom",
                "Line Items": bot_line_items,
                "Components": int(bot_qty),
                "Total Points": int(bot_points)
            })
            summary_data.append({
                "Type": "TOTAL",
                "Line Items": total_line_items,
                "Components": int(total_qty),
                "Total Points": int(total_points)
            })
            summary_data.append({
                "Type": "",
                "Line Items": "",
                "Components": "",
                "Total Points": ""
            })

        df_summ = pd.DataFrame(summary_data)
        self._fill_table("Summary", df_summ, ["Type", "Line Items", "Components", "Total Points"])

    def _fill_table(self, key, df, columns, add_sl=False):
        table = self.tables[key]
        table.blockSignals(True)
        table.clear()
        
        if add_sl and not df.empty:
            df = df.copy()
            df.reset_index(drop=True, inplace=True)
            df['Sl No.'] = df.index + 1
        
        for c in columns:
            if c not in df.columns: df[c] = ""
            
        table.setColumnCount(len(columns))
        table.setRowCount(len(df))
        table.setHorizontalHeaderLabels(columns)

        if key == "Exceptions":
            self.exc_row_map = {}

        for r_idx, (df_idx, row) in enumerate(df.iterrows()):
            if key == "Exceptions":
                self.exc_row_map[r_idx] = row["_id"]

            for c_idx, col in enumerate(columns):
                val = str(row[col]) if pd.notna(row[col]) else ""
                item = QTableWidgetItem(val)
                
                if col in ["Sl No.", "Quantity", "Points", "Total Points", "Count", "Rotation"]:
                    item.setTextAlignment(Qt.AlignCenter)
                else:
                    item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                
                table.setItem(r_idx, c_idx, item)
        
        # Column Sizing
        header = table.horizontalHeader()
        
        if key in ["Internal BOM", "BOM Top", "BOM Bottom"]:
            for i, col in enumerate(columns):
                if col in ["Sl No.", "Quantity", "Points", "Total Points"]:
                    header.setSectionResizeMode(i, QHeaderView.Fixed)
                    table.setColumnWidth(i, 80)
                elif col == "Description":
                    header.setSectionResizeMode(i, QHeaderView.Stretch)
                else:
                    header.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        
        else:
            for i in range(len(columns)):
                header.setSectionResizeMode(i, QHeaderView.Stretch)
                
        table.blockSignals(False)

    def handle_exception_edit(self, item):
        row = item.row()
        col = item.column()
        
        if row not in self.exc_row_map: return
        record_id = self.exc_row_map[row]
        
        table = self.tables["Exceptions"]
        col_name = table.horizontalHeaderItem(col).text()
        
        if col_name == "Location": df_col = "Ref Des"
        else: df_col = col_name

        new_val = item.text()
        
        if df_col not in self.full_df.columns and col_name == "Location":
             if "Ref Des" in self.full_df.columns: df_col = "Ref Des"
             elif "Designator" in self.full_df.columns: df_col = "Designator"

        idx = self.full_df.index[self.full_df["_id"] == record_id].tolist()
        if idx:
            if df_col not in self.full_df.columns:
                self.full_df[df_col] = ""
            self.full_df.at[idx[0], df_col] = new_val

    def reprocess_data(self):
        if 'Layer' in self.full_df.columns:
            self.full_df['Layer_Classified'] = self.full_df['Layer'].apply(self._classify_layer)
        self.refresh_views()
        QMessageBox.information(self, "Refreshed", "Dashboard updated based on edits.")

    def finalize_export(self):
        export_df = self.full_df.drop(columns=["_id", "Layer_Classified"], errors="ignore")
        self.export_clicked.emit(export_df)