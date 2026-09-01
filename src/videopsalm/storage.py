"""SQLite-backed data layer for Bibles and local worship song libraries."""

from __future__ import annotations

import json
import sqlite3
import xml.etree.ElementTree as ET
from typing import Any, Iterable


def connect(path: str = ":memory:") -> sqlite3.Connection:
    """Open a SQLite database and initialize the schema."""
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    initialize(connection)
    return connection


def initialize(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS bible_translations (
            id TEXT PRIMARY KEY,
            language TEXT NOT NULL,
            name TEXT NOT NULL,
            licensed INTEGER NOT NULL DEFAULT 0,
            source TEXT NOT NULL DEFAULT 'local'
        );

        CREATE TABLE IF NOT EXISTS bible_verses (
            translation_id TEXT NOT NULL,
            book TEXT NOT NULL,
            chapter INTEGER NOT NULL,
            verse INTEGER NOT NULL,
            text TEXT NOT NULL,
            PRIMARY KEY (translation_id, book, chapter, verse),
            FOREIGN KEY (translation_id) REFERENCES bible_translations(id)
        );

        CREATE TABLE IF NOT EXISTS songs (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            language TEXT NOT NULL,
            licensed INTEGER NOT NULL DEFAULT 0,
            source_format TEXT NOT NULL,
            source_ref TEXT
        );

        CREATE TABLE IF NOT EXISTS song_sections (
            song_id TEXT NOT NULL,
            section_id TEXT NOT NULL,
            label TEXT NOT NULL,
            kind TEXT NOT NULL,
            position INTEGER NOT NULL,
            lines_json TEXT NOT NULL,
            PRIMARY KEY (song_id, section_id),
            FOREIGN KEY (song_id) REFERENCES songs(id)
        );
        """
    )
    connection.commit()


def add_translation(
    connection: sqlite3.Connection,
    *,
    translation_id: str,
    language: str,
    name: str,
    licensed: bool = True,
    source: str = "local",
) -> None:
    connection.execute(
        """
        INSERT OR REPLACE INTO bible_translations (id, language, name, licensed, source)
        VALUES (?, ?, ?, ?, ?)
        """,
        (translation_id, language, name, int(licensed), source),
    )
    connection.commit()


def import_bible_payload(
    connection: sqlite3.Connection,
    *,
    translation_id: str,
    language: str,
    name: str,
    licensed: bool,
    payload: Any,
) -> int:
    """Load a single translation from a thiagobodruk-style JSON payload."""
    add_translation(connection, translation_id=translation_id, language=language, name=name, licensed=licensed)
    records = payload if isinstance(payload, list) else [payload]
    inserted = 0
    for record in records:
        if not isinstance(record, dict):
            continue
        if 'chapters' in record and 'book' in record:
            book_name = str(record.get('book', '')).strip()
            for chapter_index, chapter_verses in enumerate(record.get('chapters', []), start=1):
                if not isinstance(chapter_verses, list):
                    continue
                for verse_index, verse_text in enumerate(chapter_verses, start=1):
                    if verse_text is None:
                        continue
                    connection.execute(
                        """
                        INSERT OR REPLACE INTO bible_verses (translation_id, book, chapter, verse, text)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (translation_id, book_name, chapter_index, verse_index, str(verse_text)),
                    )
                    inserted += 1
        elif all(key in record for key in ('book', 'chapter', 'verse', 'text')):
            connection.execute(
                """
                INSERT OR REPLACE INTO bible_verses (translation_id, book, chapter, verse, text)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    translation_id,
                    str(record['book']),
                    int(record['chapter']),
                    int(record['verse']),
                    str(record['text']),
                ),
            )
            inserted += 1
    connection.commit()
    return inserted


def lookup_verse(
    connection: sqlite3.Connection,
    *,
    translation_id: str,
    book: str,
    chapter: int,
    verse: int,
) -> str | None:
    row = connection.execute(
        """
        SELECT text FROM bible_verses
        WHERE translation_id = ? AND book = ? AND chapter = ? AND verse = ?
        """,
        (translation_id, str(book), int(chapter), int(verse)),
    ).fetchone()
    return None if row is None else row['text']


def upsert_song(
    connection: sqlite3.Connection,
    *,
    song_id: str,
    title: str,
    language: str,
    licensed: bool,
    source_format: str,
    source_ref: str | None = None,
    sections: Iterable[tuple[str, str, str, list[str]]] | None = None,
) -> None:
    connection.execute(
        """
        INSERT OR REPLACE INTO songs (id, title, language, licensed, source_format, source_ref)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (song_id, title, language, int(licensed), source_format, source_ref),
    )
    if sections is None:
        connection.commit()
        return
    connection.execute("DELETE FROM song_sections WHERE song_id = ?", (song_id,))
    for position, (section_id, label, kind, lines) in enumerate(sections):
        connection.execute(
            """
            INSERT INTO song_sections (song_id, section_id, label, kind, position, lines_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (song_id, section_id, label, kind, position, json.dumps(lines)),
        )
    connection.commit()


def import_openlyrics_xml(
    connection: sqlite3.Connection,
    xml_text: str,
    *,
    song_id: str | None = None,
    language: str = "en",
    licensed: bool = True,
    source_ref: str | None = None,
) -> str:
    """Import a minimal OpenLyrics XML document into the songs table."""
    root = ET.fromstring(xml_text)
    title_elem = root.find('./title')
    if title_elem is None:
        title_elem = root.find('./titles/title')
    title = (title_elem.text if title_elem is not None and title_elem.text else 'Untitled Song').strip()
    final_id = song_id or title.lower().replace(' ', '-')
    sections: list[tuple[str, str, str, list[str]]] = []
    index = 0
    for verse_element in root.findall('.//verse'):
        label = (verse_element.attrib.get('name') or f'Verse {index + 1}').strip()
        section_id = str(index)
        lines: list[str] = []
        for line_elem in verse_element.iter():
            if line_elem.tag == 'line' and (line_elem.text or '').strip():
                lines.append(line_elem.text.strip())
        if not lines:
            continue
        sections.append((section_id, label, 'verse', lines))
        index += 1
    if not sections:
        raise ValueError('OpenLyrics import requires at least one verse with line content')
    upsert_song(
        connection,
        song_id=final_id,
        title=title,
        language=language,
        licensed=licensed,
        source_format='openlyrics',
        source_ref=source_ref,
        sections=sections,
    )
    return final_id


def get_song_sections(connection: sqlite3.Connection, song_id: str) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT section_id, label, kind, position, lines_json
        FROM song_sections
        WHERE song_id = ?
        ORDER BY position ASC
        """,
        (song_id,),
    ).fetchall()
    result: list[dict[str, Any]] = []
    for row in rows:
        result.append(
            {
                'section_id': row['section_id'],
                'label': row['label'],
                'kind': row['kind'],
                'position': row['position'],
                'lines': json.loads(row['lines_json']),
            }
        )
    return result
