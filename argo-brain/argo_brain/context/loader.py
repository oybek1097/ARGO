"""Context-file loading and @-reference expansion (spec section 4.2).

This module implements two pieces of the ARGO context subsystem:

* :class:`ContextLoader` -- discovers well-known ARGO context files in a
  directory and assembles them into a single labelled context block.
* :func:`expand_refs` -- expands ``@``-references found in arbitrary text,
  inlining file contents or listing folders.

The implementation relies only on the Python standard library.
"""

import os
import re

# Well-known ARGO context filenames, in the order they should be assembled
# (spec section 4.2). Files that are absent are simply skipped.
CONTEXT_FILES = ("MEMORY.md", "USER.md", "AGENTS.md", ".argo.md")

# Maximum number of bytes inlined for a single @file reference (~8 KB).
MAX_INLINE_BYTES = 8 * 1024

# Pattern matching an @-reference. A reference must be preceded by the start
# of the string or whitespace -- this prevents email addresses such as
# ``user@example.com`` (where ``@`` sits mid-word) from being treated as
# references. The captured group is the path that follows the ``@``.
_REF_PATTERN = re.compile(r"(?:^|(?<=\s))@([^\s@]+)")


class ContextLoader:
    """Discover and assemble ARGO context files (spec section 4.2).

    A context file holds persistent guidance for the agent. The loader scans
    a directory for the well-known filenames and exposes both the raw mapping
    and a single concatenated, labelled block.
    """

    def __init__(self, filenames=CONTEXT_FILES):
        """Create a loader.

        :param filenames: Iterable of context filenames to look for. Defaults
            to the spec-defined :data:`CONTEXT_FILES`.
        """
        self.filenames = tuple(filenames)

    def load(self, directory):
        """Scan *directory* for ARGO context files.

        :param directory: Path of the directory to scan.
        :returns: A ``dict`` mapping each present filename to its text
            content. Absent files are omitted entirely.
        """
        found = {}
        for name in self.filenames:
            path = os.path.join(directory, name)
            if os.path.isfile(path):
                try:
                    with open(path, "r", encoding="utf-8", errors="replace") as fh:
                        found[name] = fh.read()
                except OSError:
                    # An unreadable file is treated as if it were absent.
                    continue
        return found

    def assemble(self, directory):
        """Concatenate the discovered context files into one labelled block.

        Each file is preceded by a header line of the form
        ``# Context: <filename>`` so the agent can attribute guidance to its
        source. Files are emitted in the configured order.

        :param directory: Path of the directory to scan.
        :returns: A single string containing every discovered context file,
            or an empty string when none are present.
        """
        found = self.load(directory)
        blocks = []
        for name in self.filenames:
            if name in found:
                content = found[name].rstrip("\n")
                blocks.append("# Context: {0}\n{1}".format(name, content))
        return "\n\n".join(blocks)


def _format_folder_listing(path):
    """Return a human-readable listing of the directory at *path*.

    Entries are sorted; directories are suffixed with ``/`` to distinguish
    them from regular files.
    """
    try:
        entries = sorted(os.listdir(path))
    except OSError:
        return None
    lines = []
    for entry in entries:
        full = os.path.join(path, entry)
        suffix = "/" if os.path.isdir(full) else ""
        lines.append("- {0}{1}".format(entry, suffix))
    if not lines:
        return "(empty folder)"
    return "\n".join(lines)


def _expand_one(ref, base_dir):
    """Expand a single reference path relative to *base_dir*.

    :param ref: The path captured after the ``@`` sign.
    :param base_dir: Directory references are resolved against.
    :returns: The expanded replacement text, or ``None`` when the reference
        cannot be resolved (in which case it should be left untouched).
    """
    target = os.path.join(base_dir, ref)

    # A trailing slash explicitly requests a folder listing.
    if ref.endswith("/"):
        if os.path.isdir(target):
            listing = _format_folder_listing(target)
            if listing is not None:
                return "[@{0}]\n{1}".format(ref, listing)
        return None

    # A real directory (without trailing slash) is also listed.
    if os.path.isdir(target):
        listing = _format_folder_listing(target)
        if listing is not None:
            return "[@{0}/]\n{1}".format(ref, listing)
        return None

    # Otherwise, treat the reference as a file to inline.
    if os.path.isfile(target):
        try:
            with open(target, "r", encoding="utf-8", errors="replace") as fh:
                data = fh.read(MAX_INLINE_BYTES + 1)
        except OSError:
            return None
        truncated = len(data) > MAX_INLINE_BYTES
        if truncated:
            data = data[:MAX_INLINE_BYTES]
        body = data.rstrip("\n")
        if truncated:
            body += "\n... [truncated at {0} bytes]".format(MAX_INLINE_BYTES)
        return "[@{0}]\n{1}".format(ref, body)

    # Unresolvable -- caller leaves the original text in place.
    return None


def expand_refs(text, base_dir="."):
    """Expand ``@``-references in *text* (spec section 4.2).

    Two reference forms are recognised:

    * ``@path/to/file`` -- the file's contents are inlined (capped at
      ~8 KB; longer files are truncated with a marker).
    * ``@folder/`` -- the folder's entries are listed.

    A reference must appear at the start of the text or immediately after
    whitespace. This deliberately leaves email addresses such as
    ``user@example.com`` untouched, because their ``@`` sits mid-word.
    References that cannot be resolved are left exactly as written.

    :param text: The input text possibly containing references.
    :param base_dir: Directory used to resolve relative reference paths.
    :returns: The text with every resolvable reference expanded inline.
    """
    if not text:
        return text

    def _replace(match):
        ref = match.group(1)
        expanded = _expand_one(ref, base_dir)
        if expanded is None:
            # Keep the original matched text unchanged.
            return match.group(0)
        # The match may include a leading whitespace via the lookbehind, but
        # since we used a non-capturing lookbehind the whole match is "@ref".
        return expanded

    return _REF_PATTERN.sub(_replace, text)
