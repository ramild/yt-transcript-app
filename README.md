# yt-transcript-app
A Flask-based web app that generates a transcript (structured with paragraphs) from a YouTube video's URL or id.

First, create a virtual environment:
```
conda create -n py38_webapp_env python=3.8
conda activate py38_webapp_env
```

Then install all the packages needed:
```
pip install flask python-youtube vk_api youtube_transcript_api
```

Alternatively, use:
```
pip install -r requirements.txt
```

Modify the paths to your VK credentials and Google API token in main.py. You can also manually modify the VK page domain. To run locally, use:
```
python main.py
```