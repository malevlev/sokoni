#!/bin/bash
echo "  ╔══════════════════════════════════════════╗"
echo "  ║       SOKONI WATCH v2.0                  ║"
echo "  ║  Nairobi Hawker Intelligence System      ║"
echo "  ╚══════════════════════════════════════════╝"
pip3 install -r requirements.txt -q
mkdir -p data
echo "  ✅ Open → http://localhost:5000"
echo "  👔 Admin: admin / sokoni2024"
echo "  👩‍🌾 Hawker: mama_njeri / njeri2024"
command -v open &>/dev/null && (sleep 2 && open http://localhost:5000) &
command -v xdg-open &>/dev/null && (sleep 2 && xdg-open http://localhost:5000) &
python3 app.py
