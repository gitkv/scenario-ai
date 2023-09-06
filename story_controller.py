import os

from flask import Blueprint, abort, jsonify, make_response, request, send_file

from repos import StoryRepository


class StoryController:
    def __init__(self, story_repository: StoryRepository):
        self.story_repository = story_repository
        self.story_routes = Blueprint('story_routes', __name__)
        
        @self.story_routes.route("/story/getStory", methods=["GET"])
        def get_scenario():
            story = self.story_repository.get_story_by_priority()
            if story is None:
                abort(404, "No story found")
            return jsonify(story.dict())

        @self.story_routes.route("/delete/<string:story_id>", methods=["DELETE"])
        def delete_scenario(story_id):
            self.story_repository.delete_story(story_id)
            return make_response(jsonify({"message": "Deleted successfully"}), 200)

        @self.story_routes.route("/audio/<path:audio_path>", methods=["GET"])
        def get_audio(audio_path):
            full_audio_path = os.path.join(os.getcwd(), audio_path)
            if os.path.exists(full_audio_path):
                return send_file(full_audio_path)
            else:
                abort(404, "Audio file not found")
