from videopsalm import SectionKind, SetList, SetListItem, Song, SongLibrary, SongSection


def test_library_adds_and_searches_songs() -> None:
    library = SongLibrary()
    library.add(
        Song(
            "amazing-grace",
            "Amazing Grace",
            (SongSection("verse", "Verse", ("Amazing grace", "How sweet the sound"), SectionKind.VERSE),),
        )
    )

    assert library.get("amazing-grace").title == "Amazing Grace"
    assert library.search("sweet")[0].id == "amazing-grace"
    assert library.contains("amazing-grace") is True


def test_library_rejects_duplicate_ids() -> None:
    library = SongLibrary()
    song = Song("demo", "Demo", (SongSection("verse", "Verse", ("one",), SectionKind.VERSE),))
    library.add(song)

    try:
        library.add(song)
        raise AssertionError("expected duplicate song id rejection")
    except ValueError:
        pass


def test_set_list_resolves_song_order() -> None:
    items = (
        SetListItem("song", "amazing-grace", "Amazing Grace"),
        SetListItem("passage", "john-3-16", "John 3:16"),
    )
    setlist = SetList("sunday", "Sunday Service", items)
    assert setlist.resolve_song_ids() == ("amazing-grace",)
