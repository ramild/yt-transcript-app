import sys

from flask import Flask, render_template, request
from clients import YouTubeVideosHandler, VkRandomMemeFinder


DOBRIE_MEMES_DOMAIN_NAME = "dobriememes"

app = Flask(__name__)
yt_videos_handler = YouTubeVideosHandler.from_api_token_path(
    "../google-dev-token.txt",
)
vk_random_meme_finder = VkRandomMemeFinder.from_config(
    json_path="../vk_api_credentials.json",
    page_domain_name=DOBRIE_MEMES_DOMAIN_NAME,
    likes_threshold=3000,
)


@app.route("/form")
def form():
    return render_template("form.html")


@app.route("/data", methods=["POST", "GET"])
def data():
    if request.method == "GET":
        return (
            f"The URL /data is accessed directly. Try going to '/form' to submit form"
        )
    if request.method == "POST":
        yt_response = yt_videos_handler(
            request.form["video_url_or_id"],
            html_render=True,
        )
        # print(request.form, file=sys.stderr)
        meme = vk_random_meme_finder()
        form_data = {
            "video_embed_link": f"https://www.youtube.com/embed/{yt_response['video_id']}",
            "text": yt_response["text"],
            "meme_url": meme["meme_url"],
            "meme_credit": meme["meme_credit"],
        }
        return render_template("data.html", form_data=form_data)


if __name__ == "__main__":
    # Launch the Flask dev server
    app.run(host="localhost", port=5000, debug=True)
