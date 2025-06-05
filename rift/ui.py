
"""Streamlit UI for AI Agent"""
import streamlit as st
import pandas as pd
from pathlib import Path
import sqlite3
import yaml
import datetime
import uuid
from agent import Agent

from database import get_connection

WORKSPACE = Path(__file__).parent / 'workspace'
CONFIG = yaml.safe_load((WORKSPACE / 'agent_config.yaml').read_text())
DB_PATH = WORKSPACE / CONFIG.get('database_path', 'state.db')

conn = get_connection(DB_PATH)

st.set_page_config(page_title='AI Agent Control UI', layout='wide')

st.sidebar.title('Instances')
status_filters = st.sidebar.multiselect(
    'Filter status',
    ['pending', 'processing', 'paused', 'error', 'done'],
    default=['pending', 'processing', 'error'],
)

if status_filters:
    placeholders = ','.join(['?'] * len(status_filters))
    query = (
        f"SELECT * FROM instances WHERE status IN ({placeholders})"
        " ORDER BY created_at DESC"
    )
    df = pd.read_sql_query(query, conn, params=status_filters)
else:
    df = pd.DataFrame(columns=['instance_id', 'status', 'created_at'])

st.sidebar.write(df[['instance_id','status','created_at']])

instance_id = st.sidebar.text_input('Select instance_id to view')
if instance_id:
    inst = conn.execute("SELECT * FROM instances WHERE instance_id=?", (instance_id,)).fetchone()
    if inst:
        st.header(f"Instance {instance_id}")
        st.write(dict(inst))
        history = pd.read_sql_query("SELECT * FROM history_entries WHERE instance_id=? ORDER BY entry_id", conn, params=[instance_id])
        st.subheader('History')
        st.write(history)
    else:
        st.warning('Instance not found')
else:
    st.write('Select an instance from the sidebar')


st.markdown("---")
st.header("🧠 ARC Command Console")

with st.form("command_form"):
    rec_command = st.text_area("Enter recursive command", height=200, placeholder="command: analyze_folder\nagents: observer\n...")
    execute = st.form_submit_button("Execute Command")

    if execute:
        # Simulate user dropping a .rec file into input/
        command_id = uuid.uuid4().hex[:6]
        input_dir = WORKSPACE / "input"
        input_dir.mkdir(parents=True, exist_ok=True)
        file_path = input_dir / f"manual_{command_id}.rec"
        file_path.write_text(rec_command)

        st.success(f"Command written to input folder as `{file_path.name}`")

        # Trigger agent run once
        agent = Agent(WORKSPACE)
        agent.ingest_new_files()
        agent.process_pending()
        st.info("Agent processed new command.")

