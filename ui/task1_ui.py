import streamlit as st
import os
import json
import sys
import pathlib
import re
 

main_path = str(pathlib.Path(__file__).resolve().parents[1])
if main_path not in sys.path:
    sys.path.append(main_path)
 
from common.directory_parser import DirectoryParser
 
TEMP_DATA_DIR = "temp_data"
DOCS_DIR = "docs"
 
def clean_markdown(text: str) -> str:
    """Remove markdown headers like #, ##, etc."""
    return re.sub(r"#+ ", "", text).strip()
 
def find_md_by_filename_only(json_filename: str):
    """
    From 'folder_subfolder_filename.md.json' → extract 'filename.md',
    then find exact filename match recursively inside /docs.
    """
    stem = pathlib.Path(json_filename).stem  
    if stem.endswith(".md"):
        md_file = stem
    else:
        md_file = stem.split("_")[-1]
        md_file += ".md"
 
    for root, _, files in os.walk(DOCS_DIR):
        for file in files:
            if file == md_file:
                return os.path.join(root, file)
    return None
 
def render_tree(path, level=0):
    try:
        for item in sorted(os.listdir(path)):
            full_path = os.path.join(path, item)
            if os.path.isdir(full_path):
                with st.expander(f"{' ' * level}📁 {item}", expanded=False):
                    render_tree(full_path, level + 1)
            elif item.endswith(".md"):
                st.markdown(f"{' ' * level}- {item}")
    except Exception as e:
        st.error(f"Error reading folder: {e}")
 
def render():
    """Render the Task 1 UI for parsing Markdown files to JSON."""
    st.title(" Markdown to JSON Parser")
 
    
    if st.button(" Parse Documents "):
        with st.spinner("Parsing Markdown files..."):
            try:
                DirectoryParser().parse()
                st.success(" JSONs created in `/temp_data`.")
            except Exception as e:
                st.error(f"Error: {e}")
 
    
    st.markdown("<hr>", unsafe_allow_html=True)
    st.subheader(" Folder Structure: `/docs`")
 
    if os.path.exists(DOCS_DIR):
        render_tree(DOCS_DIR)
    else:
        st.warning(" `/docs` not found.")
 
   
    st.markdown("<hr>", unsafe_allow_html=True)
    st.subheader(" Preview JSON + Markdown Content")
 
    if not os.path.exists(TEMP_DATA_DIR):
        st.info("ℹ Run Task 1 to generate output.")
        return
 
    files = [f for f in os.listdir(TEMP_DATA_DIR) if f.endswith(".json")]
    if not files:
        st.warning(" No JSON found in `/temp_data/`.")
        return
 
    selected = st.selectbox("Select a JSON file", files)
   
    try:
        
        with open(os.path.join(TEMP_DATA_DIR, selected), "r", encoding="utf-8") as f:
            data = json.load(f)
 
        st.subheader(" Full JSON Structure")
        st.code(json.dumps(data, indent=2), language="json")
 
       
        md_path = find_md_by_filename_only(selected)
        if md_path:
            with open(md_path, "r", encoding="utf-8") as f:
                md_content = f.read()
            st.subheader(f" Original Markdown Content: `{os.path.relpath(md_path, DOCS_DIR)}`")
            st.text_area("Content", clean_markdown(md_content), height=300, disabled=True)
        else:
            st.warning(" Corresponding `.md` file content  not found in `/docs/`.")
 
    except Exception as e:
        st.error(f"Error loading selected file: {e}")
 
 
