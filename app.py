import requests
import toga
from toga.constants import COLUMN, ROW
from toga.style import Pack
from toga.style.pack import BOLD

from requests.exceptions import HTTPError
import os

if "SHORTCUT_API_TOKEN" not in os.environ:
    raise EnvironmentError("SHORTCUT_API_TOKEN is not set in the environment!")
else:
    SHORTCUT_API_TOKEN = os.getenv("SHORTCUT_API_TOKEN")


class StoryCard(toga.Box):
    def __init__(self, story, app, style=None):
        super().__init__(
            style=Pack(direction=COLUMN, padding=10, background_color="blue")
        )
        # Pass the main app instance to access methods within it
        self.app = app
        self.story = story

        name_label = toga.Label(f"Name: {story.get('name', 'N/A')}")
        deadline_label = toga.Label(f"Deadline: {story.get('deadline', 'N/A')}")
        blocked_label = toga.Label(f"Blocked?: {story.get('blocked', 'N/A')}")
        tasks_completed_label = toga.Label(
            f"Tasks completed: {story.get('num_tasks_completed', 'N/A')}"
        )
        story_type_label = toga.Label(f"Type: {story.get('story_type', 'N/A')}")

        details_button = toga.Button(
            "View Details", on_press=self.app.show_story_details
        )

        self.add(name_label)
        self.add(deadline_label)
        self.add(blocked_label)
        self.add(tasks_completed_label)
        self.add(story_type_label)
        self.add(details_button)

        # Event listener to the whole StoryCard
        self.on_press = self.select_story

    def show_story_details(self, widget):
        # Call the method on the app instance
        self.app.show_story_details(self.story)

    def select_story(self, widget):
        self.on_select(self.story)


