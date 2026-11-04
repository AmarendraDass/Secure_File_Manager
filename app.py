import sys
from pathlib import Path

# Ensure application directory is in sys.path so modules are found regardless of CWD
CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

# If user executed `python app.py` directly (e.g. VS Code Run button or terminal),
# automatically re-launch via streamlit so it opens in the browser seamlessly!
if __name__ == "__main__":
    try:
        from streamlit.runtime import exists
        if not exists():
            import subprocess
            cmd = [sys.executable, "-m", "streamlit", "run", str(Path(__file__).resolve())]
            cmd.extend(sys.argv[1:])
            subprocess.run(cmd)
            sys.exit(0)
    except Exception:
        pass

import io
import json
import mimetypes
import os
import shutil
import tempfile
from datetime import datetime
import zipfile

import altair as alt
import pandas as pd
import streamlit as st

from file_identifier import (
    check_extension,
    expected_type,
    format_size,
    get_hex_dump,
    get_magic_description,
    identify_file,
)
from integrity_checker import (
    calculate_sha256,
    check_integrity,
    compare_hashes,
    create_baseline,
    get_file_hashes,
)
from organizer import (
    choose_category,
    create_organized_zip,
    organize_scan_results,
)

# ---------------------------------------------------------
# Page Configuration
# ---------------------------------------------------------
st.set_page_config(
    page_title="SecureShield Pro | Cloud File Manager & Security Hub",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------
# Premium UI Styling (Light & Dark Friendly)
# ---------------------------------------------------------
st.markdown(
    """
    <style>
    /* App Container */
    .main .block-container {
        padding-top: 1.5rem;
        padding-bottom: 3rem;
        max-width: 98% !important;
    }

    /* Enterprise Hero Banner */
    .hero-banner {
        background: linear-gradient(135deg, #0F172A 0%, #1E293B 50%, #1E3A8A 100%);
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: 16px;
        padding: 24px 30px;
        color: #F8FAFC;
        margin-bottom: 22px;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.2);
    }
    .hero-title {
        font-size: 26px;
        font-weight: 800;
        letter-spacing: -0.5px;
        margin-bottom: 6px;
        display: flex;
        align-items: center;
        gap: 12px;
    }
    .hero-subtitle {
        font-size: 14px;
        color: #CBD5E1;
        line-height: 1.5;
        margin-bottom: 14px;
        max-width: 850px;
    }
    .hero-badges {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
    }
    .hero-pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        font-size: 12px;
        font-weight: 600;
        padding: 4px 12px;
        border-radius: 20px;
        background: rgba(255, 255, 255, 0.08);
        border: 1px solid rgba(255, 255, 255, 0.15);
        color: #F1F5F9;
    }
    .hero-pill.green {
        background: rgba(16, 185, 129, 0.2);
        border-color: rgba(16, 185, 129, 0.4);
        color: #6EE7B7;
    }
    .hero-pill.blue {
        background: rgba(59, 130, 246, 0.2);
        border-color: rgba(59, 130, 246, 0.4);
        color: #93C5FD;
    }

    /* Metric Cards */
    .metric-card {
        background-color: var(--background-color, rgba(128, 128, 128, 0.05));
        border: 1px solid rgba(128, 128, 128, 0.2);
        border-radius: 12px;
        padding: 16px 18px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        height: 100%;
        transition: transform 0.15s ease, box-shadow 0.15s ease;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 16px -2px rgba(0, 0, 0, 0.1);
    }
    .metric-label {
        font-size: 12px;
        font-weight: 700;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.6px;
    }
    .metric-value {
        font-size: 26px;
        font-weight: 800;
        margin: 4px 0 2px 0;
    }
    .metric-sub {
        font-size: 12px;
        color: #94A3B8;
    }
    .metric-danger .metric-value { color: #EF4444 !important; }
    .metric-safe .metric-value { color: #10B981 !important; }

    /* Threat Alert Callout */
    .threat-alert {
        background: linear-gradient(135deg, #FEF2F2 0%, #FEE2E2 100%);
        border-left: 6px solid #EF4444;
        border-radius: 10px;
        padding: 16px 20px;
        margin: 16px 0 20px 0;
        color: #991B1B;
        box-shadow: 0 4px 12px rgba(239, 68, 68, 0.1);
    }
    .threat-alert-title {
        font-weight: 800;
        font-size: 15px;
        margin-bottom: 4px;
        display: flex;
        align-items: center;
        gap: 8px;
    }

    /* Grid File Card */
    .file-card {
        border: 1px solid rgba(128, 128, 128, 0.2);
        border-radius: 12px;
        padding: 16px;
        background: var(--background-color, rgba(128, 128, 128, 0.04));
        display: flex;
        flex-direction: column;
        justifyContent: space-between;
        height: 100%;
        transition: all 0.2s ease;
    }
    .file-card:hover {
        border-color: #3B82F6;
        box-shadow: 0 8px 20px -4px rgba(59, 130, 246, 0.15);
    }
    .file-icon {
        font-size: 32px;
        margin-bottom: 8px;
    }
    .file-card-title {
        font-weight: 700;
        font-size: 14px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        margin-bottom: 4px;
    }
    .file-card-meta {
        font-size: 12px;
        color: #64748B;
        margin-bottom: 12px;
    }

    /* Forensic Hex Box */
    .hex-box {
        font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
        font-size: 12px;
        line-height: 1.45;
        background-color: #0F172A;
        color: #38BDF8;
        padding: 14px 18px;
        border-radius: 8px;
        overflow-x: auto;
        white-space: pre;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------
# Workspace Session State & Persistence
# ---------------------------------------------------------
if "workspace_dir" not in st.session_state:
    ws_temp = tempfile.mkdtemp(prefix="secureshield_workspace_")
    st.session_state["workspace_dir"] = ws_temp
    st.session_state["baseline_file"] = str(Path(ws_temp) / "baseline.json")

workspace_path = Path(st.session_state["workspace_dir"])
workspace_path.mkdir(parents=True, exist_ok=True)
baseline_file_path = Path(st.session_state["baseline_file"])

# UI View Mode State
if "view_mode" not in st.session_state:
    st.session_state["view_mode"] = "List View"


def get_category_icon(category):
    """Return an intuitive icon for each category."""
    icons = {
        "Images": "🖼️",
        "Documents": "📄",
        "Archives": "🗜️",
        "Audio": "🎵",
        "Videos": "🎬",
        "Executables": "⚙️",
        "Linux_Executables": "🐧",
        "Spreadsheets": "📊",
        "Presentations": "📽️",
        "Code_and_Data": "💻",
        "Logs": "📜",
        "Review_Mismatches": "🚨",
        "Others": "📁",
    }
    return icons.get(category, "📁")


def load_demo_files():
    """Seed workspace with demo files (including an extension-spoofed payload) for 1-click evaluation."""
    # 1. Genuine PDF document
    pdf_path = workspace_path / "Annual_Security_Report.pdf"
    pdf_content = b"%PDF-1.5\n%Header test\n1 0 obj\n<< /Title (Annual Security Report) >>\nendobj\ntrailer\n<< /Size 1 >>\nstartxref\n0\n%%EOF\n"
    pdf_path.write_bytes(pdf_content)

    # 2. Genuine PNG Image
    png_path = workspace_path / "company_logo.png"
    png_content = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x10\x00\x00\x00\x10\x08\x06\x00\x00\x00\x1f\xf3\xffa" + b"\x00" * 40
    png_path.write_bytes(png_content)

    # 3. Spoofed Payload: Windows Executable disguised as an Invoice Image!
    spoofed_path = workspace_path / "Urgent_Invoice_2026.png"
    exe_content = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff\x00\x00\xb8\x00\x00\x00" + b"\x00" * 80 + b"This program cannot be run in DOS mode."
    spoofed_path.write_bytes(exe_content)

    # 4. Genuine Text Notes
    txt_path = workspace_path / "project_milestones.txt"
    txt_content = (
        "Project SecureShield Pro\n"
        "Status: Active\n"
        "Features: Magic byte content scan, SHA-256 integrity, automated sorting.\n"
        "Reviewers: Antigravity Deepmind & Development Team.\n"
    )
    txt_path.write_text(txt_content, encoding="utf-8")

    # 5. Genuine Python Script
    py_path = workspace_path / "system_diag.py"
    py_content = "def check_health():\n    return {'status': 'healthy', 'uptime': '99.9%'}\n\nif __name__ == '__main__':\n    print(check_health())\n"
    py_path.write_text(py_content, encoding="utf-8")


# Automatically seed with demo files on first load if workspace is empty
if "auto_demo_loaded" not in st.session_state:
    if not any(workspace_path.iterdir()):
        load_demo_files()
    st.session_state["auto_demo_loaded"] = True


def scan_workspace():
    """Scan all files currently residing in the workspace directory."""
    results = []
    if not workspace_path.exists():
        return results

    for p in sorted(workspace_path.rglob("*")):
        if p.is_file() and not p.name.endswith(".tmp") and p.name != "baseline.json":
            try:
                size = p.stat().st_size
                mtime = datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            except OSError:
                size = 0
                mtime = "Unknown"

            actual = identify_file(p)
            expected = expected_type(p)
            status = check_extension(p, actual)

            res = {
                "path": p,
                "name": p.name,
                "actual_type": actual,
                "expected_type": expected,
                "status": status,
                "size_bytes": size,
                "size_formatted": format_size(size),
                "modified_time": mtime,
                "relative_path": str(p.relative_to(workspace_path)).replace("\\", "/"),
            }
            res["category"] = choose_category(res)
            results.append(res)
    return results


# ---------------------------------------------------------
# Sidebar: Control Panel & Settings
# ---------------------------------------------------------
with st.sidebar:
    st.markdown(
        """
        <div class="sidebar-brand">
            <span style="font-size:24px;">🛡️</span>
            <div>
                <div style="font-weight:800; font-size:18px; line-height:1.2;">SecureShield Pro</div>
                <div style="font-size:11px; color:#64748B;">Cloud File Manager & Guardian</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("---")
    st.markdown("### 🎛️ Workspace Actions")

    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("✨ Load Demo", use_container_width=True, help="Load sample files including a spoofed file"):
            load_demo_files()
            st.success("Loaded demo files!")
            st.rerun()

    with col_btn2:
        if st.button("🧹 Clear All", use_container_width=True, help="Delete all files from workspace"):
            for item in workspace_path.iterdir():
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item)
            st.info("Workspace cleared.")
            st.rerun()

    st.markdown("---")
    st.markdown("### 👁️ Display Preferences")
    st.session_state["view_mode"] = st.radio(
        "Explorer View Mode",
        options=["List View", "Grid View"],
        horizontal=True,
    )

    hex_buffer_size = st.select_slider(
        "Forensic Hex Buffer (Bytes)",
        options=[16, 32, 64, 128, 256],
        value=64,
        help="Amount of binary header read for forensic deep-inspection.",
    )

    st.markdown("---")
    st.markdown("### 📖 Knowledge Base")
    with st.expander("🛡️ Magic Bytes vs Extensions"):
        st.write(
            "Every binary format has unique initial bytes ('magic numbers', e.g. `%PDF-` for PDFs, "
            "`\x89PNG` for PNGs, `MZ` for Windows executables). Attackers often rename dangerous `.exe` "
            "files to `.png` or `.pdf` to deceive users. SecureShield inspects the actual binary stream "
            "to guarantee file safety."
        )

    with st.expander("🔐 SHA-256 Baseline Auditing"):
        st.write(
            "Taking a cryptographic baseline captures a digital SHA-256 fingerprint for every file. "
            "Any tampering, unauthorized editing, or malware infection will immediately trigger a hash mismatch alert."
        )

# ---------------------------------------------------------
# Hero Banner
# ---------------------------------------------------------
st.markdown(
    """
    <div class="hero-banner">
        <div class="hero-title">
            <span>🛡️</span>
            <span>SecureShield Pro | Cloud File Manager & Security Hub</span>
        </div>
        <div class="hero-subtitle">
            Perform enterprise file operations (Preview, Edit, Rename, Organize, Extract, and Compress) 
            backed by deep binary magic-byte inspection, Trojan anti-spoofing defense, and SHA-256 integrity auditing.
        </div>
        <div class="hero-badges">
            <span class="hero-pill green">● Engine Online</span>
            <span class="hero-pill blue">SHA-256 Active</span>
            <span class="hero-pill">In-Browser File Ops</span>
            <span class="hero-pill">Zero-Leak Local Sandbox</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------
# File Ingestion Bar (Upload / Zip Extract / New File)
# ---------------------------------------------------------
with st.expander("📥 **Upload Files & Import Data**", expanded=True):
    up_col1, up_col2 = st.columns([3, 1])

    with up_col1:
        new_uploads = st.file_uploader(
            "Drag and drop any files here (Documents, Images, Archives, Executables, Media, Code)",
            accept_multiple_files=True,
            key="main_file_uploader",
        )

        if new_uploads:
            saved_count = 0
            for uploaded_file in new_uploads:
                dest = workspace_path / Path(uploaded_file.name).name
                dest.write_bytes(uploaded_file.getvalue())
                saved_count += 1
            st.success(f"✔ Successfully uploaded and staged {saved_count} file(s) in workspace.")
            st.rerun()

    with up_col2:
        st.markdown("**Quick File Tools:**")
        with st.popover("➕ Create New File"):
            new_file_name = st.text_input("File Name", value="new_document.txt")
            new_file_content = st.text_area("Initial Content", placeholder="Type or paste text...")
            if st.button("Create & Save", type="primary", use_container_width=True):
                if new_file_name.strip():
                    created_path = workspace_path / Path(new_file_name.strip()).name
                    created_path.write_text(new_file_content, encoding="utf-8")
                    st.success(f"Created `{new_file_name}`!")
                    st.rerun()

# ---------------------------------------------------------
# Scan Workspace Data & Threat Evaluation
# ---------------------------------------------------------
files = scan_workspace()
total_files = len(files)
total_bytes = sum(f["size_bytes"] for f in files)
mismatches = [f for f in files if f["status"] == "MISMATCH"]
clean_files = [f for f in files if f["status"] == "MATCH"]
categories_found = len(set(f["category"] for f in files))

# ---------------------------------------------------------
# Top KPI Metric Cards
# ---------------------------------------------------------
m_col1, m_col2, m_col3, m_col4, m_col5 = st.columns(5)

with m_col1:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">Workspace Files</div>
            <div class="metric-value">{total_files}</div>
            <div class="metric-sub">Active in storage</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with m_col2:
    st.markdown(
        f"""
        <div class="metric-card metric-safe">
            <div class="metric-label">Verified Safe</div>
            <div class="metric-value">{len(clean_files)}</div>
            <div class="metric-sub">Matching signatures</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with m_col3:
    threat_style = "metric-danger" if len(mismatches) > 0 else "metric-safe"
    st.markdown(
        f"""
        <div class="metric-card {threat_style}">
            <div class="metric-label">Threat Alerts</div>
            <div class="metric-value">{len(mismatches)}</div>
            <div class="metric-sub">Extension spoofing detected</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with m_col4:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">Categories</div>
            <div class="metric-value">{categories_found}</div>
            <div class="metric-sub">Smart taxonomy groups</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with m_col5:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">Total Volume</div>
            <div class="metric-value">{format_size(total_bytes)}</div>
            <div class="metric-sub">Storage consumption</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------
# Security Threat Alert Banner
# ---------------------------------------------------------
if len(mismatches) > 0:
    st.markdown(
        f"""
        <div class="threat-alert">
            <div class="threat-alert-title">
                <span>🚨</span>
                <span>SECURITY ADVISORY: {len(mismatches)} Extension Spoofing Alert(s) Detected!</span>
            </div>
            <div>
                One or more files have binary signatures that directly contradict their declared extensions. 
                For example, an executable binary (EXE/ELF) disguised with a <code>.png</code> or <code>.pdf</code> extension. 
                Do not open or execute quarantined files until forensically analyzed.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.write("")

# ---------------------------------------------------------
# Main Navigation Tabs
# ---------------------------------------------------------
tab_explorer, tab_operations, tab_organize, tab_integrity, tab_analytics = st.tabs(
    [
        "📁 File Explorer",
        "⚡ File Operations & Editor",
        "🗂️ Smart Organizer",
        "🛡️ SHA-256 Integrity Monitor",
        "📊 Analytics & Insights",
    ]
)

# ---------------------------------------------------------
# TAB 1: File Explorer (List & Grid View)
# ---------------------------------------------------------
with tab_explorer:
    st.subheader("Workspace File Explorer")

    if not files:
        st.info("No files currently in workspace. Upload files above or click '✨ Load Demo' in the sidebar.")
    else:
        # Search & Filters
        f_col1, f_col2, f_col3, f_col4 = st.columns([2, 1, 1, 1])

        with f_col1:
            search_query = st.text_input("🔍 Search files", placeholder="Filter by name...", label_visibility="collapsed")

        with f_col2:
            cat_list = ["All Categories"] + sorted(list(set(f["category"] for f in files)))
            filter_cat = st.selectbox("Category", cat_list, label_visibility="collapsed")

        with f_col3:
            status_list = ["All Verdicts"] + sorted(list(set(f["status"] for f in files)))
            filter_status = st.selectbox("Verdict", status_list, label_visibility="collapsed")

        with f_col4:
            sort_by = st.selectbox("Sort By", ["Name (A-Z)", "Size (Largest)", "Size (Smallest)", "Recent"], label_visibility="collapsed")

        # Filter Logic
        displayed_files = files
        if search_query:
            displayed_files = [f for f in displayed_files if search_query.lower() in f["name"].lower()]
        if filter_cat != "All Categories":
            displayed_files = [f for f in displayed_files if f["category"] == filter_cat]
        if filter_status != "All Verdicts":
            displayed_files = [f for f in displayed_files if f["status"] == filter_status]

        # Sorting
        if sort_by == "Name (A-Z)":
            displayed_files = sorted(displayed_files, key=lambda x: x["name"].lower())
        elif sort_by == "Size (Largest)":
            displayed_files = sorted(displayed_files, key=lambda x: x["size_bytes"], reverse=True)
        elif sort_by == "Size (Smallest)":
            displayed_files = sorted(displayed_files, key=lambda x: x["size_bytes"])
        elif sort_by == "Recent":
            displayed_files = sorted(displayed_files, key=lambda x: x["modified_time"], reverse=True)

        st.caption(f"Showing **{len(displayed_files)}** of **{len(files)}** files")

        # 1. LIST VIEW
        if st.session_state["view_mode"] == "List View":
            table_data = []
            for f in displayed_files:
                st_verdict = f["status"]
                if st_verdict == "MATCH":
                    badge_str = "✔ Clean Match"
                elif st_verdict == "MISMATCH":
                    badge_str = "🚨 SPOOFED (MISMATCH)"
                elif st_verdict == "UNRECOGNIZED SIGNATURE":
                    badge_str = "❓ Unknown Signature"
                else:
                    badge_str = f"ℹ {st_verdict}"

                table_data.append({
                    "Icon": get_category_icon(f["category"]),
                    "File Name": f["name"],
                    "Category": f["category"],
                    "Verdict": badge_str,
                    "Detected Type": f["actual_type"],
                    "Extension": f["path"].suffix or "(none)",
                    "Size": f["size_formatted"],
                    "Last Modified": f["modified_time"],
                })

            df_display = pd.DataFrame(table_data)
            st.dataframe(
                df_display,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Icon": st.column_config.TextColumn("", width="small"),
                    "File Name": st.column_config.TextColumn("File Name", width="large"),
                    "Verdict": st.column_config.TextColumn("Security Verdict", width="medium"),
                    "Category": st.column_config.TextColumn("Category", width="small"),
                    "Detected Type": st.column_config.TextColumn("Binary Type", width="small"),
                    "Extension": st.column_config.TextColumn("Ext", width="small"),
                    "Size": st.column_config.TextColumn("Size", width="small"),
                    "Last Modified": st.column_config.TextColumn("Modified", width="medium"),
                },
            )

        # 2. GRID VIEW
        else:
            cols_per_row = 3
            for i in range(0, len(displayed_files), cols_per_row):
                row_files = displayed_files[i:i + cols_per_row]
                g_cols = st.columns(cols_per_row)
                for idx, f in enumerate(row_files):
                    with g_cols[idx]:
                        is_spoof = f["status"] == "MISMATCH"
                        card_class = "file-card"
                        st.markdown(
                            f"""
                            <div class="{card_class}">
                                <div class="file-icon">{get_category_icon(f['category'])}</div>
                                <div class="file-card-title" title="{f['name']}">{f['name']}</div>
                                <div class="file-card-meta">
                                    • {f['size_formatted']} | {f['category']}<br>
                                    • Binary: <b>{f['actual_type']}</b> ({f['status']})
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                        # Quick Action Buttons below card
                        qb1, qb2 = st.columns(2)
                        with qb1:
                            file_data = f["path"].read_bytes()
                            st.download_button(
                                "📥 Download",
                                data=file_data,
                                file_name=f["name"],
                                key=f"grid_dl_{f['name']}_{i}_{idx}",
                                use_container_width=True,
                            )
                        with qb2:
                            if st.button("🗑️ Delete", key=f"grid_del_{f['name']}_{i}_{idx}", use_container_width=True):
                                f["path"].unlink(missing_ok=True)
                                st.rerun()

        # Batch Download Option
        st.markdown("---")
        b_col1, b_col2 = st.columns([1, 3])
        with b_col1:
            if files:
                all_zip_buf = create_organized_zip(files)
                st.download_button(
                    "📦 Download All as ZIP",
                    data=all_zip_buf,
                    file_name="workspace_bundle.zip",
                    mime="application/zip",
                    use_container_width=True,
                )

# ---------------------------------------------------------
# TAB 2: File Operations & In-Browser Editor
# ---------------------------------------------------------
with tab_operations:
    st.subheader("File Operations & In-Browser Viewer / Editor")
    st.caption("Inspect, read, edit code/text files, preview media, rename, extract archives, or duplicate files directly.")

    if not files:
        st.info("No files available. Upload files or load demo to perform operations.")
    else:
        file_map = {f["name"]: f for f in files}
        target_name = st.selectbox(
            "Select a file to manage:",
            options=list(file_map.keys()),
            index=0,
        )

        curr_file = file_map[target_name]
        c_path = Path(curr_file["path"])

        op_tab1, op_tab2, op_tab3, op_tab4 = st.tabs(
            [
                "👁️ Preview & Content Viewer",
                "✏️ In-Browser Text/Code Editor",
                "🏷️ Rename & Duplicate",
                "🔬 Forensic Hex & Hash Inspector",
            ]
        )

        # 1. Preview & Content Viewer
        with op_tab1:
            st.markdown(f"#### Previewing: `{curr_file['name']}`")
            ext = c_path.suffix.lower()

            # Image Preview
            if ext in [".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"]:
                try:
                    st.image(str(c_path), caption=f"{curr_file['name']} ({curr_file['size_formatted']})")
                except Exception as exc:
                    st.warning(f"Could not render image: {exc}")

            # Audio Preview
            elif ext in [".mp3", ".wav", ".ogg", ".flac"]:
                st.audio(str(c_path))

            # Video Preview
            elif ext in [".mp4", ".mov"]:
                st.video(str(c_path))

            # Text / Code Preview
            elif curr_file["actual_type"] == "TEXT" or ext in [".txt", ".py", ".md", ".json", ".csv", ".xml", ".html", ".css", ".js", ".log"]:
                try:
                    text_content = c_path.read_text(encoding="utf-8", errors="replace")
                    if ext == ".py":
                        st.code(text_content, language="python")
                    elif ext == ".json":
                        st.code(text_content, language="json")
                    elif ext == ".md":
                        st.markdown(text_content)
                    elif ext == ".csv":
                        try:
                            df_csv = pd.read_csv(c_path)
                            st.dataframe(df_csv, use_container_width=True)
                        except Exception:
                            st.text(text_content)
                    else:
                        st.text_area("File Content", value=text_content, height=250, disabled=True)
                except Exception as exc:
                    st.error(f"Cannot read text content: {exc}")

            # ZIP Archive Preview
            elif ext == ".zip" or curr_file["actual_type"] == "ZIP":
                st.info("📦 This is a ZIP archive.")
                try:
                    with zipfile.ZipFile(c_path, "r") as zf:
                        zip_names = zf.namelist()
                        st.markdown(f"**Archive contains {len(zip_names)} files:**")
                        st.write(zip_names)

                        if st.button("⚡ Extract ZIP Archive to Workspace", type="primary", key="extract_zip_btn"):
                            extract_dest = workspace_path / c_path.stem
                            zf.extractall(extract_dest)
                            st.success(f"Extracted files into folder: `{c_path.stem}/`")
                            st.rerun()
                except Exception as exc:
                    st.error(f"Error reading ZIP archive: {exc}")

            else:
                st.info(f"Binary format `{curr_file['actual_type']}`. Use the Hex & Hash Inspector tab to inspect byte structure.")

            # Download & Delete Action Buttons
            st.write("")
            act_c1, act_c2, _ = st.columns([1, 1, 2])
            with act_c1:
                st.download_button(
                    "📥 Download This File",
                    data=c_path.read_bytes(),
                    file_name=curr_file["name"],
                    key=f"dl_preview_{curr_file['name']}",
                    use_container_width=True,
                )
            with act_c2:
                if st.button("🗑️ Delete This File", type="secondary", key=f"del_preview_{curr_file['name']}", use_container_width=True):
                    c_path.unlink(missing_ok=True)
                    st.success(f"Deleted `{curr_file['name']}`")
                    st.rerun()

        # 2. In-Browser Text/Code Editor
        with op_tab2:
            st.markdown(f"#### Edit: `{curr_file['name']}`")
            try:
                raw_bytes = c_path.read_bytes()
                is_text = curr_file["actual_type"] == "TEXT" or b"\x00" not in raw_bytes[:1024]
            except Exception:
                is_text = False

            if not is_text:
                st.warning("⚠️ This appears to be a binary file. Editing binary files as text may corrupt their structure.")
            else:
                current_text = c_path.read_text(encoding="utf-8", errors="replace")
                edited_text = st.text_area(
                    "Editor Content",
                    value=current_text,
                    height=320,
                    key=f"editor_{curr_file['name']}",
                )

                if st.button("💾 Save Changes", type="primary", key=f"save_btn_{curr_file['name']}"):
                    c_path.write_text(edited_text, encoding="utf-8")
                    st.success(f"✔ Changes saved to `{curr_file['name']}` successfully!")
                    st.rerun()

        # 3. Rename & Duplicate
        with op_tab3:
            st.markdown("#### Rename File")
            rn_col1, rn_col2 = st.columns([3, 1])
            with rn_col1:
                new_name_val = st.text_input("New Name (with extension)", value=curr_file["name"], key=f"rn_input_{curr_file['name']}")
            with rn_col2:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("Rename", type="primary", key=f"rn_btn_{curr_file['name']}", use_container_width=True):
                    cleaned_name = Path(new_name_val.strip()).name
                    if cleaned_name and cleaned_name != curr_file["name"]:
                        new_target = c_path.parent / cleaned_name
                        if new_target.exists():
                            st.error(f"A file named `{cleaned_name}` already exists!")
                        else:
                            c_path.rename(new_target)
                            st.success(f"Renamed `{curr_file['name']}` -> `{cleaned_name}`!")
                            st.rerun()

            st.markdown("---")
            st.markdown("#### Duplicate File")
            if st.button("📋 Duplicate File (Create Copy)", key=f"dup_btn_{curr_file['name']}", use_container_width=False):
                stem = c_path.stem
                suffix = c_path.suffix
                copy_name = f"{stem}_copy{suffix}"
                copy_path = c_path.parent / copy_name
                count = 1
                while copy_path.exists():
                    copy_name = f"{stem}_copy_{count}{suffix}"
                    copy_path = c_path.parent / copy_name
                    count += 1
                shutil.copy2(c_path, copy_path)
                st.success(f"Created duplicate: `{copy_name}`")
                st.rerun()

        # 4. Forensic Hex & Hash Inspector
        with op_tab4:
            st.markdown("#### Forensic Inspection & Cryptographic Hashes")
            h_col1, h_col2 = st.columns([1, 1])

            with h_col1:
                st.markdown("**File Details:**")
                st.write(f"• **Assigned Category:** `{curr_file['category']}`")
                st.write(f"• **True Binary Signature:** `{curr_file['actual_type']}`")
                st.write(f"• **Declared Extension:** `{c_path.suffix or '(none)'}`")
                st.write(f"• **Security Verdict:** `{curr_file['status']}`")

                # Compute SHA-256
                try:
                    f_hash = calculate_sha256(c_path)
                    st.markdown("**Cryptographic SHA-256 Hash:**")
                    st.code(f_hash, language="text")
                except Exception as exc:
                    st.error(f"Error computing hash: {exc}")

            with h_col2:
                st.markdown(f"**Forensic Hex Dump (First {hex_buffer_size} Bytes):**")
                hex_dump_str = get_hex_dump(c_path, num_bytes=hex_buffer_size)
                st.markdown(f'<div class="hex-box">{hex_dump_str}</div>', unsafe_allow_html=True)

# ---------------------------------------------------------
# TAB 3: Smart File Organizer
# ---------------------------------------------------------
with tab_organize:
    st.subheader("Smart Content-Aware Organizer")
    st.caption("Sorts files into dedicated category folders based on verified magic-byte signatures rather than spoofable extensions.")

    if not files:
        st.info("No files in workspace to organize.")
    else:
        # Group files by category
        cat_map = {}
        for f in files:
            cat = f["category"]
            cat_map.setdefault(cat, []).append(f)

        st.markdown("#### Proposed Categorization Plan")
        p_cols = st.columns(min(len(cat_map), 4) or 1)
        for idx, (cat_name, cat_files_list) in enumerate(sorted(cat_map.items())):
            with p_cols[idx % len(p_cols)]:
                badge = "🚨" if cat_name == "Review_Mismatches" else get_category_icon(cat_name)
                st.markdown(
                    f"""
                    <div class="metric-card">
                        <div class="metric-label">{badge} {cat_name}</div>
                        <div class="metric-value" style="font-size:22px;">{len(cat_files_list)}</div>
                        <div class="metric-sub">Auto-assigned folder</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        st.write("")
        with st.expander("👁️ View file assignments by category"):
            for cat_name, c_files in sorted(cat_map.items()):
                st.markdown(f"**{get_category_icon(cat_name)} {cat_name}** ({len(c_files)} files):")
                st.write(", ".join(f"`{f['name']}`" for f in c_files))

        st.markdown("---")
        st.markdown("#### ⚡ 1-Click Organized ZIP Archive")
        st.write("Generate and download a single `.zip` archive with all files cleanly arranged into their category subdirectories.")

        organized_zip_buf = create_organized_zip(files)
        st.download_button(
            "📦 Download Organized Files (.ZIP)",
            data=organized_zip_buf,
            file_name="organized_workspace.zip",
            mime="application/zip",
            key="dl_org_zip_btn",
            use_container_width=True,
        )

# ---------------------------------------------------------
# TAB 4: SHA-256 Cryptographic Integrity Monitor
# ---------------------------------------------------------
with tab_integrity:
    st.subheader("SHA-256 File Integrity Guardian")
    st.caption("Record tamper-evident cryptographic snapshots and detect unauthorized modifications, additions, or deletions.")

    if not files:
        st.info("No files in workspace to monitor.")
    else:
        b_exists = baseline_file_path.is_file()
        b_data = None
        if b_exists:
            try:
                b_data = json.loads(baseline_file_path.read_text(encoding="utf-8"))
            except Exception:
                b_exists = False

        bi_col1, bi_col2 = st.columns([2, 1])
        with bi_col1:
            if b_exists and b_data:
                st.markdown(
                    f"""
                    <div style="background-color:rgba(16,185,129,0.12); border:1px solid #10B981; border-radius:12px; padding:16px 20px;">
                        <div style="font-weight:800; color:#065F46; font-size:16px; margin-bottom:4px;">
                            ✔ Cryptographic Baseline Snapshot Active
                        </div>
                        <div style="font-size:13px; color:#047857;">
                            • <b>Created:</b> {b_data.get('created_at')}<br>
                            • <b>Tracked:</b> {len(b_data.get('files', {}))} files recorded<br>
                            • <b>Algorithm:</b> {b_data.get('algorithm', 'SHA-256')}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    """
                    <div style="background-color:rgba(128,128,128,0.08); border:1px solid rgba(128,128,128,0.25); border-radius:12px; padding:16px 20px;">
                        <div style="font-weight:700; font-size:15px; margin-bottom:4px;">
                            ℹ No Baseline Snapshot Found
                        </div>
                        <div style="font-size:13px; color:#64748B;">
                            Take a cryptographic baseline snapshot now to detect future tampering or file edits.
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        with bi_col2:
            if st.button("📸 Create / Refresh Baseline", type="primary", key="btn_create_baseline", use_container_width=True):
                try:
                    c = create_baseline(workspace_path, baseline_file_path)
                    st.success(f"Baseline created for {c} files!")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Error creating baseline: {exc}")

            if b_exists:
                st.download_button(
                    "💾 Export Baseline JSON",
                    data=baseline_file_path.read_bytes(),
                    file_name="baseline.json",
                    mime="application/json",
                    key="dl_baseline_btn",
                    use_container_width=True,
                )

        st.markdown("---")
        st.markdown("#### 🔍 Run Integrity Verification")

        if st.button("⚡ Verify Files Against Baseline", key="btn_verify_baseline", use_container_width=True):
            if not b_exists:
                st.warning("Please create a baseline snapshot first.")
            else:
                try:
                    results = check_integrity(workspace_path, baseline_file_path, strict_folder_check=False)

                    unchanged = sum(1 for r in results if r[1] == "UNCHANGED")
                    modified = sum(1 for r in results if r[1] == "MODIFIED")
                    added = sum(1 for r in results if r[1] == "ADDED")
                    deleted = sum(1 for r in results if r[1] == "DELETED")

                    # Scorecards
                    c1, c2, c3, c4 = st.columns(4)
                    with c1:
                        st.markdown(
                            f"""
                            <div class="metric-card metric-safe">
                                <div class="metric-label">Intact / Verified</div>
                                <div class="metric-value">{unchanged}</div>
                                <div class="metric-sub">Identical hashes</div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                    with c2:
                        m_cls = "metric-danger" if modified > 0 else "metric-safe"
                        st.markdown(
                            f"""
                            <div class="metric-card {m_cls}">
                                <div class="metric-label">Tampered / Modified</div>
                                <div class="metric-value">{modified}</div>
                                <div class="metric-sub">Hash mismatch!</div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                    with c3:
                        st.markdown(
                            f"""
                            <div class="metric-card">
                                <div class="metric-label">Newly Added</div>
                                <div class="metric-value">{added}</div>
                                <div class="metric-sub">Added since baseline</div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                    with c4:
                        st.markdown(
                            f"""
                            <div class="metric-card">
                                <div class="metric-label">Missing / Deleted</div>
                                <div class="metric-value">{deleted}</div>
                                <div class="metric-sub">Removed from storage</div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                    st.write("")
                    table_rows = []
                    for item in results:
                        fn, st_code = item[0], item[1]
                        orig_h = getattr(item, "original_hash", "N/A") or "N/A"
                        curr_h = getattr(item, "current_hash", "N/A") or "N/A"

                        if st_code == "UNCHANGED":
                            lbl = "✔ Intact"
                        elif st_code == "MODIFIED":
                            lbl = "🚨 TAMPERED (MODIFIED)"
                        elif st_code == "ADDED":
                            lbl = "➕ Added"
                        elif st_code == "DELETED":
                            lbl = "➖ Deleted"
                        else:
                            lbl = st_code

                        table_rows.append({
                            "Status": lbl,
                            "File Name": fn,
                            "Baseline SHA-256": orig_h,
                            "Current Workspace SHA-256": curr_h,
                        })

                    st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)

                except Exception as exc:
                    st.error(f"Integrity check failed: {exc}")

# ---------------------------------------------------------
# TAB 5: Analytics & Visual Telemetry
# ---------------------------------------------------------
with tab_analytics:
    st.subheader("Visual Telemetry & Storage Analytics")
    st.caption("Distribution of binary formats, security verdicts, and category consumption.")

    if not files:
        st.info("No data available to plot.")
    else:
        v_col1, v_col2 = st.columns(2)

        with v_col1:
            st.markdown("#### Detected Binary Formats")
            b_counts = {}
            for f in files:
                t = f["actual_type"]
                b_counts[t] = b_counts.get(t, 0) + 1
            df_b = pd.DataFrame([{"Format": k, "Files": v} for k, v in b_counts.items()])

            chart_fmt = (
                alt.Chart(df_b)
                .mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6)
                .encode(
                    x=alt.X("Format:N", sort="-y"),
                    y=alt.Y("Files:Q"),
                    color=alt.Color("Format:N", legend=None),
                    tooltip=["Format", "Files"],
                )
                .properties(height=300)
            )
            st.altair_chart(chart_fmt, use_container_width=True)

        with v_col2:
            st.markdown("#### Security Verification Breakdown")
            v_counts = {}
            for f in files:
                st_code = f["status"]
                v_counts[st_code] = v_counts.get(st_code, 0) + 1
            df_v = pd.DataFrame([{"Verdict": k, "Count": v} for k, v in v_counts.items()])

            chart_v = (
                alt.Chart(df_v)
                .mark_arc(innerRadius=55)
                .encode(
                    theta=alt.Theta("Count:Q"),
                    color=alt.Color(
                        "Verdict:N",
                        scale=alt.Scale(
                            domain=["MATCH", "MISMATCH", "UNRECOGNIZED SIGNATURE", "NOT CHECKED"],
                            range=["#10B981", "#EF4444", "#F59E0B", "#6366F1"],
                        ),
                    ),
                    tooltip=["Verdict", "Count"],
                )
                .properties(height=300)
            )
            st.altair_chart(chart_v, use_container_width=True)

        st.markdown("---")
        st.markdown("#### Storage by Category (KB)")
        c_sizes = {}
        for f in files:
            c = f["category"]
            c_sizes[c] = c_sizes.get(c, 0) + (f["size_bytes"] / 1024)

        df_sz = pd.DataFrame([
            {"Category": k, "Size (KB)": round(v, 2)}
            for k, v in sorted(c_sizes.items(), key=lambda x: x[1], reverse=True)
        ])

        chart_sz = (
            alt.Chart(df_sz)
            .mark_bar(color="#3B82F6", cornerRadiusTopRight=6, cornerRadiusBottomRight=6)
            .encode(
                y=alt.Y("Category:N", sort="-x"),
                x=alt.X("Size (KB):Q"),
                tooltip=["Category", "Size (KB)"],
            )
            .properties(height=260)
        )
        st.altair_chart(chart_sz, use_container_width=True)
