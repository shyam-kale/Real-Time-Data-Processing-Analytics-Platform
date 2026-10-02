import sys, os
sys.path.insert(0, os.path.dirname(__file__))
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./dataflow.db"
os.environ["DATABASE_URL_SYNC"] = "sqlite:///./dataflow.db"

try:
    from app.main import app
    print("APP IMPORT OK")
    print("Routes loaded:", len([r for r in app.routes if hasattr(r, 'path')]))
    for r in app.routes:
        if hasattr(r, 'methods') and r.methods:
            print(f"  {list(r.methods)[0]:6s} {r.path}")
except Exception as e:
    import traceback
    print("IMPORT ERROR:", e)
    traceback.print_exc()
