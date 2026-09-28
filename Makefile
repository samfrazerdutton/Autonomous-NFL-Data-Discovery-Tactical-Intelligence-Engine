.PHONY: demo backend frontend test build-sample

demo:
	bash scripts/demo.sh

backend:
	cd backend && .venv/Scripts/python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

frontend:
	cd frontend && npm run dev

test:
	cd backend && .venv/Scripts/python.exe -m pytest -q

pipeline:
	cd backend && .venv/Scripts/python.exe scripts/run_pipeline.py 2022 2023
