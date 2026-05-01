"""
Validation tests: HTML structure and content correctness.

Verifies that:
1. A slide deck HTML file exists with proper slide structure
2. No marketing/campaign remnants in any HTML
3. SDK and security-domain content is present

Tests are expected to FAIL before implementation (TDD red phase).
"""

import os
import re
from html.parser import HTMLParser
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(filename):
    path = os.path.join(PROJECT_ROOT, filename)
    with open(path) as f:
        return f.read()


class HTMLStructureChecker(HTMLParser):
    """Lightweight HTML parser that collects tags, ids, and text content."""

    def __init__(self):
        super().__init__()
        self.tags = []
        self.ids = []
        self.classes = []
        self.text_content = []
        self.errors_found = []
        self._current_tag = None

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        self._current_tag = tag
        attrs_dict = dict(attrs)
        if "id" in attrs_dict:
            self.ids.append(attrs_dict["id"])
        if "class" in attrs_dict:
            self.classes.extend(attrs_dict["class"].split())

    def handle_data(self, data):
        stripped = data.strip()
        if stripped:
            self.text_content.append(stripped)

    def handle_endtag(self, tag):
        pass

    @property
    def full_text(self):
        return " ".join(self.text_content)


def _parse_html(filename):
    source = _read(filename)
    checker = HTMLStructureChecker()
    checker.feed(source)
    return checker, source


# ── Slide deck HTML ───────────────────────────────────────────────────

class TestSlideDeckHTML:
    """Validate that a slide deck HTML exists with proper structure."""

    def _find_slide_deck(self):
        """Find the slide deck file (could have various names)."""
        candidates = [
            "interactive.html",
            "slide_deck.html",
            "slides.html",
            "deck.html",
            "demo_slides.html",
            "coco_sdk_slides.html",
        ]
        for name in candidates:
            path = os.path.join(PROJECT_ROOT, name)
            if os.path.isfile(path):
                return name
        # Also check for any HTML file with 'slide' or 'interactive' in the name
        for f in os.listdir(PROJECT_ROOT):
            if f.endswith(".html") and ("slide" in f.lower() or "interactive" in f.lower()):
                if not f.startswith("example"):
                    return f
        return None

    def test_slide_deck_exists(self):
        name = self._find_slide_deck()
        assert name is not None, \
            "A slide deck HTML file must be created (e.g., interactive.html)"

    def test_slide_deck_is_valid_html(self):
        name = self._find_slide_deck()
        assert name is not None, "Slide deck not found"
        checker, source = _parse_html(name)
        assert "html" in checker.tags

    def test_slide_deck_has_slides(self):
        """Should have multiple slide sections/divs."""
        name = self._find_slide_deck()
        assert name is not None, "Slide deck not found"
        _, source = _parse_html(name)
        slide_pattern = re.compile(r'class="[^"]*slide[^"]*"', re.IGNORECASE)
        react_slide_pattern = re.compile(r'function\s+Slide\w*\s*\(', re.IGNORECASE)
        section_count = source.lower().count("<section")
        slide_matches = len(slide_pattern.findall(source))
        react_slides = len(react_slide_pattern.findall(source))
        total = section_count + slide_matches + react_slides
        assert total >= 3, \
            f"Slide deck should have at least 3 slides, found {total}"

    def test_slide_deck_has_security_content(self):
        name = self._find_slide_deck()
        assert name is not None, "Slide deck not found"
        _, source = _parse_html(name)
        source_lower = source.lower()
        assert "security" in source_lower or "threat" in source_lower, \
            "Slide deck must have security-domain content"

    def test_slide_deck_has_sdk_content(self):
        name = self._find_slide_deck()
        assert name is not None, "Slide deck not found"
        _, source = _parse_html(name)
        source_lower = source.lower()
        assert "sdk" in source_lower or "agent sdk" in source_lower or "cortex code" in source_lower, \
            "Slide deck must reference Cortex Code Agent SDK"

    def test_slide_deck_references_demo_scripts(self):
        """Slide deck should reference the demo Python scripts."""
        name = self._find_slide_deck()
        assert name is not None, "Slide deck not found"
        _, source = _parse_html(name)
        assert "demo_single_turn" in source, "Should reference demo_single_turn.py"
        assert "demo_multi_turn" in source, "Should reference demo_multi_turn.py"
        assert "demo_structured_output" in source, "Should reference demo_structured_output.py"
        assert "demo_chat_embed" in source, "Should reference demo_chat_embed.py"

    def test_slide_deck_has_chat_embed_section(self):
        """Must have a section about embedding in chat tools."""
        name = self._find_slide_deck()
        assert name is not None, "Slide deck not found"
        _, source = _parse_html(name)
        source_lower = source.lower()
        assert "embed" in source_lower or "chat" in source_lower, \
            "Slide deck must have a chat embedding section"

    def test_slide_deck_has_governance_section(self):
        """Must address governance / RBAC / cost controls."""
        name = self._find_slide_deck()
        assert name is not None, "Slide deck not found"
        _, source = _parse_html(name)
        source_lower = source.lower()
        governance_terms = ["governance", "rbac", "role-based", "cost"]
        found = any(term in source_lower for term in governance_terms)
        assert found, \
            f"Slide deck must address governance. Expected one of: {governance_terms}"
