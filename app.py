import streamlit as st
import tempfile
from pathlib import Path
from main import scan_folder
from integrity_checker import create_baseline, check_integrity

st.title("Secure File Management System")

uploaded_files = st.file_uploader("Upload files to scan", accept_multiple_files=True)

if uploaded_files:
    if "file_workspace" not in st.session_state:
        temporary_workspace = tempfile.TemporaryDirectory()
        workspace_path = Path(temporary_workspace.name)
        st.session_state["file_workspace"] = temporary_workspace
        st.session_state["upload_path"] = workspace_path / "uploads"
        st.session_state["baseline_path"] = workspace_path / "baseline.json"
        st.session_state["upload_path"].mkdir()

    upload_path = st.session_state["upload_path"]
    baseline_path = st.session_state["baseline_path"]

    for existing_file in upload_path.iterdir():
        if existing_file.is_file():
            existing_file.unlink()

    for uploaded_file in uploaded_files:
        filename = Path(uploaded_file.name).name
        if not filename:
            filename = "upload"

        file_path = upload_path / filename
        suffix_number = 1
        while file_path.exists():
            file_path = upload_path / (
                f"{Path(filename).stem}_{suffix_number}"
                f"{Path(filename).suffix}"
            )
            suffix_number += 1

        file_path.write_bytes(uploaded_file.getvalue())

    st.subheader("File Scan Report")
    results = scan_folder(upload_path)
    display_results = [
        {**result, "path": str(result["path"])}
        for result in results
    ]
    st.dataframe(display_results)

    st.subheader("Integrity Controls")
    if st.button("Create Baseline"):
        count = create_baseline(upload_path, baseline_path)
        st.success(f"Baseline created successfully for {count} files.")

    if baseline_path.is_file():
        if st.button("Check Integrity"):
            try:
                integrity_results = check_integrity(upload_path, baseline_path)
            except ValueError as exc:
                st.warning(str(exc))
            else:
                st.dataframe(integrity_results)