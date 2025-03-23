import base64
import mimetypes
import re
import os
from urllib.parse import quote, unquote, urlparse, urlunparse


class FileHandler:
    @staticmethod
    def file_to_base64(file_path):
        """
        Converts a file to its base64 representation.
        """
        try:
            mime_type, _ = mimetypes.guess_type(file_path)
            mime_type = mime_type or 'application/octet-stream'
            with open(file_path, "rb") as file:
                base64_str = base64.b64encode(file.read()).decode('utf-8')
            return mime_type, base64_str
        except FileNotFoundError:
            return None, None

    @staticmethod
    def is_image_file(file_path):
        """
        Checks if a file is an image based on its extension.
        """
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff']
        _, ext = os.path.splitext(file_path)
        return ext.lower() in image_extensions


class Normalizer:
    @staticmethod
    def normalize_file_url(url):
        """
        Normalizes a file URL, ensuring it works across different operating systems.
        """
        parsed_url = urlparse(url)
        if parsed_url.scheme == 'file':
            file_path = unquote(parsed_url.path)
            if re.match(r'^[a-zA-Z]:\\', file_path):  # Windows style path
                file_path = file_path.replace('\\', '/')
                if os.name == 'nt':  # Running on Windows
                    file_path = file_path.lstrip('/')  # Remove leading slash
            normalized_path = os.path.normpath(file_path)
            return urlunparse(parsed_url._replace(path=normalized_path))
        return url


class MarkdownParser:
    def __init__(self, file_handler, normalizer):
        self.file_handler = file_handler
        self.normalizer = normalizer

    def parse_markdown(self, markdown_text):
        """
        Parses markdown text, converts local file URLs to base64 images if they are images, and generates appropriate links.
        """
        def replace_link(match):
            alt_text = match.group(1)
            url = self.normalizer.normalize_file_url(match.group(2))

            if url.startswith('file://'):
                parsed_url = urlparse(url)
                file_path = parsed_url.path
                if self.file_handler.is_image_file(file_path):
                    mime_type, base64_str = self.file_handler.file_to_base64(file_path)
                    if mime_type:
                        img_html = (
                            f'<div style="text-align: center; margin-bottom: 20px;">'
                            f'<a href="{url}" target="_blank" style="display: block; margin-bottom: 10px;">View Full Image</a>'
                            f'<img src="data:{mime_type};base64,{base64_str}" '
                            f'alt="{alt_text}" style="max-width: 300px; max-height: 300px; border-radius: 15px; border: 2px solid #ccc;" />'
                            f'</div>'
                        )
                        return img_html
                else:
                    return f'<a href="{url}" target="_blank">{alt_text}</a>'
            return match.group(0)  # If not a local file, leave the link as is

        # Regex to find markdown image links
        pattern = re.compile(r'!\[([^\]]*)\]\(([^)]+)\)')
        # Check if any links are present
        if not pattern.search(markdown_text):
            return markdown_text

        new_markdown = pattern.sub(replace_link, markdown_text)
        return new_markdown


class LinkGenerator:
    @staticmethod
    def generate_markdown_links(search_results):
        """
        Generates markdown links or image tags from search results.
        """
        links = []
        for result in search_results['metadatas']:
            for metadata in result:
                content_preview = metadata.get('content', 'Click to view document')
                link = f'<a href="{metadata["source"]}">{content_preview}</a>'
                links.append(link)
        return "\n\n".join(links)


# Example usage for testing

# # Test markdown text
# markdown_text = """
# This is an example markdown with a local image link:
# ![Example Image](file:///C:/path/to/local/image.jpg)
#
# And a local file link:
# ![Document](file:///C:/path/to/local/document.pdf#page=5)
#
# And a Windows path:
# ![Windows Path](C:\\path\\to\\local\\file.txt)
# """
#


# print(processed_markdown)