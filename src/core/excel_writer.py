import pandas as pd
import xlsxwriter

def generate_production_files(df, output_path):
    """
    Generates the PCB Production Workbook.
    Version: 5.5 (Reordered Columns per Spec)
    """
    writer = pd.ExcelWriter(output_path, engine='xlsxwriter')
    workbook = writer.book
    
    # --- STYLES ---
    header_fmt = workbook.add_format({
        'bold': True, 
        'bg_color': '#BDD7EE', 
        'border': 1,
        'align': 'center',
        'valign': 'vcenter'
    })
    
    wrap_fmt = workbook.add_format({
        'text_wrap': True, 
        'border': 1,
        'valign': 'top'
    })
    
    center_fmt = workbook.add_format({
        'align': 'center', 
        'border': 1
    })

    # --- SAFETY FIX: ENSURE COLUMNS EXIST ---
    required_cols = ['Mounting Type', 'Points', 'Part Number', 'Description', 'Layer']
    for col in required_cols:
        if col not in df.columns:
            df[col] = ""

    # --- DATA PREP ---
    cols_numeric = ['Ref X', 'Ref Y', 'Rotation', 'Points']
    for c in cols_numeric:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors='coerce')

    if 'Layer' in df.columns:
        df['Layer_Classified'] = df['Layer'].apply(_classify_layer)
    else:
        df['Layer_Classified'] = "Unknown"

    df_top_all = df[df['Layer_Classified'] == 'Top'].copy()
    df_bot_all = df[df['Layer_Classified'] == 'Bottom'].copy()
    
    if 'Part Number' in df.columns:
        df['Part Number'] = df['Part Number'].fillna("")
        mask_blank = df['Part Number'].astype(str).str.strip() == ""
        df.loc[mask_blank, 'Part Number'] = "DNP"

    # --- TAB 1: INTERNAL BOM ---
    df_internal = df[df['Status'] != 'XY_ONLY'].copy()
    df_internal_grouped = _group_bom_data(df_internal, calc_total_points=False)
    df_internal_grouped.rename(columns={'Designator': 'Location'}, inplace=True)
    
    # [UPDATED ORDER]
    # Part Number, Description, Location, Quantity, Mounting Type, Points
    cols_int = ['Part Number', 'Description', 'Location', 'Quantity', 'Mounting Type', 'Points']
    
    _write_custom_sheet(writer, df_internal_grouped, "Internal BOM", cols_int,
                        header_fmt, wrap_fmt, center_fmt, sort_by_bom_order=True)

    # --- TAB 2: XY DATA ---
    df_xy_master = df[df['Status'] != 'BOM_ONLY'].copy()
    df_xy_master.rename(columns={'Ref Des': 'Location', 'Ref X': 'X', 'Ref Y': 'Y'}, inplace=True)
    
    _write_custom_sheet(writer, df_xy_master, "XY Data", 
                        ['Location', 'X', 'Y', 'Rotation', 'Layer'], 
                        header_fmt, wrap_fmt, center_fmt, sort_by_bom_order=False)

    # --- TAB 3: BOM TOP ---
    df_bom_top = df_top_all[df_top_all['Status'] != 'XY_ONLY'].copy()
    df_bom_top_grouped = _group_bom_data(df_bom_top, calc_total_points=True)
    df_bom_top_grouped['Layer'] = "TopLayer"
    df_bom_top_grouped.rename(columns={'Designator': 'Location'}, inplace=True)
    
    # [UPDATED ORDER]
    # Sl No., Part Number, Description, Location, Quantity, Mounting Type, Points, Total Points, Layer
    cols_top = ['Sl No.', 'Part Number', 'Description', 'Location', 'Quantity', 'Mounting Type', 'Points', 'Total Points', 'Layer']
    
    _write_custom_sheet(writer, df_bom_top_grouped, "BOM Top", cols_top, 
                        header_fmt, wrap_fmt, center_fmt, sort_by_bom_order=True, add_sl_no=True)

    # --- TAB 4: BOM BOTTOM ---
    df_bom_bot = df_bot_all[df_bot_all['Status'] != 'XY_ONLY'].copy()
    df_bom_bot_grouped = _group_bom_data(df_bom_bot, calc_total_points=True)
    df_bom_bot_grouped['Layer'] = "BottomLayer"
    df_bom_bot_grouped.rename(columns={'Designator': 'Location'}, inplace=True)
    
    # [UPDATED ORDER]
    # Sl No., Part Number, Description, Location, Quantity, Mounting Type, Points, Total Points, Layer
    cols_bot = ['Sl No.', 'Part Number', 'Description', 'Location', 'Quantity', 'Mounting Type', 'Points', 'Total Points', 'Layer']
    
    _write_custom_sheet(writer, df_bom_bot_grouped, "BOM Bottom", cols_bot, 
                        header_fmt, wrap_fmt, center_fmt, sort_by_bom_order=True, add_sl_no=True)

    # --- TAB 5: XY TOP ---
    df_xy_top = df_top_all[df_top_all['Status'] != 'BOM_ONLY'].copy()
    df_xy_top['Layer'] = "TopLayer"
    df_xy_top.rename(columns={'Ref Des': 'Location', 'Ref X': 'X', 'Ref Y': 'Y'}, inplace=True)
    
    _write_custom_sheet(writer, df_xy_top, "XY Top", 
                        ['Sl No.', 'Part Number', 'Location', 'X', 'Y', 'Rotation', 'Description', 'Layer'], 
                        header_fmt, wrap_fmt, center_fmt, sort_by_bom_order=True, add_sl_no=True)

    # --- TAB 6: XY BOTTOM ---
    df_xy_bot = df_bot_all[df_bot_all['Status'] != 'BOM_ONLY'].copy()
    df_xy_bot['Layer'] = "BottomLayer"
    df_xy_bot.rename(columns={'Ref Des': 'Location', 'Ref X': 'X', 'Ref Y': 'Y'}, inplace=True)
    
    _write_custom_sheet(writer, df_xy_bot, "XY Bottom", 
                        ['Sl No.', 'Part Number', 'Location', 'X', 'Y', 'Rotation', 'Description', 'Layer'], 
                        header_fmt, wrap_fmt, center_fmt, sort_by_bom_order=True, add_sl_no=True)

    # --- TAB 7: SUMMARY SHEET ---
    _write_summary_sheet(writer, df, header_fmt, center_fmt)

    # --- TAB 8: EXCEPTIONS REPORT ---
    mask_error = (df['Status'] != 'MATCHED') & (df['Is Ignored'] == False)
    df_errors = df[mask_error].copy()
    df_errors['Issue Type'] = "Unknown Error"
    df_errors.loc[df_errors['Status'] == 'XY_ONLY', 'Issue Type'] = 'On Board but Missing from BOM (DNP?)'
    df_errors.loc[df_errors['Status'] == 'BOM_ONLY', 'Issue Type'] = 'In BOM but Missing from Board'
    
    df_errors.rename(columns={'Ref Des': 'Location'}, inplace=True)
    
    cols_err = ['Location', 'Issue Type', 'Part Number', 'Layer', 'Description', 'Remarks']
    
    _write_custom_sheet(writer, df_errors, "Exceptions Report", cols_err, 
                        header_fmt, wrap_fmt, center_fmt, sort_by_bom_order=True, add_sl_no=False)
    
    if not df_errors.empty:
        ws = writer.sheets['Exceptions Report']
        ws.set_tab_color('#C00000')

    writer.close()
    return output_path

