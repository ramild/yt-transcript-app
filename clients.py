import re
import random
import json
import vk_api

from typing import Any, Dict, List, Tuple, Union

import pyyoutube
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._transcripts import TranscriptList

VideoSubs = List[Dict[str, Any]]


class YouTubeVideosHandler:
    # Codes of languages I can understand.
    OK_LANGUAGE_CODES = ["en-GB", "en", "en-US", "ru"]
    # Error message if no relevant subtitles are found.
    SORRY_MESSAGE = "Unfortunately, there are no subs for this video :("

    def __init__(self, yt_api_client):
        self._yt_api_client = yt_api_client
        self._yt_transcripts_client = YouTubeTranscriptApi()

    @staticmethod
    def from_api_token_path(token_filepath: str):
        with open(token_filepath) as f:
            api_key = f.read()
        return YouTubeVideosHandler(
            yt_api_client=pyyoutube.Api(api_key=api_key),
        )

    def __call__(
        self,
        video_url_or_id: str,
        html_render=False,
    ) -> Dict[str, str]:
        video_id = video_url_or_id
        if "youtube" in video_url_or_id:
            video_id = video_url_or_id.split("=")[-1]
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        subs = self._yt_transcripts_client.list_transcripts(video_id)
        video_subs = self._get_video_subs(subs)
        if video_subs is None:
            return {
                "video_url": video_url,
                "video_id": video_id,
                "text": self.SORRY_MESSAGE,
            }
        start_seconds = self._get_timestamps(video_id, video_subs)
        script_sentences = self._convert_to_sentences(video_subs)
        text = self._generate_text(script_sentences, start_seconds)
        if html_render:
            text = text.replace("\n\n", "<br><br>")
        return {
            "video_url": video_url,
            "video_id": video_id,
            "text": text,
        }

    def _get_video_subs(
        self,
        subs: TranscriptList,
    ) -> Union[VideoSubs, None]:
        for language_code in subs._manually_created_transcripts.keys():
            if language_code in self.OK_LANGUAGE_CODES:
                return subs._manually_created_transcripts[language_code].fetch()
        return None

    def _get_timestamps(
        self,
        video_id: str,
        video_subs: VideoSubs,
    ) -> List[float]:
        video_by_id = self._yt_api_client.get_video_by_id(
            video_id=video_id,
        )
        description = video_by_id.items[0].snippet.description
        timestamps = re.findall("\d{1,2}:\d{2}", description)
        start_seconds = []

        for timestamp in timestamps:
            mins, secs = timestamp.split(":")
            start_seconds.append(int(mins) * 60.0 + int(secs))
        start_seconds.append(video_subs[-1]["start"] + video_subs[-1]["duration"])

        if start_seconds[0] == 0.0:
            return start_seconds[1:]
        return start_seconds

    def _convert_to_sentences(
        self,
        video_subs: VideoSubs,
    ) -> VideoSubs:
        script_sentences = []
        current_sentence = ""
        start_time = 0.0

        for sub in video_subs:
            current_sentence += sub["text"].replace("\n", " ") + " "
            if sub["text"].endswith((".", "!", "?")):
                duration = round(
                    sub["start"] + sub["duration"] - start_time,
                    2,
                )
                script_sentences.append(
                    {
                        "text": current_sentence,
                        "start": start_time,
                        "duration": duration,
                    }
                )
                current_sentence = ""
                start_time = duration
        return script_sentences

    def _generate_text(
        self,
        script_sentences: VideoSubs,
        start_seconds: List[float],
    ) -> str:
        video_transcript = ""
        current_paragraph = 0

        for sub_time in script_sentences:
            end_time = sub_time["start"] + sub_time["duration"]
            if (
                current_paragraph < len(start_seconds)
                and end_time > start_seconds[current_paragraph]
            ):
                if start_seconds[current_paragraph] > sub_time["start"] + 2.0:
                    video_transcript += sub_time["text"]
                    continue
                if len(video_transcript) > 10:
                    current_paragraph += 1
                    video_transcript += "\n\n"
            video_transcript += sub_time["text"]

        generated_text = video_transcript.strip("_- ")
        generated_text = re.sub(r"\(.*?\) ", "", generated_text)
        return generated_text


class VkRandomMemeFinder:
    PHOTO_WIDTH_THRESHOLD = 600
    POST_URL = "https://vk.com/{domain}?w=wall{owner_id}_{item_id}"

    def __init__(
        self,
        vk_client,
        page_domain_name: str,
        likes_threshold: int,
    ):
        self._vk_client = vk_client
        self._page_domain_name = page_domain_name
        self._likes_threshold = likes_threshold
        self._collect_memes()

    @staticmethod
    def from_config(
        json_path: str,
        page_domain_name: str,
        likes_threshold: int,
    ):
        with open(json_path, "r") as json_file:
            client_credentials = json.load(json_file)

        vk_session = vk_api.VkApi(
            client_credentials["email_or_phone_number"],
            client_credentials["password"],
        )
        vk_session.auth()
        vk_client = vk_session.get_api()
        return VkRandomMemeFinder(
            vk_client,
            page_domain_name,
            likes_threshold,
        )

    def __call__(self) -> Dict[str, str]:
        # Get random meme from a public page.
        index = random.randint(0, self._memes_count - 1)
        return {
            "meme_url": self._photo_urls[index],
            "meme_credit": self._photo_credits[index],
        }

    def _collect_memes(self) -> List[Tuple[str, str]]:
        wall_posts = self._vk_client.wall.get(
            domain=self._page_domain_name,
            count=100,
        )["items"]

        self._photo_urls = []
        self._photo_credits = []

        for wall_post in wall_posts:
            if "attachments" not in wall_post:
                continue
            likes_count = self._vk_client.likes.getList(
                type="post",
                owner_id=wall_post["owner_id"],
                item_id=wall_post["id"],
            )["count"]
            photo = wall_post["attachments"][0].get("photo")
            if photo and likes_count > self._likes_threshold:
                for photo_item in photo["sizes"]:
                    if photo_item["width"] > self.PHOTO_WIDTH_THRESHOLD:
                        self._photo_urls.append(photo_item["url"])
                        self._photo_credits.append(
                            self.POST_URL.format(
                                domain=self._page_domain_name,
                                owner_id=wall_post["owner_id"],
                                item_id=wall_post["id"],
                            )
                        )
                        break
        self._memes_count = len(self._photo_urls)
        return zip(self._photo_urls, self._photo_credits)
