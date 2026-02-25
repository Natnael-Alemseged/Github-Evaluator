import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver

def read_state():
    conn = sqlite3.connect("checkpoints.db", check_same_thread=False)
    memory = SqliteSaver(conn)
    config = {"configurable": {"thread_id": "audit_001"}}
    state_tuple = memory.get_tuple(config)
    state = state_tuple.checkpoint["channel_values"]
    
    print("--- EVIDENCES ---")
    for k, v in state.get("evidences", {}).items():
        for ev in v:
            print(f"[{k}] {ev.content}")
            
    print("\n--- OPINIONS ---")
    for op in state.get("opinions", []):
        if op.criterion_id == "safe_tool_engineering":
            print(f"Judge: {op.judge} - Score: {op.score} - Argument: {op.argument}")

if __name__ == "__main__":
    read_state()
