from flask import Flask, render_template, request, redirect, url_for
import json, os
from datetime import datetime
from collections import defaultdict
from werkzeug.utils import secure_filename

# --- basic config ------------------------------------------------------------
APP_ROOT       = os.path.dirname(os.path.abspath(__file__))
DATA_FILE      = os.path.join(APP_ROOT, "trades.json")
UPLOAD_FOLDER  = os.path.join(APP_ROOT, "static", "uploads")
ALLOWED_EXT    = {"png", "jpg", "jpeg", "gif"}

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --- helpers -----------------------------------------------------------------
def _ensure_data_file():
    """Create an empty JSON list if the file is missing or unreadable."""
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w") as f:
            json.dump([], f)

def load_trades():
    _ensure_data_file()
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:          # corrupted file → reset
        with open(DATA_FILE, "w") as f:
            json.dump([], f)
        return []

def save_trades(trades):
    with open(DATA_FILE, "w") as f:
        json.dump(trades, f, indent=4)

def allowed(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT
    )

# --- routes ------------------------------------------------------------------
@app.route("/")
def dashboard():
    trades = load_trades()
    total = len(trades)
    wins  = sum(1 for t in trades if t["result"] > 0)
    loss  = sum(1 for t in trades if t["result"] < 0)
    pnl   = round(sum(t["result"] for t in trades), 2)
    win_rate = round(wins / total * 100, 2) if total else 0

    best  = max(trades, key=lambda t: t["result"], default=None)
    worst = min(trades, key=lambda t: t["result"], default=None)

    monthly = defaultdict(float)
    for t in trades:
        try:
            month = datetime.strptime(t["date"], "%Y-%m-%d").strftime("%B %Y")
        except ValueError:
            month = "Unknown"
        monthly[month] += t["result"]

    return render_template(
        "index.html",
        total=total, wins=wins, losses=loss, profit=pnl,
        win_rate=win_rate, best=best, worst=worst,
        monthly=sorted(monthly.items())       # chronological
    )

@app.route("/trades")
def trade_log():
    trades = load_trades()[::-1]            # newest first
    return render_template("trades.html", trades=trades)

@app.route("/add", methods=["GET", "POST"])
def add_trade():
    if request.method == "POST":
        stock      = request.form["stock"].upper()
        direction  = request.form["direction"]
        entry      = float(request.form["entry"])
        exit_      = float(request.form["exit"])
        qty        = int(request.form["qty"])
        date       = request.form["date"]           # expect yyyy-mm-dd
        result     = round(
            (exit_ - entry) * qty if direction == "Buy" else
            (entry - exit_) * qty, 2
        )

        img_name = ""
        img_file = request.files.get("image")
        if img_file and allowed(img_file.filename):
            img_name = secure_filename(img_file.filename)
            img_file.save(os.path.join(app.config["UPLOAD_FOLDER"], img_name))

        trades = load_trades()
        trades.append({
            "stock": stock, "direction": direction,
            "entry": entry, "exit": exit_, "qty": qty,
            "date": date, "result": result, "image": img_name
        })
        save_trades(trades)
        return redirect(url_for("dashboard"))

    return render_template("add_trade.html")

# --- run ---------------------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)
