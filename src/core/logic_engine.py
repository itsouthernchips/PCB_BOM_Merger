import pandas as pd
from src.core.normalizer import normalize_bom_data
import re

def perform_merge_v2(bom_df, xy_df, mapping):
    print("\n!!! EXECUTING V5.0 LOGIC (SUFFIX FIX) !!!")
    
    # --- 1. KEY RETRIEVAL ---
    bom_ref_col = mapping.get("BOM Location Col")
    xy_ref_col = mapping.get("XY Location Col")
    
    if not bom_ref_col or not xy_ref_col:
         raise ValueError("Mapping Error: Location Columns missing.")

    ref_x_col = mapping.get("Center-X")
    ref_y_col = mapping.get("Center-Y")
    rot_col   = mapping.get("Rotation")
    
    pts_col   = mapping.get("Points")
    mnt_col   = mapping.get("Mounting Type")

    # --- 2. CLEAN UNITS FROM XY DATA ---
    if ref_x_col and ref_x_col in xy_df.columns:
        xy_df[ref_x_col] = _clean_numeric_col(xy_df[ref_x_col])
    if ref_y_col and ref_y_col in xy_df.columns:
        xy_df[ref_y_col] = _clean_numeric_col(xy_df[ref_y_col])
    if rot_col and rot_col in xy_df.columns:
        xy_df[rot_col] = _clean_numeric_col(xy_df[rot_col])

    # --- 3. PREPARE XY DATA ---
    # XY data has no duplicate references, use as-is
    xy_clean = xy_df.copy()

    # --- 4. PRE-PROCESS BOM ---
    print(f"Normalizing BOM...")
    bom_exploded = normalize_bom_data(bom_df, bom_ref_col, delimiter=',') 
    bom_exploded['_BOM_ORDER'] = range(len(bom_exploded))

    # --- 5. MERGE ---
    bom_exploded['_JOIN_KEY'] = bom_exploded[bom_ref_col].astype(str).str.strip().str.upper()
    xy_clean['_JOIN_KEY'] = xy_clean[xy_ref_col].astype(str).str.strip().str.upper()

    # Suffixes are important here. 
    # If both files have "Points", they become Points_XY and Points_BOM
    merged_df = pd.merge(xy_clean, bom_exploded, on='_JOIN_KEY', how='outer', indicator=True, suffixes=('_XY', '_BOM'))

    # --- 6. BUILD OUTPUT ---
    final_rows = []
    
    for _, row in merged_df.iterrows():
        merge_status = row['_merge']
        status = "MATCHED" if merge_status == 'both' else ("XY_ONLY" if merge_status == 'left_only' else "BOM_ONLY")
        
        bom_order = row.get("_BOM_ORDER")
        if pd.isna(bom_order): 
            bom_order = 999999
            
        # Helper to find data whether it has _BOM suffix or not
        def _get_merged_val(col_name):
            if not col_name: return ""
            # Priority 1: Check exact name (if no collision)
            if col_name in row and pd.notna(row[col_name]): return row[col_name]
            # Priority 2: Check _BOM suffix (if collision occurred)
            col_bom = f"{col_name}_BOM"
            if col_bom in row and pd.notna(row[col_bom]): return row[col_bom]
            return ""

        # Retrieve Values safely
        mnt_val = ""
        if mnt_col:
            raw_mnt = str(_get_merged_val(mnt_col)).strip().upper()
            mnt_val = raw_mnt if raw_mnt != "NAN" else ""
            
        pts_val = ""
        if pts_col:
            pts_val = str(_get_merged_val(pts_col)).strip()
            if pts_val.lower() == "nan": pts_val = ""

        part_val = _get_merged_val(mapping.get("Part No."))
        desc_val = _get_merged_val(mapping.get("Description"))
        qty_val  = _get_merged_val(mapping.get("Quantity"))

        new_row = {
            "Ref Des":     row['_JOIN_KEY'],
            "Status":      status,
            "Is Ignored":  False,
            "BOM_Order":   bom_order,
            
            "Layer":       row.get(mapping.get("Layer"), ""),
            "Ref X":       row.get(ref_x_col, ""),
            "Ref Y":       row.get(ref_y_col, ""),
            "Rotation":    row.get(rot_col, ""),
            
            "Part Number": part_val,
            "Description": desc_val,
            "Quantity":    qty_val,
            
            "Points":        pts_val,
            "Mounting Type": mnt_val
        }
        
        ref = str(new_row["Ref Des"])
        if (ref.startswith("FID") or ref.startswith("TP") or ref.startswith("MH")) and status == "XY_ONLY":
            new_row["Is Ignored"] = True
                
        final_rows.append(new_row)

    return pd.DataFrame(final_rows)

def _clean_numeric_col(series):
    return series.astype(str).apply(
        lambda x: re.sub(r"[^\d\.\-]", "", x) if pd.notnull(x) else x
    )