class ShortcutApp(toga.App):
    def startup(self):
        self.main_window = toga.MainWindow(title="Shortcut Stories")
        self.main_window.size = (800, 600)
        # Register a new font
        toga.Font.register("Roboto", "resources/fonts/Roboto/Roboto-Regular.ttf")
        # NOTE: not supported on Mac OS
        toga.Font.register(
            "Roboto bold", "resources/fonts/Roboto/Roboto-Regular.ttf", weight=BOLD
        )

        # Create the outer ScrollContainer
        self.outer_scroll_container = toga.ScrollContainer(
            horizontal=True, vertical=True
        )
        self.outer_scroll_container.style.height = 500
        self.outer_scroll_container.style.min_width = 500

        # Create the boxes that display in the scroll_container
        self.content_box = toga.Box(style=Pack(direction=COLUMN, padding=5))
        self.headers_box = toga.Box(style=Pack(direction=ROW, padding=5))

        # Box to hold the story columns
        self.columns_box = toga.Box(style=Pack(direction=ROW, padding=5))

        self.story_cards = {}

        # Minimum width for headers and story cards
        header_width = 280

        states = [
            "To Do",
            "Backlog",
            "In Progress",
            "Completed",
            "Blocked",
            "In Review",
            "Done",
        ]

        # Create story and header columns
        for state in states:
            # Create a new box to act as a column
            column_box = toga.Box(style=Pack(direction=COLUMN, padding=5))
            column_box.style.min_height = 200  # Set a minimum height for the column
            column_box.style.width = header_width

            # Uncomment to have header IN the story card

            # header_label = toga.Label(state, style=Pack(padding=(5, 5), background_color='white'))
            # header_label.style.font_weight = 'bold'
            # header_label.style.color = 'black'
            # column_box.add(header_label)

            spacer = toga.Box(style=Pack(flex=1))
            column_box.add(spacer)

            column_box.style.background_color = (
                "lightgrey"  # Set a temporary background color
            )
            column_box.style.flex = 1

            # Store the column box in the dictionary for later reference
            self.story_cards[state] = column_box

            self.columns_box.add(column_box)

            header_label = toga.Label(
                state,
                style=Pack(
                    padding=(5, 5),
                    background_color="white",
                    text_align="center",
                    font_family="Roboto",
                ),
            )
            header_label.style.font_weight = "bold"
            header_label.style.color = "black"
            header_label.style.width = header_width
            header_label.style.flex = 1

            self.headers_box.add(header_label)

        # Make sure that the content_box also has a flex attribute to grow within the main window
        self.content_box.style.flex = 1

        self.outer_scroll_container.content = self.columns_box

        # Create the selection widget for members
        self.member_selection = toga.Selection(on_change=self.on_member_selected)

        # Create a new box that will contain both headers and columns
        self.scrollable_content_box = toga.Box(style=Pack(direction=COLUMN))

        # Add the headers_and column box to the scrollable content box
        self.scrollable_content_box.add(self.headers_box)
        self.scrollable_content_box.add(self.columns_box)

        # Set the scrollable content box as the content of the outer_scroll_container
        self.outer_scroll_container.content = self.scrollable_content_box

        self.content_box.style.flex = 1

        # Main displays
        self.content_box.add(self.member_selection)
        self.content_box.add(self.outer_scroll_container)

        # Set the main content box as the content of the main window
        self.main_window.content = self.content_box
        self.main_window.show()

        # Fetch members to populate the selection widget
        self.fetch_members()

    def fetch_members(self):
        headers = {
            "Content-Type": "application/json",
            "Shortcut-Token": SHORTCUT_API_TOKEN,
        }
        response = requests.get(
            "https://api.app.shortcut.com/api/v3/members", headers=headers
        )
        if response.status_code == 200:
            self.members = response.json()
            self.member_selection.items = [
                member["profile"]["name"] for member in self.members
            ]

    def on_member_selected(self, widget):
        member_name = widget.value
        member_id = next(
            (
                member["id"]
                for member in self.members
                if member["profile"]["name"] == member_name
            ),
            None,
        )
        if member_id is not None:
            self.fetch_stories(member_id)
        else:
            raise ValueError("No member ID!")

    def fetch_stories(self, member_id):
        headers = {
            "Content-Type": "application/json",
            "Shortcut-Token": SHORTCUT_API_TOKEN,
        }
        body = {"owner_ids": [member_id], "archived": False}
        response = requests.post(
            "https://api.app.shortcut.com/api/v3/stories/search",
            headers=headers,
            json=body,
        )
        if response.status_code == 201:
            self.update_stories_view(response.json())
        else:
            error_msg = f"Bad request, status code: {response.status_code}"
            if response.text:
                error_msg += f", response text: {response.text}"

            raise HTTPError(error_msg)

    def fetch_story_details(self, story_id):
        headers = {
            "Content-Type": "application/json",
            "Shortcut-Token": SHORTCUT_API_TOKEN,
        }
        response = requests.get(
            f"https://api.app.shortcut.com/api/v3/stories/{story_id}", headers=headers
        )
        if response.status_code == 200:
            return response.json()
        else:
            error_msg = f"Bad request, status code: {response.status_code}"
            if response.text:
                error_msg += f", response text: {response.text}"

            raise HTTPError(error_msg)

    def show_story_details(self, widget):
        story_card = widget.parent
        story = story_card.story

        story_details = self.fetch_story_details(story["id"])

        if story_details:
            details_window = toga.Window(title=f"Story: {story_details['name']}")
            details_box = toga.Box(style=Pack(direction=COLUMN, padding=10))

            # Story Name and Type
            name_label = toga.Label(
                f"Name: {story_details['name']}", style=Pack(padding=(0, 0, 5, 0))
            )
            type_label = toga.Label(
                f"Type: {story_details['story_type']}", style=Pack(padding=(0, 0, 5, 0))
            )

            # Description (displays as markdown)
            description_label = toga.Label(
                f"Description: {story_details['description']}",
                style=Pack(padding=(0, 0, 5, 0)),
            )

            # Story ID and Global ID
            id_label = toga.Label(
                f"Story ID: {story_details['id']}", style=Pack(padding=(0, 0, 5, 0))
            )
            global_id_label = toga.Label(
                f"Global ID: {story_details['global_id']}",
                style=Pack(padding=(0, 0, 5, 0)),
            )

            # Dates
            created_at_label = toga.Label(
                f"Created At: {story_details['created_at']}",
                style=Pack(padding=(0, 0, 5, 0)),
            )
            updated_at_label = toga.Label(
                f"Updated At: {story_details['updated_at']}",
                style=Pack(padding=(0, 0, 5, 0)),
            )
            deadline_label = toga.Label(
                f"Deadline: {story_details.get('deadline', 'No Deadline')}",
                style=Pack(padding=(0, 0, 5, 0)),
            )

            # Status
            status_label = toga.Label(
                f"Status: {'Completed' if story_details['completed'] else 'In Progress'}",
                style=Pack(padding=(0, 0, 5, 0)),
            )

            # Assignees
            owners_label = toga.Label(
                f"Owners: {', '.join(story_details['owner_ids'])}",
                style=Pack(padding=(0, 0, 5, 0)),
            )
            followers_label = toga.Label(
                f"Followers: {', '.join(story_details['follower_ids'])}",
                style=Pack(padding=(0, 0, 5, 0)),
            )

            # Tasks
            tasks_details = [
                f"{task['description']} - {'Completed' if task['complete'] else 'Incomplete'}"
                for task in story_details["tasks"]
            ]
            tasks_label = toga.Label(
                f"Tasks: {', '.join(tasks_details)}", style=Pack(padding=(0, 0, 5, 0))
            )

            # Labels
            labels_label = toga.Label(
                f"Labels: {', '.join(label['name'] for label in story_details['labels'])}"
            )

            # App URL TODO: make shareable
            app_url_label = toga.Label(
                f"App URL: {story_details['app_url']}", style=Pack(padding=(0, 0, 5, 0))
            )

            # Add all the labels to the details_box
            for label in [
                name_label,
                type_label,
                description_label,
                id_label,
                global_id_label,
                created_at_label,
                updated_at_label,
                deadline_label,
                status_label,
                owners_label,
                followers_label,
                app_url_label,
                tasks_label,
                labels_label,
            ]:
                details_box.add(label)

            details_window.content = details_box
            details_window.show()
        else:
            raise Exception("Failed to fetch story details.")

    def update_stories_view(self, stories):

        # Clear existing cards
        for state, container in self.story_cards.items():
            while container.children:
                container.remove(container.children[0])

        state_id_mapping = {
            500000007: "To Do",
            500000008: "In Progress",
            500000006: "Backlog",
            500000009: "Done",
            500000005: "In Review",
            500000004: "Completed",
        }
        # Add new stories
        for story in stories:
            state_id = story.get("workflow_state_id")
            state_name = state_id_mapping.get(
                state_id, "To Do"
            )  # Default to 'To Do' if no match

            if state_name in self.story_cards:
                card = StoryCard(story, self, style=Pack(padding=5))
                self.story_cards[state_name].add(card)
                self.story_cards[state_name].refresh()
            else:
                raise LookupError(f"No matching state for story with state ID {state_id}")

        # Ensure each column box has at least one visible widget
        for state, column_box in self.story_cards.items():
            has_content = False
            for i, child in enumerate(column_box.children):
                if (
                    not isinstance(child, toga.Box)
                    or child.style.visibility == "visible"
                ):
                    has_content = True
                    break

            if not has_content:
                placeholder = toga.Label(
                    "No stories!", style=Pack(padding=5, text_align="center")
                )
                column_box.add(placeholder)

        self.columns_box.refresh()


def main():
    return ShortcutApp("Shortcut", "org.eastonware.shortcut")


if __name__ == "__main__":
    main().main_loop()
