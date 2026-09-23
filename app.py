"""HTTP API for deploying the Wikipedia research bot."""

from flask import Flask, jsonify, render_template, request

from src.exceptions import WikiBotError
from src.research_bot import ResearchBot

app = Flask(__name__)
bot = ResearchBot()


@app.get("/")
def dashboard():
    return render_template("index.html")


@app.get("/health")
def health():
    return jsonify({"status": "ok", "stored_articles": bot.stats()["stored_articles"]})


@app.get("/search")
def search():
    query = request.args.get("q", "")
    limit = request.args.get("limit", default=10, type=int)
    results = bot.search(query, limit=max(1, min(limit, 50)))
    return jsonify(
        [
            {"title": result.title, "page_id": result.page_id, "snippet": result.snippet}
            for result in results
        ]
    )


@app.post("/research")
def research():
    payload = request.get_json(silent=True) or {}
    title = payload.get("title", "")
    article = bot.research_topic(
        title,
        fetch_full_text=bool(payload.get("full_text", False)),
    )
    return jsonify(article.to_dict())


@app.get("/articles/recent")
def recent_articles():
    limit = request.args.get("limit", default=10, type=int)
    articles = bot.recent(limit=max(1, min(limit, 100)))
    return jsonify([article.to_dict() for article in articles])


@app.post("/ask")
def ask():
    payload = request.get_json(silent=True) or {}
    question = payload.get("question", "")
    limit = payload.get("limit", 5)
    return jsonify(bot.ask(question, limit=max(1, min(int(limit), 10))))


@app.errorhandler(WikiBotError)
def handle_bot_error(error):
    return jsonify({"error": str(error)}), 400


@app.errorhandler(Exception)
def handle_unexpected_error(error):
    app.logger.exception("Unexpected API error")
    return jsonify({"error": "Internal server error"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
