.PHONY: setup pipeline dashboard

setup:
	python3 -m pip install -r requirements.txt

pipeline:
	python3 load_data.py

dashboard:
	python3 generate_dashboard.py
	@echo ""
	@echo "Dashboard: http://localhost:8050/dashboard.html"
	@echo "In Codespaces: open the forwarded port 8050 in the Ports tab, then navigate to /dashboard.html"
	@echo ""
	-lsof -ti:8050 | xargs kill -9 2>/dev/null || true
	python3 -m http.server 8050