def _classify_layer(val):
    s = str(val).strip().lower()
    if s in ['b', 'bottom', 'bot', 'bottomlayer', 'bottom layer', 'back', 'solder']: return 'Bottom'
    if s in ['t', 'top', 'toplayer', 'top layer', 'front', 'component']: return 'Top'
    return 'Unknown'

def _group_bom_data(df, calc_total_points=False):
    if df.empty: return df
    
    # Group by Part Number + Mounting Type + Points
    fill_cols = ['Part Number', 'Description', 'Points', 'Mounting Type']
    for c in fill_cols:
        if c in df.columns: df[c] = df[c].fillna('')
    
    valid_group_cols = [c for c in fill_cols if c in df.columns]
    if not valid_group_cols: return df
    
    agg_rules = {'Ref Des': lambda x: ', '.join(sorted(x.astype(str)))}
    if 'BOM_Order' in df.columns: agg_rules['BOM_Order'] = 'min'
    
    grouped = df.groupby(valid_group_cols).agg(agg_rules).reset_index()
    grouped.rename(columns={'Ref Des': 'Designator'}, inplace=True)
    grouped['Quantity'] = grouped['Designator'].apply(lambda x: len(str(x).split(',')))

    # Calculate Total Points
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

def _write_summary_sheet(writer, df, header_fmt, center_fmt):
    """
    Creates the Summary sheet with SMD vs THT counts.
    """
    valid_mask = df['Status'] != 'XY_ONLY'
    df_clean = df[valid_mask].copy()

    summary_data = []

    for layer in ["Top", "Bottom"]:
        layer_mask = df_clean['Layer_Classified'] == layer
        df_layer = df_clean[layer_mask]
        
        smd_count = len(df_layer[df_layer['Mounting Type'] == 'SMD'])
        tht_count = len(df_layer[df_layer['Mounting Type'] == 'THT'])
        
        summary_data.append({"Scope": f"{layer} BOM", "Type": "SMD", "Count": smd_count})
        summary_data.append({"Scope": f"{layer} BOM", "Type": "THT", "Count": tht_count})
        
        summary_data.append({"Scope": f"{layer} BOM", "Type": "TOTAL", "Count": smd_count + tht_count})
        summary_data.append({"Scope": "", "Type": "", "Count": ""})

    df_summary = pd.DataFrame(summary_data)
    
    sheet_name = "Summary"
    df_summary.to_excel(writer, sheet_name=sheet_name, index=False, startrow=1, header=False)
    
    ws = writer.sheets[sheet_name]
    
    headers = ["Scope", "Component Type", "Count"]
    for i, h in enumerate(headers):
        ws.write(0, i, h, header_fmt)
        ws.set_column(i, i, 20)
        
    for row_idx, row_data in enumerate(df_summary.values):
        excel_row = row_idx + 1
        ws.write(excel_row, 0, row_data[0], center_fmt)
        ws.write(excel_row, 1, row_data[1], center_fmt)
        ws.write(excel_row, 2, row_data[2], center_fmt)

