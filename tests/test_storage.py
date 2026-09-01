import pytest

from videopsalm import connect, import_bible_payload, import_openlyrics_xml, lookup_verse


def test_imports_bible_payload_into_sqlite() -> None:
    db = connect(":memory:")
    payload = [
        {
            "book": "John",
            "chapters": [
                ["For God so loved the world", "that he gave his only Son"],
                ["In him was life"],
            ],
        }
    ]
    import_bible_payload(
        db,
        translation_id="demo-web",
        language="en",
        name="Demo translation",
        licensed=True,
        payload=payload,
    )
    assert lookup_verse(db, translation_id="demo-web", book="John", chapter=1, verse=1) == "For God so loved the world"
    assert lookup_verse(db, translation_id="demo-web", book="John", chapter=2, verse=1) == "In him was life"


def test_imports_openlyrics_into_song_sections() -> None:
    db = connect(":memory:")
    xml = '''
    <song>
      <title>Grace That Saved Me</title>
      <verse name="Verse 1">
        <line>Grace that saved me</line>
        <line>Now I stand</line>
      </verse>
      <verse name="Chorus">
        <line>With You I am home</line>
      </verse>
    </song>
    '''
    song_id = import_openlyrics_xml(db, xml, source_ref="demo.xml")
    rows = db.execute(
        "SELECT section_id, label, kind, lines_json FROM song_sections WHERE song_id = ? ORDER BY position ASC",
        (song_id,),
    ).fetchall()
    assert len(rows) == 2
    assert rows[0][1] == "Verse 1"
    assert rows[1][1] == "Chorus"


def test_invalid_openlyrics_raises() -> None:
    db = connect(":memory:")
    with pytest.raises(ValueError):
        import_openlyrics_xml(db, "<song></song>")