def _write_custom_sheet(writer, df, sheet_name, cols, header_fmt, wrap_fmt, center_fmt, 
                        sort_by_bom_order=False, add_sl_no=False):
    
    if df.empty:
        pd.DataFrame(columns=[c for c in cols if c != 'Sl No.']).to_excel(writer, sheet_name=sheet_name, index=False)
        return

    final_df = df.copy()

    if sort_by_bom_order and 'BOM_Order' in final_df.columns:
        final_df = final_df.sort_values(by=['BOM_Order', 'Location' if 'Location' in final_df else 'Designator'])
    else:
        sort_col = 'Location' if 'Location' in final_df.columns else ('Designator' if 'Designator' in final_df.columns else None)
        if sort_col: final_df = final_df.sort_values(by=sort_col)

    if add_sl_no:
        final_df.reset_index(drop=True, inplace=True)
        final_df['Sl No.'] = final_df.index + 1

    export_data = pd.DataFrame()
    for col in cols:
        export_data[col] = final_df[col] if col in final_df.columns else ""

    export_data.to_excel(writer, sheet_name=sheet_name, index=False, startrow=1, header=False)
    
    worksheet = writer.sheets[sheet_name]
    worksheet.set_row_pixels(0, 35)

    for idx, col_name in enumerate(cols):
        worksheet.write(0, idx, col_name, header_fmt)
        
        max_len = len(col_name)
        if not export_data.empty:
            sample_len = export_data[col_name].head(50).astype(str).map(len).max()
            if pd.notna(sample_len): max_len = max(max_len, sample_len)
        
        final_width = min(max_len + 4, 50)
        worksheet.set_column(idx, idx, final_width)

    for row_idx, row_data in enumerate(export_data.values):
        excel_row = row_idx + 1
        for col_idx, value in enumerate(row_data):
            col_name = cols[col_idx]
            
            if col_name == "Location": cell_fmt = wrap_fmt
            else: cell_fmt = center_fmt
            
            if pd.isna(value): value = ""
            worksheet.write(excel_row, col_idx, value, cell_fmt)